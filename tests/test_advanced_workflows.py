"""
Tests for advanced workflow features including DSL parsing, templates, and advanced execution.
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from graygems.core.workflow_dsl import (
    WorkflowDSL,
    WorkflowTemplate,
    WorkflowTemplateRegistry,
    template_registry,
    BUILTIN_TEMPLATES,
)
from graygems.core.workflow import (
    WorkflowManager,
    AdvancedWorkflowStep,
    WorkflowTransaction,
)
from graygems.core.registry import ServiceRegistry
from graygems.core.service import Service, Task
from graygems.core.error_handler import WorkflowError


class TestWorkflowDSL:
    """Test the Workflow DSL parser and compiler"""

    def test_parse_variables(self):
        """Test parsing variable declarations"""
        dsl = WorkflowDSL()

        # Test string variable
        var_name, var_value = dsl._parse_variable('var input_file = "data.csv"')
        assert var_name == "input_file"
        assert var_value == "data.csv"

        # Test numeric variable
        var_name, var_value = dsl._parse_variable("var batch_size = 10")
        assert var_name == "batch_size"
        assert var_value == 10

        # Test list variable
        var_name, var_value = dsl._parse_variable(
            'var files = ["file1.csv", "file2.csv"]'
        )
        assert var_name == "files"
        assert var_value == ["file1.csv", "file2.csv"]

    def test_parse_service_step(self):
        """Test parsing service step declarations"""
        dsl = WorkflowDSL()

        # Test simple service step
        step_id, step_config = dsl._parse_service_step(
            "step validate: file_utils.validate(file=input_file)"
        )
        assert step_id == "validate"
        assert step_config["service"] == "file_utils"
        assert step_config["task"] == "validate"
        assert step_config["inputs"] == {"file": "input_file"}

        # Test service step with multiple parameters
        step_id, step_config = dsl._parse_service_step(
            "step process: data_processor.transform(input=input_file, output=output_dir)"
        )
        assert step_id == "process"
        assert step_config["service"] == "data_processor"
        assert step_config["task"] == "transform"
        assert step_config["inputs"] == {"input": "input_file", "output": "output_dir"}

    def test_parse_parameters(self):
        """Test parameter parsing"""
        dsl = WorkflowDSL()

        # Test empty parameters
        inputs = dsl._parse_parameters("")
        assert inputs == {}

        # Test single parameter
        inputs = dsl._parse_parameters("file=input_file")
        assert inputs == {"file": "input_file"}

        # Test multiple parameters
        inputs = dsl._parse_parameters(
            "input=input_file, output=output_dir, format=json"
        )
        assert inputs == {
            "input": "input_file",
            "output": "output_dir",
            "format": "json",
        }

        # Test parameters with complex values
        inputs = dsl._parse_parameters('message="Hello World", numbers=[1, 2, 3]')
        assert inputs == {"message": "Hello World", "numbers": [1, 2, 3]}

    def test_parse_simple_workflow(self):
        """Test parsing a simple workflow"""
        dsl_code = """
        # Simple workflow
        var input_file = "data.csv"
        var output_dir = "results"
        
        step validate: file_utils.validate(file=input_file)
        step process: data_processor.transform(input=input_file, output=output_dir)
        """

        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)

        assert "variables" in workflow
        assert workflow["variables"]["input_file"] == "data.csv"
        assert workflow["variables"]["output_dir"] == "results"

        assert "steps" in workflow
        assert "validate" in workflow["steps"]
        assert "process" in workflow["steps"]

        validate_step = workflow["steps"]["validate"]
        assert validate_step["service"] == "file_utils"
        assert validate_step["task"] == "validate"
        assert validate_step["inputs"] == {"file": "input_file"}

    def test_parse_condition_workflow(self):
        """Test parsing workflow with conditions"""
        dsl_code = """
        var input_file = "data.csv"
        
        step validate: file_utils.validate(file=input_file)
        
        if validate.success:
            step process: data_processor.transform(input=input_file)
        else:
            step fix: data_processor.clean(input=input_file)
        """

        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)

        # Check that condition step was created
        condition_steps = [
            step for step in workflow["steps"].values() if step["type"] == "condition"
        ]
        assert len(condition_steps) == 1

        condition_step = condition_steps[0]
        assert "condition" in condition_step
        assert "if_steps" in condition_step
        assert "else_steps" in condition_step

    def test_parse_parallel_workflow(self):
        """Test parsing workflow with parallel execution"""
        dsl_code = """
        var input_file = "data.csv"
        
        parallel:
            step validate: file_utils.validate(file=input_file)
            step backup: file_utils.copy(source=input_file, target="backup/")
        """

        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)

        # Check that parallel step was created
        parallel_steps = [
            step for step in workflow["steps"].values() if step["type"] == "parallel"
        ]
        assert len(parallel_steps) == 1

        parallel_step = parallel_steps[0]
        assert "steps" in parallel_step
        assert len(parallel_step["steps"]) == 2

    def test_parse_loop_workflow(self):
        """Test parsing workflow with loops"""
        dsl_code = """
        var files = ["file1.csv", "file2.csv"]
        
        for file in files:
            step process: data_processor.transform(input=file)
        """

        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)

        # Check that loop step was created
        loop_steps = [
            step for step in workflow["steps"].values() if step["type"] == "loop"
        ]
        assert len(loop_steps) == 1

        loop_step = loop_steps[0]
        assert "variable" in loop_step
        assert "collection" in loop_step
        assert "steps" in loop_step


class TestWorkflowTemplate:
    """Test workflow template functionality"""

    def test_template_creation(self):
        """Test creating a workflow template"""
        dsl_code = """
        var input_file = "${input_file}"
        step process: data_processor.transform(input=input_file)
        """

        parameters = {"input_file": "default.csv"}
        template = WorkflowTemplate("test_template", dsl_code, parameters)

        assert template.name == "test_template"
        assert template.dsl_code == dsl_code
        assert template.parameters == parameters

    def test_template_compilation(self):
        """Test template compilation with parameters"""
        dsl_code = """
        var input_file = "${input_file}"
        var output_dir = "${output_dir}"
        step process: data_processor.transform(input=input_file, output=output_dir)
        """

        parameters = {"input_file": "default.csv", "output_dir": "default_results"}
        template = WorkflowTemplate("test_template", dsl_code, parameters)

        # Compile with default parameters
        workflow = template.compile()
        assert workflow["variables"]["input_file"] == "default.csv"
        assert workflow["variables"]["output_dir"] == "default_results"

        # Compile with custom parameters
        workflow = template.compile(
            input_file="custom.csv", output_dir="custom_results"
        )
        assert workflow["variables"]["input_file"] == "custom.csv"
        assert workflow["variables"]["output_dir"] == "custom_results"

    def test_template_serialization(self):
        """Test template serialization and deserialization"""
        dsl_code = """
        var input_file = "${input_file}"
        step process: data_processor.transform(input=input_file)
        """

        parameters = {"input_file": "default.csv"}
        template = WorkflowTemplate("test_template", dsl_code, parameters)

        # Convert to dict
        template_dict = template.to_dict()
        assert template_dict["name"] == "test_template"
        assert template_dict["dsl_code"] == dsl_code
        assert template_dict["parameters"] == parameters

        # Create from dict
        new_template = WorkflowTemplate.from_dict(template_dict)
        assert new_template.name == template.name
        assert new_template.dsl_code == template.dsl_code
        assert new_template.parameters == template.parameters


class TestWorkflowTemplateRegistry:
    """Test workflow template registry"""

    def test_template_registration(self):
        """Test registering and retrieving templates"""
        registry = WorkflowTemplateRegistry()

        dsl_code = """
        var input_file = "${input_file}"
        step process: data_processor.transform(input=input_file)
        """

        template = WorkflowTemplate(
            "test_template", dsl_code, {"input_file": "default.csv"}
        )
        registry.register(template)

        # Test retrieval
        retrieved = registry.get("test_template")
        assert retrieved is not None
        assert retrieved.name == "test_template"

        # Test listing
        templates = registry.list_templates()
        assert "test_template" in templates

    def test_builtin_templates(self):
        """Test that built-in templates are available"""
        assert "data_processing" in BUILTIN_TEMPLATES
        assert "parallel_processing" in BUILTIN_TEMPLATES
        assert "conditional_workflow" in BUILTIN_TEMPLATES

        # Test that templates are registered in global registry
        assert "data_processing" in template_registry.list_templates()
        assert "parallel_processing" in template_registry.list_templates()
        assert "conditional_workflow" in template_registry.list_templates()


class TestAdvancedWorkflowExecution:
    """Test advanced workflow execution features"""

    @pytest.fixture
    def mock_service(self):
        """Create a mock service for testing"""
        service = Mock(spec=Service)
        service.input_model = None
        service.get_task.return_value = AsyncMock(spec=Task)
        return service

    @pytest.fixture
    def mock_registry(self, mock_service):
        """Create a mock registry with services"""
        registry = ServiceRegistry()
        registry.register("file_utils", mock_service)
        registry.register("data_processor", mock_service)
        registry.register("text_processor", mock_service)
        return registry

    @pytest.fixture
    def workflow_manager(self, mock_registry, tmp_path):
        """Create a workflow manager for testing"""
        return WorkflowManager(mock_registry, tmp_path)

    def test_create_dsl_transaction(self, workflow_manager):
        """Test creating a transaction from DSL code"""
        dsl_code = """
        var input_file = "data.csv"
        step validate: file_utils.validate(file=input_file)
        """

        transaction = workflow_manager.create_dsl_transaction(dsl_code, "test_project")

        assert transaction.project_id == "test_project"
        assert len(transaction.steps) == 1
        assert "validate" in transaction.steps
        assert transaction.variables["input_file"] == "data.csv"

    def test_create_template_transaction(self, workflow_manager):
        """Test creating a transaction from a template"""
        # Register a test template
        dsl_code = """
        var input_file = "${input_file}"
        step validate: file_utils.validate(file=input_file)
        """
        template = WorkflowTemplate(
            "test_template", dsl_code, {"input_file": "default.csv"}
        )
        template_registry.register(template)

        transaction = workflow_manager.create_template_transaction(
            "test_template", "test_project", input_file="custom.csv"
        )

        assert transaction.project_id == "test_project"
        assert len(transaction.steps) == 1
        assert transaction.variables["input_file"] == "custom.csv"

    @pytest.mark.asyncio
    async def test_execute_service_step(self, workflow_manager, mock_service):
        """Test executing a service step"""
        # Setup mock task
        mock_task = AsyncMock()
        mock_task.execute.return_value = {
            "result": "success",
            "outputs": {"processed": True},
        }
        mock_service.get_task.return_value = mock_task

        # Create transaction with service step
        transaction = WorkflowTransaction(
            transaction_id="test_transaction",
            project_id="test_project",
            workflow_data={},
        )

        step = AdvancedWorkflowStep(
            step_id="test_step",
            step_type="service",
            service_name="file_utils",
            task_name="validate",
            inputs={"file": "test.csv"},
        )
        transaction.steps["test_step"] = step

        # Execute step
        await workflow_manager._execute_service_step(transaction, step)

        assert step.status == "completed"
        assert step.outputs == {"processed": True}
        mock_task.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_condition_step(self, workflow_manager):
        """Test executing a conditional step"""
        # Create transaction with condition step
        transaction = WorkflowTransaction(
            transaction_id="test_transaction",
            project_id="test_project",
            workflow_data={},
        )

        # Add a service step that will be referenced
        service_step = AdvancedWorkflowStep(
            step_id="validate",
            step_type="service",
            service_name="file_utils",
            task_name="validate",
            inputs={"file": "test.csv"},
        )
        service_step.status = "completed"
        service_step.outputs = {"success": True}
        transaction.steps["validate"] = service_step

        # Add condition step
        condition_step = AdvancedWorkflowStep(
            step_id="condition_1",
            step_type="condition",
            condition="validate.success",
            if_steps=[],
            else_steps=[],
        )
        transaction.steps["condition_1"] = condition_step

        # Execute condition step
        await workflow_manager._execute_condition_step(transaction, condition_step)

        assert condition_step.status == "completed"
        assert condition_step.outputs["condition_result"] is True

    @pytest.mark.asyncio
    async def test_execute_parallel_step(self, workflow_manager):
        """Test executing parallel steps"""
        # Create transaction with parallel step
        transaction = WorkflowTransaction(
            transaction_id="test_transaction",
            project_id="test_project",
            workflow_data={},
        )

        # Add service steps that will be executed in parallel
        step1 = AdvancedWorkflowStep(
            step_id="step1",
            step_type="service",
            service_name="file_utils",
            task_name="validate",
            inputs={"file": "test1.csv"},
        )
        step2 = AdvancedWorkflowStep(
            step_id="step2",
            step_type="service",
            service_name="file_utils",
            task_name="validate",
            inputs={"file": "test2.csv"},
        )
        transaction.steps["step1"] = step1
        transaction.steps["step2"] = step2

        # Add parallel step
        parallel_step = AdvancedWorkflowStep(
            step_id="parallel_1",
            step_type="parallel",
            parallel_steps=["step1", "step2"],
        )
        transaction.steps["parallel_1"] = parallel_step

        # Mock the service step execution
        with patch.object(workflow_manager, "_execute_service_step") as mock_execute:
            await workflow_manager._execute_parallel_step(transaction, parallel_step)

            # Should have called execute for both steps
            assert mock_execute.call_count == 2

        assert parallel_step.status == "completed"
        assert parallel_step.outputs["parallel_completed"] is True

    @pytest.mark.asyncio
    async def test_execute_loop_step(self, workflow_manager):
        """Test executing loop steps"""
        # Create transaction with loop step
        transaction = WorkflowTransaction(
            transaction_id="test_transaction",
            project_id="test_project",
            workflow_data={},
        )

        # Add service step that will be executed in loop
        service_step = AdvancedWorkflowStep(
            step_id="process_item",
            step_type="service",
            service_name="data_processor",
            task_name="process",
            inputs={"item": "item"},
        )
        transaction.steps["process_item"] = service_step

        # Add loop step
        loop_step = AdvancedWorkflowStep(
            step_id="loop_1",
            step_type="loop",
            loop_variable="item",
            loop_collection=["file1.csv", "file2.csv"],
            loop_steps=["process_item"],
        )
        transaction.steps["loop_1"] = loop_step

        # Mock the service step execution
        with patch.object(workflow_manager, "_execute_service_step") as mock_execute:
            await workflow_manager._execute_loop_step(transaction, loop_step)

            # Should have called execute for each item in the collection
            assert mock_execute.call_count == 2

        assert loop_step.status == "completed"
        assert loop_step.outputs["total_iterations"] == 2
        assert len(loop_step.outputs["loop_results"]) == 2

    def test_evaluate_condition(self, workflow_manager):
        """Test condition evaluation"""
        # Create transaction with completed steps
        transaction = WorkflowTransaction(
            transaction_id="test_transaction",
            project_id="test_project",
            workflow_data={},
        )

        # Add a step with boolean output
        step = AdvancedWorkflowStep(step_id="validate", step_type="service")
        step.status = "completed"
        step.outputs = {"success": True}
        transaction.steps["validate"] = step

        # Test condition evaluation
        result = workflow_manager._evaluate_condition(transaction, "validate.success")
        assert result is True

        # Test with false condition
        step.outputs = {"success": False}
        result = workflow_manager._evaluate_condition(transaction, "validate.success")
        assert result is False

    def test_resolve_dependency_reference(self, workflow_manager):
        """Test resolving dependency references"""
        # Create transaction with completed steps
        transaction = WorkflowTransaction(
            transaction_id="test_transaction",
            project_id="test_project",
            workflow_data={},
        )

        # Add a step with nested output
        step = AdvancedWorkflowStep(step_id="process", step_type="service")
        step.status = "completed"
        step.outputs = {"result": {"data": [1, 2, 3], "metadata": {"count": 3}}}
        transaction.steps["process"] = step

        # Test resolving nested reference
        value = workflow_manager._resolve_dependency_reference(
            transaction, "$process.result.metadata.count"
        )
        assert value == 3

        # Test resolving list reference
        value = workflow_manager._resolve_dependency_reference(
            transaction, "$process.result.data"
        )
        assert value == [1, 2, 3]


class TestIntegration:
    """Integration tests for advanced workflow features"""

    @pytest.mark.asyncio
    async def test_complete_dsl_workflow_execution(self, tmp_path):
        """Test complete DSL workflow execution"""
        # Create mock services
        registry = ServiceRegistry()

        # Mock file_utils service
        file_utils_service = Mock(spec=Service)
        file_utils_service.input_model = None

        validate_task = AsyncMock()
        validate_task.execute.return_value = {
            "success": True,
            "outputs": {"valid": True},
        }
        file_utils_service.get_task.return_value = validate_task

        registry.register("file_utils", file_utils_service)

        # Create workflow manager
        workflow_manager = WorkflowManager(registry, tmp_path)

        # Define DSL workflow
        dsl_code = """
        var input_file = "test.csv"
        step validate: file_utils.validate(file=input_file)
        """

        # Execute workflow
        result = await workflow_manager.execute_dsl_workflow(
            "test_project", dsl_code, tmp_path
        )

        # Verify result
        assert result["status"] == "completed"
        assert "validate" in result["steps"]
        assert result["steps"]["validate"]["status"] == "completed"
        assert result["variables"]["input_file"] == "test.csv"

    @pytest.mark.asyncio
    async def test_template_workflow_execution(self, tmp_path):
        """Test template workflow execution"""
        # Create mock services
        registry = ServiceRegistry()

        # Mock file_utils service
        file_utils_service = Mock(spec=Service)
        file_utils_service.input_model = None

        validate_task = AsyncMock()
        validate_task.execute.return_value = {
            "success": True,
            "outputs": {"valid": True},
        }
        file_utils_service.get_task.return_value = validate_task

        copy_task = AsyncMock()
        copy_task.execute.return_value = {"success": True, "outputs": {"copied": True}}
        file_utils_service.get_task.side_effect = lambda name: (
            validate_task if name == "validate" else copy_task
        )

        registry.register("file_utils", file_utils_service)

        # Mock data_processor service
        data_processor_service = Mock(spec=Service)
        data_processor_service.input_model = None

        transform_task = AsyncMock()
        transform_task.execute.return_value = {
            "result": "processed",
            "outputs": {"processed": True},
        }

        analyze_task = AsyncMock()
        analyze_task.execute.return_value = {
            "result": "analyzed",
            "outputs": {"analyzed": True},
        }

        clean_task = AsyncMock()
        clean_task.execute.return_value = {
            "result": "cleaned",
            "outputs": {"cleaned": True},
        }

        def get_task(name):
            if name == "transform":
                return transform_task
            elif name == "analyze":
                return analyze_task
            elif name == "clean":
                return clean_task
            else:
                return transform_task

        data_processor_service.get_task.side_effect = get_task
        registry.register("data_processor", data_processor_service)

        # Mock text_processor service
        text_processor_service = Mock(spec=Service)
        text_processor_service.input_model = None

        report_task = AsyncMock()
        report_task.execute.return_value = {
            "result": "reported",
            "outputs": {"reported": True},
        }
        text_processor_service.get_task.return_value = report_task

        registry.register("text_processor", text_processor_service)

        # Create workflow manager
        workflow_manager = WorkflowManager(registry, tmp_path)

        # Execute built-in template
        result = await workflow_manager.execute_template_workflow(
            "test_project",
            "data_processing",
            tmp_path,
            input_file="custom.csv",
            output_dir="custom_results",
        )

        # Verify result
        assert result["status"] == "completed"
        assert result["variables"]["input_file"] == "custom.csv"
        assert result["variables"]["output_dir"] == "custom_results"
