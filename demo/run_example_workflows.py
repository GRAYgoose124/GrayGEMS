#!/usr/bin/env python3
"""
Example Workflows Runner
Runs all example DSL workflows from examples/advanced_workflows/ and verifies they work correctly.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List

from graygems.core.registry import ServiceRegistry
from graygems.core.service import Service, Task
from graygems.core.workflow import WorkflowManager
from graygems.core.workflow_dsl import WorkflowDSL, template_registry

class ExampleWorkflowRunner:
    """Runner for example workflows with comprehensive service mocking"""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.registry = self._create_mock_services()
        self.workflow_manager = WorkflowManager(self.registry, project_dir)
        self.results = {}
        
    def _create_mock_services(self) -> ServiceRegistry:
        """Create comprehensive mock services for all example workflows"""
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
        
        # Mock data_processor service with all required tasks
        data_processor_service = Mock(spec=Service)
        data_processor_service.input_model = None
        
        # Create mock tasks for all data_processor operations
        tasks = {
            "analyze": {"result": "analyzed", "outputs": {"analyzed": True}},
            "transform": {"result": "transformed", "outputs": {"transformed": True}},
            "clean": {"result": "cleaned", "outputs": {"cleaned": True}},
            "aggregate": {"result": "aggregated", "outputs": {"aggregated": True}},
            "finalize": {"result": "finalized", "outputs": {"finalized": True}},
            "detect_type": {"result": "csv", "outputs": {"type": "csv"}},
            "process_csv": {"result": "processed_csv", "outputs": {"processed": True}},
            "process_json": {"result": "processed_json", "outputs": {"processed": True}},
            "process_xml": {"result": "processed_xml", "outputs": {"processed": True}},
            "process_generic": {"result": "processed_generic", "outputs": {"processed": True}},
            "quick_analysis": {"result": "quick_analysis", "outputs": {"analysis": "quick"}},
            "detailed_analysis": {"result": "detailed_analysis", "outputs": {"analysis": "detailed"}},
            "export": {"result": "exported", "outputs": {"exported": True}},
        }
        
        def get_data_task(name):
            if name in tasks:
                task = AsyncMock()
                task.execute.return_value = tasks[name]
                return task
            else:
                # Default task for any other name
                task = AsyncMock()
                task.execute.return_value = {"result": "processed", "outputs": {"processed": True}}
                return task
        
        data_processor_service.get_task.side_effect = get_data_task
        registry.register("data_processor", data_processor_service)
        
        # Mock text_processor service with all required tasks
        text_processor_service = Mock(spec=Service)
        text_processor_service.input_model = None
        
        text_tasks = {
            "generate_report": {"result": "report_generated", "outputs": {"reported": True}},
            "generate_summary": {"result": "summary_generated", "outputs": {"summarized": True}},
            "generate_quick_report": {"result": "quick_report", "outputs": {"quick_report": True}},
            "generate_detailed_report": {"result": "detailed_report", "outputs": {"detailed_report": True}},
            "generate_batch_summary": {"result": "batch_summary", "outputs": {"batch_summary": True}},
            "log_error": {"result": "error_logged", "outputs": {"logged": True}},
            "log_warning": {"result": "warning_logged", "outputs": {"logged": True}},
        }
        
        def get_text_task(name):
            if name in text_tasks:
                task = AsyncMock()
                task.execute.return_value = text_tasks[name]
                return task
            else:
                # Default task for any other name
                task = AsyncMock()
                task.execute.return_value = {"result": "text_processed", "outputs": {"processed": True}}
                return task
        
        text_processor_service.get_task.side_effect = get_text_task
        registry.register("text_processor", text_processor_service)
        
        return registry
    
    async def run_workflow(self, name: str, dsl_file: Path, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single workflow and return results"""
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print(f"File: {dsl_file}")
        print(f"Parameters: {parameters}")
        print(f"{'='*60}")
        
        # Read DSL content
        dsl_content = dsl_file.read_text()
        print(f"Original DSL Content:\n{dsl_content}")
        
        # For batch_processing, show what the substitution would look like
        if name == "batch_processing":
            print(f"\nDEBUG - Parameters for substitution:")
            for param_name, param_value in parameters.items():
                print(f"  {param_name}: {param_value} (type: {type(param_value)})")
            
            # Show what the substitution would produce
            substituted_dsl = dsl_content
            for param_name, param_value in parameters.items():
                placeholder = f"${{{param_name}}}"
                if isinstance(param_value, (list, tuple)):
                    replacement = str(param_value)
                else:
                    replacement = str(param_value)
                substituted_dsl = substituted_dsl.replace(placeholder, replacement)
            
            print(f"\nDEBUG - After substitution:\n{substituted_dsl}")
        
        try:
            # Execute workflow
            result = await self.workflow_manager.execute_dsl_workflow(
                f"example_{name}",
                dsl_content,
                self.project_dir,
                **parameters
            )
            
            # Store result
            self.results[name] = {
                "status": result["status"],
                "steps": len(result["steps"]),
                "variables": result.get("variables", {}),
                "success": result["status"] == "completed"
            }
            
            print(f"\n✅ Workflow '{name}' completed successfully!")
            print(f"   Status: {result['status']}")
            print(f"   Steps executed: {len(result['steps'])}")
            print(f"   Variables: {result.get('variables', {})}")
            
            # Show step details
            print("\n   Step Details:")
            for step_id, step_info in result["steps"].items():
                step_type = step_info.get("step_type", "service")
                service = step_info.get("service", "unknown")
                task = step_info.get("task", "unknown")
                status = step_info.get("status", "unknown")
                print(f"     {step_id}: {status} ({step_type}: {service}.{task})")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Workflow '{name}' failed: {e}")
            self.results[name] = {
                "status": "failed",
                "error": str(e),
                "success": False
            }
            return {"status": "failed", "error": str(e)}
    
    async def run_all_examples(self):
        """Run all example workflows"""
        examples_dir = Path("examples/advanced_workflows")
        
        if not examples_dir.exists():
            print(f"❌ Examples directory not found: {examples_dir}")
            return
        
        # Define parameters for each workflow
        workflow_params = {
            "data_processing": {
                "input_file": "example_data.csv",
                "output_dir": "example_results",
                "backup_dir": "example_backup"
            },
            "batch_processing": {
                "input_files": ["file1.csv", "file2.csv", "file3.csv"],
                "output_dir": "batch_results",
                "batch_size": 3
            },
            "conditional_workflow": {
                "data_type": "csv",
                "input_file": "conditional_data.csv",
                "processing_mode": "detailed"
            }
        }
        
        # Run each workflow
        for dsl_file in examples_dir.glob("*.dsl"):
            name = dsl_file.stem
            parameters = workflow_params.get(name, {})
            
            await self.run_workflow(name, dsl_file, parameters)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary of all workflow executions"""
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        
        total = len(self.results)
        successful = sum(1 for r in self.results.values() if r["success"])
        failed = total - successful
        
        print(f"Total workflows: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(successful/total)*100:.1f}%")
        
        print(f"\nDetailed Results:")
        for name, result in self.results.items():
            status_icon = "✅" if result["success"] else "❌"
            print(f"  {status_icon} {name}: {result['status']}")
            if not result["success"] and "error" in result:
                print(f"      Error: {result['error']}")
        
        if failed == 0:
            print(f"\n🎉 All workflows executed successfully!")
        else:
            print(f"\n⚠️  {failed} workflow(s) failed. Check the errors above.")

def main():
    """Main function to run all example workflows"""
    print("GrayGEMS Example Workflows Runner")
    print("=" * 60)
    
    # Create project directory
    project_dir = Path("demo/example_workflows")
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and run the workflow runner
    runner = ExampleWorkflowRunner(project_dir)
    
    try:
        asyncio.run(runner.run_all_examples())
    except KeyboardInterrupt:
        print("\n\n⚠️  Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 