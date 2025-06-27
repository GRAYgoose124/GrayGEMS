#!/usr/bin/env python3
"""
GrayGEMS CLI Tool
Command-line interface for managing GrayGEMS configurations
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from .core.project_manager import ProjectManager
from .core.registry import global_registry
from .core.config_manager import ConfigManager
from .core.workflow import WorkflowManager
from .core.workflow_dsl import WorkflowDSL, template_registry

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def load_config(config_path: Optional[Path] = None) -> ConfigManager:
    """Load configuration"""
    config_manager = ConfigManager()
    
    if config_path and config_path.exists():
        config_manager.load_config(config_path)
    else:
        # Try to find config in current directory
        default_config = Path("gems_config.json")
        if default_config.exists():
            config_manager.load_config(default_config)
        else:
            logger.warning("No configuration file found. Using default settings.")
    
    return config_manager

async def run_workflow(project_id: str, workflow_file: Path, config_path: Optional[Path] = None):
    """Run a workflow from a JSON file"""
    setup_logging()
    
    # Load configuration
    config_manager = load_config(config_path)
    
    # Register services
    config_manager.register_services(config_manager.config, global_registry)
    
    # Create project manager
    project_manager = ProjectManager()
    project = project_manager.get_or_create_project(project_id)
    
    # Load workflow
    with open(workflow_file, 'r') as f:
        workflow_data = json.load(f)
    
    # Create workflow manager
    workflow_manager = WorkflowManager(global_registry, project.project_dir)
    
    # Execute workflow
    result = await workflow_manager.execute_workflow(project_id, workflow_data, project.project_dir)
    
    print(json.dumps(result, indent=2, default=str))

async def run_dsl_workflow(project_id: str, dsl_file: Path, config_path: Optional[Path] = None, **parameters):
    """Run a workflow from DSL code"""
    setup_logging()
    
    # Load configuration
    config_manager = load_config(config_path)
    
    # Register services
    config_manager.register_services(config_manager.config, global_registry)
    
    # Create project manager
    project_manager = ProjectManager()
    project = project_manager.get_or_create_project(project_id)
    
    # Load DSL code
    with open(dsl_file, 'r') as f:
        dsl_code = f.read()
    
    # Create workflow manager
    workflow_manager = WorkflowManager(global_registry, project.project_dir)
    
    # Execute DSL workflow
    result = await workflow_manager.execute_dsl_workflow(project_id, dsl_code, project.project_dir, **parameters)
    
    print(json.dumps(result, indent=2, default=str))

async def run_template_workflow(project_id: str, template_name: str, config_path: Optional[Path] = None, **parameters):
    """Run a workflow from a template"""
    setup_logging()
    
    # Load configuration
    config_manager = load_config(config_path)
    
    # Register services
    config_manager.register_services(config_manager.config, global_registry)
    
    # Create project manager
    project_manager = ProjectManager()
    project = project_manager.get_or_create_project(project_id)
    
    # Create workflow manager
    workflow_manager = WorkflowManager(global_registry, project.project_dir)
    
    # Execute template workflow
    result = await workflow_manager.execute_template_workflow(project_id, template_name, project.project_dir, **parameters)
    
    print(json.dumps(result, indent=2, default=str))

def list_templates():
    """List available workflow templates"""
    templates = template_registry.list_templates()
    
    if not templates:
        print("No templates available.")
        return
    
    print("Available workflow templates:")
    for template_name in templates:
        template = template_registry.get(template_name)
        print(f"  {template_name}")
        if template.parameters:
            print(f"    Parameters: {', '.join(template.parameters.keys())}")

def show_template(template_name: str):
    """Show details of a specific template"""
    template = template_registry.get(template_name)
    if not template:
        print(f"Template '{template_name}' not found.")
        return
    
    print(f"Template: {template_name}")
    print(f"Parameters: {template.parameters}")
    print("\nDSL Code:")
    print(template.dsl_code)

def compile_dsl(dsl_file: Path, output_file: Optional[Path] = None):
    """Compile DSL code to JSON workflow"""
    setup_logging()
    
    # Load DSL code
    with open(dsl_file, 'r') as f:
        dsl_code = f.read()
    
    # Parse DSL
    dsl_parser = WorkflowDSL()
    workflow_data = dsl_parser.parse_workflow(dsl_code)
    
    # Output result
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(workflow_data, f, indent=2)
        print(f"Compiled workflow saved to {output_file}")
    else:
        print(json.dumps(workflow_data, indent=2))

def create_template(template_name: str, dsl_file: Path, parameters: Dict[str, Any] = None):
    """Create a new workflow template"""
    setup_logging()
    
    # Load DSL code
    with open(dsl_file, 'r') as f:
        dsl_code = f.read()
    
    # Create template
    from .core.workflow_dsl import WorkflowTemplate
    template = WorkflowTemplate(template_name, dsl_code, parameters or {})
    
    # Register template
    template_registry.register(template)
    
    print(f"Template '{template_name}' created and registered.")

def create_config(args):
    """Create a new configuration file"""
    config_manager = ConfigManager()
    config_path = Path(args.config_path)
    
    try:
        config = config_manager.create_config(
            config_path,
            name=args.name,
            version=args.version
        )
        print(f"✅ Created configuration: {config_path}")
        print(f"📝 Name: {config.name}")
        print(f"📦 Version: {config.version}")
    except Exception as e:
        print(f"❌ Failed to create configuration: {e}")
        sys.exit(1)

def validate_config(args):
    """Validate a configuration file"""
    config_manager = ConfigManager()
    config_path = Path(args.config_path)
    
    try:
        config = config_manager.load_config(config_path)
        errors = config_manager.validate_config()
        
        if errors:
            print(f"❌ Configuration validation failed:")
            for error in errors:
                print(f"   - {error}")
            sys.exit(1)
        else:
            print(f"✅ Configuration is valid: {config_path}")
            summary = config_manager.get_config_summary()
            print(f"📝 Name: {summary['name']}")
            print(f"📦 Version: {summary['version']}")
            print(f"🏗️ Entities: {len(summary['entities'])}")
            print(f"🔧 Core Services: {len(summary['core_services'])}")
    except Exception as e:
        print(f"❌ Failed to validate configuration: {e}")
        sys.exit(1)

def list_config(args):
    """List configuration details"""
    config_manager = ConfigManager()
    config_path = Path(args.config_path)
    
    try:
        config = config_manager.load_config(config_path)
        summary = config_manager.get_config_summary()
        
        print(f"📋 Configuration: {summary['name']} v{summary['version']}")
        print(f"📝 Description: {summary['description']}")
        print()
        
        print("🏗️ Entities:")
        for entity_name, entity in summary['entities'].items():
            status = "✅" if entity['enabled'] else "❌"
            print(f"  {status} {entity_name}: {entity['description']}")
            
            for service_name, service in entity['services'].items():
                service_status = "✅" if service['enabled'] else "❌"
                print(f"    {service_status} {service_name}: {len(service['tasks'])} tasks")
        
        print("\n🔧 Core Services:")
        for service_name, service in summary['core_services'].items():
            status = "✅" if service['enabled'] else "❌"
            print(f"  {status} {service_name}: {service['description']} ({len(service['tasks'])} tasks)")
            
    except Exception as e:
        print(f"❌ Failed to list configuration: {e}")
        sys.exit(1)

def add_entity(args):
    """Add an entity to configuration"""
    config_manager = ConfigManager()
    config_path = Path(args.config_path)
    
    try:
        config = config_manager.load_config(config_path)
        success = config_manager.add_entity(args.entity_name, args.description, args.module)
        
        if success:
            config_manager.save_config(config, config_path)
            print(f"✅ Added entity: {args.entity_name}")
        else:
            print(f"❌ Failed to add entity: {args.entity_name}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to add entity: {e}")
        sys.exit(1)

def add_service(args):
    """Add a service to an entity"""
    config_manager = ConfigManager()
    config_path = Path(args.config_path)
    
    try:
        config = config_manager.load_config(config_path)
        success = config_manager.add_service(args.entity_name, args.service_name, args.description)
        
        if success:
            config_manager.save_config(config, config_path)
            print(f"✅ Added service: {args.entity_name}.{args.service_name}")
        else:
            print(f"❌ Failed to add service: {args.entity_name}.{args.service_name}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to add service: {e}")
        sys.exit(1)

def add_task(args):
    """Add a task to a service"""
    config_manager = ConfigManager()
    config_path = Path(args.config_path)
    
    try:
        config = config_manager.load_config(config_path)
        success = config_manager.add_task(
            args.entity_name, 
            args.service_name, 
            args.task_name,
            args.input_model,
            args.output_model,
            args.description
        )
        
        if success:
            config_manager.save_config(config, config_path)
            print(f"✅ Added task: {args.entity_name}.{args.service_name}.{args.task_name}")
        else:
            print(f"❌ Failed to add task: {args.entity_name}.{args.service_name}.{args.task_name}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to add task: {e}")
        sys.exit(1)

def enable_disable(args):
    """Enable or disable entities, services, or tasks"""
    config_manager = ConfigManager()
    config_path = Path(args.config_path)
    
    try:
        config = config_manager.load_config(config_path)
        success = False
        
        if args.type == "entity":
            success = config_manager.enable_entity(args.name, args.enable)
        elif args.type == "service":
            success = config_manager.enable_service(args.entity_name, args.name, args.enable)
        elif args.type == "task":
            success = config_manager.enable_task(args.entity_name, args.service_name, args.name, args.enable)
        
        if success:
            config_manager.save_config(config, config_path)
            action = "enabled" if args.enable else "disabled"
            print(f"✅ {action.capitalize()}: {args.name}")
        else:
            print(f"❌ Failed to {'enable' if args.enable else 'disable'}: {args.name}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to modify configuration: {e}")
        sys.exit(1)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="GrayGEMS Command Line Interface")
    parser.add_argument("--config", type=Path, help="Path to configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run workflow command
    run_parser = subparsers.add_parser("run", help="Run a workflow from JSON file")
    run_parser.add_argument("project_id", help="Project ID")
    run_parser.add_argument("workflow_file", type=Path, help="Path to workflow JSON file")
    
    # Run DSL workflow command
    dsl_parser = subparsers.add_parser("run-dsl", help="Run a workflow from DSL file")
    dsl_parser.add_argument("project_id", help="Project ID")
    dsl_parser.add_argument("dsl_file", type=Path, help="Path to DSL file")
    dsl_parser.add_argument("--param", "-p", action="append", nargs=2, metavar=("KEY", "VALUE"),
                           help="Parameter key-value pair")
    
    # Run template workflow command
    template_parser = subparsers.add_parser("run-template", help="Run a workflow from template")
    template_parser.add_argument("project_id", help="Project ID")
    template_parser.add_argument("template_name", help="Template name")
    template_parser.add_argument("--param", "-p", action="append", nargs=2, metavar=("KEY", "VALUE"),
                                help="Parameter key-value pair")
    
    # List templates command
    subparsers.add_parser("list-templates", help="List available workflow templates")
    
    # Show template command
    show_parser = subparsers.add_parser("show-template", help="Show template details")
    show_parser.add_argument("template_name", help="Template name")
    
    # Compile DSL command
    compile_parser = subparsers.add_parser("compile-dsl", help="Compile DSL to JSON workflow")
    compile_parser.add_argument("dsl_file", type=Path, help="Path to DSL file")
    compile_parser.add_argument("--output", "-o", type=Path, help="Output JSON file")
    
    # Create template command
    create_parser = subparsers.add_parser("create-template", help="Create a new workflow template")
    create_parser.add_argument("template_name", help="Template name")
    create_parser.add_argument("dsl_file", type=Path, help="Path to DSL file")
    create_parser.add_argument("--param", "-p", action="append", nargs=2, metavar=("KEY", "VALUE"),
                              help="Default parameter key-value pair")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new configuration")
    create_parser.add_argument("config_path", help="Path to configuration file")
    create_parser.add_argument("--name", default="GrayGEMS Configuration", help="Configuration name")
    create_parser.add_argument("--version", default="1.0.0", help="Configuration version")
    create_parser.set_defaults(func=create_config)
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a configuration")
    validate_parser.add_argument("config_path", help="Path to configuration file")
    validate_parser.set_defaults(func=validate_config)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List configuration details")
    list_parser.add_argument("config_path", help="Path to configuration file")
    list_parser.set_defaults(func=list_config)
    
    # Add entity command
    entity_parser = subparsers.add_parser("add-entity", help="Add an entity")
    entity_parser.add_argument("config_path", help="Path to configuration file")
    entity_parser.add_argument("entity_name", help="Entity name")
    entity_parser.add_argument("description", help="Entity description")
    entity_parser.add_argument("module", help="Entity module path")
    entity_parser.set_defaults(func=add_entity)
    
    # Add service command
    service_parser = subparsers.add_parser("add-service", help="Add a service")
    service_parser.add_argument("config_path", help="Path to configuration file")
    service_parser.add_argument("entity_name", help="Entity name")
    service_parser.add_argument("service_name", help="Service name")
    service_parser.add_argument("description", help="Service description")
    service_parser.set_defaults(func=add_service)
    
    # Add task command
    task_parser = subparsers.add_parser("add-task", help="Add a task")
    task_parser.add_argument("config_path", help="Path to configuration file")
    task_parser.add_argument("entity_name", help="Entity name")
    task_parser.add_argument("service_name", help="Service name")
    task_parser.add_argument("task_name", help="Task name")
    task_parser.add_argument("input_model", help="Input model class")
    task_parser.add_argument("output_model", help="Output model class")
    task_parser.add_argument("--description", default="", help="Task description")
    task_parser.set_defaults(func=add_task)
    
    # Enable/disable command
    enable_parser = subparsers.add_parser("enable", help="Enable or disable components")
    enable_parser.add_argument("config_path", help="Path to configuration file")
    enable_parser.add_argument("type", choices=["entity", "service", "task"], help="Component type")
    enable_parser.add_argument("name", help="Component name")
    enable_parser.add_argument("--entity-name", help="Entity name (for services/tasks)")
    enable_parser.add_argument("--service-name", help="Service name (for tasks)")
    enable_parser.add_argument("--disable", action="store_true", help="Disable instead of enable")
    enable_parser.set_defaults(func=enable_disable)
    
    args = parser.parse_args()
    
    if args.verbose:
        setup_logging(verbose=True)
    
    if args.command == "run":
        asyncio.run(run_workflow(args.project_id, args.workflow_file, args.config))
    
    elif args.command == "run-dsl":
        # Parse parameters
        parameters = {}
        if args.param:
            for key, value in args.param:
                # Try to parse as JSON, otherwise treat as string
                try:
                    parameters[key] = json.loads(value)
                except json.JSONDecodeError:
                    parameters[key] = value
        
        asyncio.run(run_dsl_workflow(args.project_id, args.dsl_file, args.config, **parameters))
    
    elif args.command == "run-template":
        # Parse parameters
        parameters = {}
        if args.param:
            for key, value in args.param:
                # Try to parse as JSON, otherwise treat as string
                try:
                    parameters[key] = json.loads(value)
                except json.JSONDecodeError:
                    parameters[key] = value
        
        asyncio.run(run_template_workflow(args.project_id, args.template_name, args.config, **parameters))
    
    elif args.command == "list-templates":
        list_templates()
    
    elif args.command == "show-template":
        show_template(args.template_name)
    
    elif args.command == "compile-dsl":
        compile_dsl(args.dsl_file, args.output)
    
    elif args.command == "create-template":
        # Parse parameters
        parameters = {}
        if args.param:
            for key, value in args.param:
                # Try to parse as JSON, otherwise treat as string
                try:
                    parameters[key] = json.loads(value)
                except json.JSONDecodeError:
                    parameters[key] = value
        
        create_template(args.template_name, args.dsl_file, parameters)
    
    elif args.command == "create":
        args.func(args)
    
    elif args.command == "validate":
        args.func(args)
    
    elif args.command == "list":
        args.func(args)
    
    elif args.command == "add-entity":
        args.func(args)
    
    elif args.command == "add-service":
        args.func(args)
    
    elif args.command == "add-task":
        args.func(args)
    
    elif args.command == "enable":
        args.func(args)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 