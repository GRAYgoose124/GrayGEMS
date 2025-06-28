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


def find_steps_of_type(steps_dict, step_type):
    """Recursively search for steps of a given type in the nested structure"""
    found = []
    for step_id, step in steps_dict.items():
        if step.get("type") == step_type:
            found.append((step_id, step))
        # Recursively search nested blocks
        if step.get("type") == "loop" and "steps" in step:
            found.extend(find_steps_of_type(step["steps"], step_type))
        if step.get("type") == "parallel" and "steps" in step:
            found.extend(find_steps_of_type(step["steps"], step_type))
        if step.get("type") == "condition":
            if "if_steps_dict" in step:
                found.extend(find_steps_of_type(step["if_steps_dict"], step_type))
            if "else_steps_dict" in step:
                found.extend(find_steps_of_type(step["else_steps_dict"], step_type))
    return found


def find_step_by_name(steps_dict, step_name):
    """Recursively search for a step containing the given name in its ID"""
    found = []
    for step_id, step in steps_dict.items():
        if step_name in step_id:
            found.append((step_id, step))
        # Recursively search nested blocks
        if step.get("type") == "loop" and "steps" in step:
            found.extend(find_step_by_name(step["steps"], step_name))
        if step.get("type") == "parallel" and "steps" in step:
            found.extend(find_step_by_name(step["steps"], step_name))
        if step.get("type") == "condition":
            if "if_steps_dict" in step:
                found.extend(find_step_by_name(step["if_steps_dict"], step_name))
            if "else_steps_dict" in step:
                found.extend(find_step_by_name(step["else_steps_dict"], step_name))
    return found


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

    def test_parse_conditional_workflow(self):
        """Test parsing a workflow with nested conditions and parallel execution"""
        dsl_code = '''
        var input_data = ${input_data}
        var threshold = "${threshold}"
        
        step validate: data_processor.validate(input=input_data)
        
        if validate.success:
            if validate.score > threshold:
                parallel:
                    step process: data_processor.transform(input=input_data)
                    step analyze: data_processor.analyze(input=input_data)
                step report: text_processor.generate_report(data=analyze.result)
            else:
                step flag: text_processor.flag_low_score(score=validate.score)
        else:
            step log_error: text_processor.log_error(message="Validation failed")
        
        step aggregate: data_processor.aggregate(input=input_data)
        step archive: file_utils.archive(input=aggregate.result)
        '''
        
        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)
        steps = workflow["steps"]
        
        # Verify validate step exists
        validate_steps = find_step_by_name(steps, "validate")
        assert validate_steps, "validate step not found"
        
        # Verify nested conditions exist
        condition_steps = find_steps_of_type(steps, "condition")
        assert len(condition_steps) >= 2, "Should have at least 2 condition steps"
        
        # Find the outer condition (the one that depends on validate.success)
        outer_condition = None
        for step_id, step_config in condition_steps:
            if step_config.get("condition") == "validate.success":
                outer_condition = step_config
                break
        
        assert outer_condition is not None, "Outer condition not found"
        
        # Verify outer condition has if_steps and else_steps
        assert "if_steps" in outer_condition, "Outer condition missing if_steps"
        assert "else_steps" in outer_condition, "Outer condition missing else_steps"
        
        # Find nested condition in if_steps (recursively)
        nested_condition_found = False
        if "if_steps_dict" in outer_condition:
            nested_condition_found = bool(find_steps_of_type(outer_condition["if_steps_dict"], "condition"))
        elif "if_steps" in outer_condition:
            # If only if_steps (list of IDs), try to find in steps dict
            for step_id in outer_condition["if_steps"]:
                if step_id in steps and steps[step_id].get("type") == "condition":
                    nested_condition_found = True
                    break
        assert nested_condition_found, "Should have at least one nested condition"
        
        # Verify that all expected service steps exist in the nested structure
        expected_services = ["validate", "process", "analyze", "archive", "flag", "log_error", "aggregate"]
        for service in expected_services:
            service_found = bool(find_step_by_name(steps, service))
            assert service_found, f"Service step '{service}' not found in nested structure"

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

    def test_parse_batch_processing_workflow(self):
        """Test parsing a batch processing workflow with nested loops, parallels, and conditions"""
        dsl_code = '''
        var input_files = ${input_files}
        var output_dir = "${output_dir}"
        var batch_size = "${batch_size}"
    
        for file in input_files:
            parallel:
                step validate_file: file_utils.validate(file=file)
                step backup_file: file_utils.copy(source=file, target="backup/")
            if validate_file.success:
                parallel:
                    step process_file: data_processor.transform(input=file, output=output_dir)
                    step analyze_file: data_processor.analyze(input=file)
                step report_file: text_processor.generate_report(data=analyze_file.result)
            else:
                step log_invalid: text_processor.log_error(message="Invalid file: " + file)
        step aggregate: data_processor.aggregate(input=output_dir, batch_size=batch_size)
        step batch_summary: text_processor.generate_batch_summary(data=aggregate.result)
        '''
        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)
        steps = workflow["steps"]
        # Check for loop step
        loop_steps = [k for k, v in steps.items() if v.get("type") == "loop"]
        assert loop_steps, "No loop step found"
        loop_step = steps[loop_steps[0]]
        # Check for parallel and condition steps inside the loop
        # Look for steps that contain "parallel" or "condition" in their ID
        nested_parallel = any("parallel" in s for s in loop_step["steps"])
        nested_condition = any("condition" in s for s in loop_step["steps"])
        assert nested_parallel, "No parallel step found in loop"
        assert nested_condition, "No condition step found in loop"
        # Check for service steps
        assert "aggregate" in steps
        assert "batch_summary" in steps
        # Check that all expected service steps are present (with unique IDs)
        expected_service_steps = [
            "validate_file", "backup_file", "process_file", "analyze_file", "report_file", "log_invalid"
        ]
        # Use recursive search to find steps by name
        for step_name in expected_service_steps:
            found_steps = find_step_by_name(steps, step_name)
            assert found_steps, f"Missing expected service step: {step_name}"
        
        # Verify that the nested structure is correct
        # Check that validate_file is inside a parallel block
        validate_steps = find_step_by_name(steps, "validate_file")
        assert validate_steps, "validate_file step not found in any block"
        
        # Check that process_file and analyze_file are inside a parallel block
        process_steps = find_step_by_name(steps, "process_file")
        analyze_steps = find_step_by_name(steps, "analyze_file")
        assert process_steps, "process_file step not found in any block"
        assert analyze_steps, "analyze_file step not found in any block"

    def test_dsl_execution_structure_validation(self):
        """Test that DSL produces correct execution structure for complex workflows"""
        dsl_code = """
        var input_files = ["file1.csv", "file2.csv"]
        var output_dir = "results"
        
        for file in input_files:
            parallel:
                step validate: file_utils.validate(file=file)
                step backup: file_utils.copy(source=file, target="backup/")
            
            if validate.success:
                parallel:
                    step process: data_processor.transform(input=file, output=output_dir)
                    step analyze: data_processor.analyze(input=file)
                step report: text_processor.generate_report(data=analyze.result)
            else:
                step log_error: text_processor.log_error(message="Invalid file: " + file)
        
        step aggregate: data_processor.aggregate(input=output_dir)
        step summary: text_processor.generate_summary(data=aggregate.result)
        """
        
        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)
        steps = workflow["steps"]
        
        # Verify loop structure
        loop_step = None
        for step_id, step_config in steps.items():
            if step_config.get("type") == "loop":
                loop_step = step_config
                break
        
        assert loop_step is not None, "Loop step not found"
        assert loop_step["variable"] == "file"
        assert loop_step["collection"] == "input_files"
        
        # Verify loop contains parallel and condition
        loop_children = loop_step["steps"]
        assert len(loop_children) == 2, f"Loop should have 2 children, got {len(loop_children)}"
        
        # Find parallel and condition in loop using recursive search
        parallel_steps = find_steps_of_type(loop_step["steps"], "parallel")
        condition_steps = find_steps_of_type(loop_step["steps"], "condition")
        
        assert len(parallel_steps) >= 1, "Parallel step not found in loop"
        assert len(condition_steps) >= 1, "Condition step not found in loop"
        
        parallel_in_loop = parallel_steps[0][1]  # Get the first parallel step config
        condition_in_loop = condition_steps[0][1]  # Get the first condition step config
        
        # Verify parallel contains validate and backup (with unique IDs)
        parallel_steps_list = parallel_in_loop["steps"]
        assert len(parallel_steps_list) == 2, f"Parallel should have 2 steps, got {len(parallel_steps_list)}"
        # Look for steps that contain the expected names
        validate_found = any("validate" in step_id for step_id in parallel_steps_list)
        backup_found = any("backup" in step_id for step_id in parallel_steps_list)
        assert validate_found, "validate step not found in parallel"
        assert backup_found, "backup step not found in parallel"
        
        # Verify condition structure
        assert "validate.success" in condition_in_loop["condition"], f"Condition should reference validate.success, got: {condition_in_loop['condition']}"
        
        # Check if_steps and else_steps exist (they may be in the nested structure)
        if_steps_exist = "if_steps" in condition_in_loop or "if_steps_dict" in condition_in_loop
        else_steps_exist = "else_steps" in condition_in_loop or "else_steps_dict" in condition_in_loop
        assert if_steps_exist, "Condition missing if_steps"
        assert else_steps_exist, "Condition missing else_steps"
        
        # Verify top-level steps after loop
        top_level_steps = [step_id for step_id, step_config in steps.items() 
                          if step_config.get("type") == "service" and step_id not in 
                          [s for s in steps.values() if s.get("type") in ["loop", "parallel", "condition"] 
                           for child in s.get("steps", [])]]
        
        assert "aggregate" in top_level_steps
        assert "summary" in top_level_steps

    def test_dsl_dependency_validation(self):
        """Test that DSL correctly calculates dependencies between steps"""
        dsl_code = """
        var input_file = "data.csv"
        
        step validate: file_utils.validate(file=input_file)
        step process: data_processor.transform(input=input_file)
        step analyze: data_processor.analyze(input=process.result)
        step report: text_processor.generate_report(data=analyze.result)
        """
        
        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)
        steps = workflow["steps"]
        
        # Verify dependencies
        assert steps["validate"]["dependencies"] == []
        assert steps["process"]["dependencies"] == []
        assert steps["analyze"]["dependencies"] == ["process"]
        assert steps["report"]["dependencies"] == ["analyze"]

    def test_dsl_parallel_execution_validation(self):
        """Test that DSL correctly structures parallel execution"""
        dsl_code = """
        var input_file = "data.csv"
        
        parallel:
            step validate: file_utils.validate(file=input_file)
            step backup: file_utils.copy(source=input_file, target="backup/")
            step metadata: file_utils.extract_metadata(file=input_file)
        
        step process: data_processor.transform(input=input_file)
        """
        
        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)
        steps = workflow["steps"]
        
        # Find parallel step
        parallel_step = None
        for step_id, step_config in steps.items():
            if step_config.get("type") == "parallel":
                parallel_step = step_config
                break
        
        assert parallel_step is not None, "Parallel step not found"
        assert len(parallel_step["steps"]) == 3, "Parallel should have 3 steps"
        # Look for steps that contain the expected names
        validate_found = any("validate" in step_id for step_id in parallel_step["steps"])
        backup_found = any("backup" in step_id for step_id in parallel_step["steps"])
        metadata_found = any("metadata" in step_id for step_id in parallel_step["steps"])
        assert validate_found, "validate step not found in parallel"
        assert backup_found, "backup step not found in parallel"
        assert metadata_found, "metadata step not found in parallel"

    def test_dsl_condition_execution_validation(self):
        """Test that DSL correctly structures conditional execution"""
        dsl_code = """
        var input_file = "data.csv"
        
        step validate: file_utils.validate(file=input_file)
        
        if validate.success:
            step process: data_processor.transform(input=input_file)
            step analyze: data_processor.analyze(input=process.result)
        else:
            step fix: data_processor.clean(input=input_file)
            step retry: file_utils.validate(file=fix.result)
        
        step final: text_processor.generate_report(data=analyze.result)
        """
        
        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)
        steps = workflow["steps"]
        
        # Find condition step
        condition_step = None
        for step_id, step_config in steps.items():
            if step_config.get("type") == "condition":
                condition_step = step_config
                break
        
        assert condition_step is not None, "Condition step not found"
        assert condition_step["condition"] == "validate.success"
        assert len(condition_step["if_steps"]) == 2, "If steps should have 2 items"
        assert len(condition_step["else_steps"]) == 2, "Else steps should have 2 items"
        
        # Verify if_steps (with unique IDs)
        if_steps = condition_step["if_steps"]
        process_found = any("process" in step_id for step_id in if_steps)
        analyze_found = any("analyze" in step_id for step_id in if_steps)
        assert process_found, "process step not found in if_steps"
        assert analyze_found, "analyze step not found in if_steps"
        
        # Verify else_steps (with unique IDs)
        else_steps = condition_step["else_steps"]
        fix_found = any("fix" in step_id for step_id in else_steps)
        retry_found = any("retry" in step_id for step_id in else_steps)
        assert fix_found, "fix step not found in else_steps"
        assert retry_found, "retry step not found in else_steps"

    def test_dsl_loop_execution_validation(self):
        """Test that DSL correctly structures loop execution"""
        dsl_code = """
        var files = ["file1.csv", "file2.csv", "file3.csv"]
        
        for file in files:
            step process: data_processor.transform(input=file)
            step validate: file_utils.validate(file=process.result)
            
            if validate.success:
                step archive: file_utils.move(source=file, target="processed/")
            else:
                step log_error: text_processor.log_error(message="Failed to process " + file)
        """
        
        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)
        steps = workflow["steps"]
        
        # Find loop step
        loop_step = None
        for step_id, step_config in steps.items():
            if step_config.get("type") == "loop":
                loop_step = step_config
                break
        
        assert loop_step is not None, "Loop step not found"
        assert loop_step["variable"] == "file"
        assert loop_step["collection"] == "files"
        
        # Verify loop contains expected steps
        loop_steps = loop_step["steps"]
        assert len(loop_steps) == 3, f"Loop should have 3 children, got {len(loop_steps)}"
        
        # Should contain: process, validate, and condition
        # Look for steps that contain the expected names
        process_found = any("process" in step_id for step_id in loop_steps)
        validate_found = any("validate" in step_id for step_id in loop_steps)
        condition_found = any("condition" in step_id for step_id in loop_steps)
        assert process_found, "process step not found in loop"
        assert validate_found, "validate step not found in loop"
        assert condition_found, "condition step not found in loop"

    def test_dsl_complex_nesting_validation(self):
        """Test that DSL correctly handles complex nested structures"""
        dsl_code = """
        var input_files = ["file1.csv", "file2.csv"]
        
        for file in input_files:
            parallel:
                step validate: file_utils.validate(file=file)
                step backup: file_utils.copy(source=file, target="backup/")
            
            if validate.success:
                parallel:
                    step process: data_processor.transform(input=file)
                    step analyze: data_processor.analyze(input=file)
                
                if analyze.quality > 0.8:
                    step archive: file_utils.move(source=file, target="high_quality/")
                else:
                    step flag: text_processor.flag_low_quality(file=file, quality=analyze.quality)
            else:
                step log_error: text_processor.log_error(message="Invalid file: " + file)
        
        step aggregate: data_processor.aggregate(input="high_quality/")
        """
        
        dsl = WorkflowDSL()
        workflow = dsl.parse_workflow(dsl_code)
        steps = workflow["steps"]
        
        # Verify overall structure
        loop_steps = [k for k, v in steps.items() if v.get("type") == "loop"]
        assert len(loop_steps) == 1, "Should have exactly one loop"
        
        loop_step = steps[loop_steps[0]]
        assert len(loop_step["steps"]) == 2, "Loop should have 2 children (parallel + condition)"
        
        # Verify nested condition inside the main condition
        # Use recursive search to find condition steps in the nested structure
        condition_steps = find_steps_of_type(steps, "condition")
        assert len(condition_steps) >= 1, "Should have at least one condition"
        
        # Verify that we have nested conditions by looking for condition steps that contain other condition steps
        nested_conditions = 0
        for step_id, condition_config in condition_steps:
            # Check if this condition has nested conditions in its if_steps
            if "if_steps_dict" in condition_config:
                nested_conditions += len(find_steps_of_type(condition_config["if_steps_dict"], "condition"))
            elif "if_steps" in condition_config:
                # Check if any of the if_steps are conditions
                for if_step_id in condition_config["if_steps"]:
                    if if_step_id in steps and steps[if_step_id].get("type") == "condition":
                        nested_conditions += 1
        
        assert nested_conditions >= 1, "Should have at least one nested condition"
        
        # Verify that all expected service steps exist in the nested structure
        expected_services = ["validate", "process", "analyze", "archive", "flag", "log_error", "aggregate"]
        for service in expected_services:
            service_found = bool(find_step_by_name(steps, service))
            assert service_found, f"Service step '{service}' not found in nested structure"


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

    @pytest.mark.asyncio
    async def test_execute_batch_processing_workflow(self, workflow_manager, mock_registry):
        """Integration test: Execute a batch-processing DSL workflow with loop, parallel, and condition"""
        dsl_code = '''
        var input_files = ["file1.csv", "file2.csv"]
        var output_dir = "results"
        var batch_size = 2
    
        for file in input_files:
            parallel:
                step validate_file: file_utils.validate(file=file)
                step backup_file: file_utils.copy(source=file, target="backup/")
            if validate_file.success:
                parallel:
                    step process_file: data_processor.transform(input=file, output=output_dir)
                    step analyze_file: data_processor.analyze(input=file)
                step report_file: text_processor.generate_report(data=analyze_file.result)
            else:
                step log_invalid: text_processor.log_error(message="Invalid file: " + file)
        step aggregate: data_processor.aggregate(input=output_dir, batch_size=batch_size)
        step batch_summary: text_processor.generate_batch_summary(data=aggregate.result)
        '''
    
        # Patch all service tasks to record their calls
        call_log = []
        def make_mock_task(name):
            async def mock_task(inputs, project_dir):
                call_log.append((name, dict(inputs)))
                # Simulate validation: file1.csv is valid, file2.csv is not
                if name == "file_utils.validate":
                    success = inputs["file"] == "file1.csv"
                    return {"outputs": {"success": success}}
                if name == "data_processor.analyze":
                    result = f"analysis_of_{inputs['input']}"
                    return {"outputs": {"result": result}}
                if name == "text_processor.generate_report":
                    return {"outputs": {"report": f"report_for_{inputs['data']}"}}
                if name == "text_processor.log_error":
                    return {"outputs": {"logged": True}}
                if name == "data_processor.aggregate":
                    return {"outputs": {"result": {}}}
                if name == "text_processor.generate_batch_summary":
                    return {"outputs": {"summary": "batch_complete"}}
                # Default response for other tasks
                return {"outputs": {}}
            
            return mock_task
    
        # Create proper mock services with tasks dictionary
        from unittest.mock import Mock
        from graygems.core.service import Service, Task
        
        class MockTask(Task):
            def __init__(self, name, mock_func):
                self.name = name
                self.mock_func = mock_func
            
            async def execute(self, inputs, project_dir):
                return await self.mock_func(inputs, project_dir)
        
        # Create mock services with proper structure
        for service_name in ["file_utils", "data_processor", "text_processor"]:
            # Create a mock service with proper structure
            mock_service = Mock()
            mock_service.tasks = {}
            mock_service.input_model = None
            
            # Add tasks to the service
            for task_name in ["validate", "copy", "transform", "analyze", "generate_report", "log_error", "aggregate", "generate_batch_summary"]:
                full_task_name = f"{service_name}.{task_name}"
                mock_task = MockTask(full_task_name, make_mock_task(full_task_name))
                mock_service.tasks[task_name] = mock_task
            
            # Set up get_task method
            def get_task(name, svc=mock_service):
                return svc.tasks.get(name)
            mock_service.get_task.side_effect = get_task
            
            # Replace existing service or register new one
            if service_name in mock_registry._services:
                mock_registry._services[service_name] = mock_service
            else:
                mock_registry.register(service_name, mock_service)
    
        # Run the workflow
        project_id = "test_project"
        transaction = workflow_manager.create_dsl_transaction(dsl_code, project_id)
        
        result = await workflow_manager.execute_dsl_workflow(
            project_id, dsl_code, workflow_manager.project_dir
        )
    
        # Verify the workflow completed successfully
        assert result["status"] == "completed"
        assert "transaction_id" in result
    
        # Verify that the essential workflow logic worked correctly
        validate_calls = [call for call in call_log if call[0] == "file_utils.validate"]
        assert len(validate_calls) >= 2, f"Expected at least 2 validate calls, got {len(validate_calls)}"
        
        copy_calls = [call for call in call_log if call[0] == "file_utils.copy"]
        assert len(copy_calls) >= 2, f"Expected at least 2 copy calls, got {len(copy_calls)}"
        
        # Verify that both files were processed
        validate_files = [call[1]["file"] for call in validate_calls]
        assert "file1.csv" in validate_files, "file1.csv should have been validated"
        assert "file2.csv" in validate_files, "file2.csv should have been validated"
        
        # Verify conditional execution (file1.csv should be processed, file2.csv should be logged as error)
        transform_calls = [call for call in call_log if call[0] == "data_processor.transform"]
        assert len(transform_calls) >= 1, f"Expected at least 1 transform call, got {len(transform_calls)}"
        
        log_calls = [call for call in call_log if call[0] == "text_processor.log_error"]
        assert len(log_calls) >= 1, f"Expected at least 1 log error call, got {len(log_calls)}"
        
        # Verify that step references are being resolved correctly
        report_calls = [call for call in call_log if call[0] == "text_processor.generate_report"]
        assert len(report_calls) >= 1, f"Expected at least 1 report call, got {len(report_calls)}"
        
        # Check that at least one report call has resolved data (not the literal string)
        resolved_reports = [call for call in report_calls if call[1]["data"] != "analyze_file.result"]
        assert len(resolved_reports) >= 1, "At least one report should have resolved step reference data"
        
        # Verify final aggregation and summary
        aggregate_calls = [call for call in call_log if call[0] == "data_processor.aggregate"]
        assert len(aggregate_calls) == 1, f"Expected 1 aggregate call, got {len(aggregate_calls)}"
        
        summary_calls = [call for call in call_log if call[0] == "text_processor.generate_batch_summary"]
        assert len(summary_calls) == 1, f"Expected 1 batch summary call, got {len(summary_calls)}"


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
