#!/usr/bin/env python3
"""
GrayGEMS CLI Tool
Command-line interface for managing GrayGEMS configurations
"""

import argparse
import sys
from pathlib import Path
from .core.config_manager import ConfigManager

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
    parser = argparse.ArgumentParser(description="GrayGEMS Configuration Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
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
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Set enable flag for enable/disable command
    if hasattr(args, 'disable'):
        args.enable = not args.disable
    
    args.func(args)

if __name__ == "__main__":
    main() 