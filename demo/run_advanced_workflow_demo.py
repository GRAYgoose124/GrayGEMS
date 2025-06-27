#!/usr/bin/env python3
"""
Advanced Workflow Demo
Demonstrates the new DSL workflow features, templates, and advanced execution.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from graygems.core.registry import ServiceRegistry
from graygems.core.service import Service, Task
from graygems.core.workflow import WorkflowManager
from graygems.core.workflow_dsl import WorkflowDSL, template_registry


def create_mock_services():
    """Create mock services for the demo"""
    registry = ServiceRegistry()

    # Mock file_utils service
    file_utils_service = Mock(spec=Service)
    file_utils_service.input_model = None

    validate_task = AsyncMock()
    validate_task.execute.return_value = {"success": True, "outputs": {"valid": True}}

    copy_task = AsyncMock()
    copy_task.execute.return_value = {"success": True, "outputs": {"copied": True}}

    def get_file_task(name):
        if name == "validate":
            return validate_task
        elif name == "copy":
            return copy_task
        else:
            return validate_task

    file_utils_service.get_task.side_effect = get_file_task
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

    def get_data_task(name):
        if name == "transform":
            return transform_task
        elif name == "analyze":
            return analyze_task
        elif name == "clean":
            return clean_task
        else:
            return transform_task

    data_processor_service.get_task.side_effect = get_data_task
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

    return registry


async def demo_dsl_workflow():
    """Demo a simple DSL workflow"""
    print("=== DSL Workflow Demo ===")

    # Create mock services
    registry = create_mock_services()

    # Create workflow manager
    project_dir = Path("demo/projects/dsl_demo")
    project_dir.mkdir(parents=True, exist_ok=True)
    workflow_manager = WorkflowManager(registry, project_dir)

    # Define a simple DSL workflow
    dsl_code = """
    # Simple data processing workflow
    var input_file = "data.csv"
    var output_dir = "results"
    
    step validate: file_utils.validate(file=input_file)
    step process: data_processor.transform(input=input_file, output=output_dir)
    step report: text_processor.generate_report(data=process.result)
    """

    print("DSL Code:")
    print(dsl_code)

    # Execute the workflow
    result = await workflow_manager.execute_dsl_workflow(
        "demo_project", dsl_code, project_dir
    )

    print("\nWorkflow Result:")
    print(f"Status: {result['status']}")
    print(f"Steps executed: {len(result['steps'])}")
    for step_id, step_info in result["steps"].items():
        print(
            f"  {step_id}: {step_info['status']} ({step_info['service']}.{step_info['task']})"
        )


async def demo_template_workflow():
    """Demo a template workflow"""
    print("\n=== Template Workflow Demo ===")

    # Create mock services
    registry = create_mock_services()

    # Create workflow manager
    project_dir = Path("demo/projects/template_demo")
    project_dir.mkdir(parents=True, exist_ok=True)
    workflow_manager = WorkflowManager(registry, project_dir)

    # Show available templates
    print("Available templates:")
    for template_name in template_registry.list_templates():
        template = template_registry.get(template_name)
        print(f"  {template_name}: {template.parameters}")

    # Execute a built-in template
    print("\nExecuting 'data_processing' template...")
    result = await workflow_manager.execute_template_workflow(
        "template_project",
        "data_processing",
        project_dir,
        input_file="custom_data.csv",
        output_dir="custom_results",
        backup_dir="custom_backup",
    )

    print(f"Template execution result: {result['status']}")
    print(f"Variables: {result['variables']}")


async def demo_advanced_workflow():
    """Demo an advanced workflow with conditions and parallel execution"""
    print("\n=== Advanced Workflow Demo ===")

    # Create mock services
    registry = create_mock_services()

    # Create workflow manager
    project_dir = Path("demo/projects/advanced_demo")
    project_dir.mkdir(parents=True, exist_ok=True)
    workflow_manager = WorkflowManager(registry, project_dir)

    # Define an advanced DSL workflow
    advanced_dsl = """
    # Advanced workflow with conditions and parallel execution
    var input_file = "data.csv"
    var output_dir = "results"
    
    step validate: file_utils.validate(file=input_file)
    
    if validate.success:
        step backup: file_utils.copy(source=input_file, target="backup/")
        
        parallel:
            step analyze: data_processor.analyze(input=input_file)
            step transform: data_processor.transform(input=input_file, output=output_dir)
        
        step report: text_processor.generate_report(data=analyze.result)
    else:
        step fix_data: data_processor.clean(input=input_file)
    """

    print("Advanced DSL Code:")
    print(advanced_dsl)

    # Execute the advanced workflow
    result = await workflow_manager.execute_dsl_workflow(
        "advanced_project", advanced_dsl, project_dir
    )

    print(f"\nAdvanced workflow result: {result['status']}")
    print(f"Steps executed: {len(result['steps'])}")
    for step_id, step_info in result["steps"].items():
        print(
            f"  {step_id}: {step_info['status']} ({step_info.get('step_type', 'service')})"
        )


def demo_dsl_compilation():
    """Demo DSL compilation to JSON"""
    print("\n=== DSL Compilation Demo ===")

    dsl_parser = WorkflowDSL()

    # Define a DSL workflow
    dsl_code = """
    var input_file = "data.csv"
    step process: data_processor.transform(input=input_file)
    """

    print("DSL Code:")
    print(dsl_code)

    # Compile to JSON
    workflow_json = dsl_parser.parse_workflow(dsl_code)

    print("\nCompiled JSON:")
    print(json.dumps(workflow_json, indent=2))


async def main():
    """Run all demos"""
    print("GrayGEMS Advanced Workflow Demo")
    print("=" * 50)

    # Demo DSL compilation
    demo_dsl_compilation()

    # Demo DSL workflow execution
    await demo_dsl_workflow()

    # Demo template workflow execution
    await demo_template_workflow()

    # Demo advanced workflow execution
    await demo_advanced_workflow()

    print("\n" + "=" * 50)
    print("Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
