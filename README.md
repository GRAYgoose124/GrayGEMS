# GrayGEMS

GrayGEMS is a flexible, configuration-driven service orchestration framework that allows you to define entities, services, and tasks via JSON configuration files. It provides a robust API for executing workflows with proper project management and authentication.

## Features

- **Configuration-Driven**: Define all entities, services, and tasks via JSON configuration
- **Dynamic Service Registration**: Import and register services at runtime
- **Project Management**: Token-based authentication and project isolation
- **Workflow Execution**: Execute complex workflows with dependency resolution
- **Error Handling**: Comprehensive error handling and logging
- **CLI Tools**: Command-line interface for configuration management

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd GrayGEMS

# Install dependencies
pip install -e .
```

## Quick Start

### 1. Create a Configuration

Use the GrayGEMS CLI to create and manage configurations:

```bash
# Create a new configuration
python -m graygems.cli create config.json --name "My GrayGEMS Instance"

# Add an entity
python -m graygems.cli add-entity config.json calculator "Calculator services" "demo.entities.calculator"

# Add a service to the entity
python -m graygems.cli add-service config.json calculator math "Mathematical operations"

# Add a task to the service
python -m graygems.cli add-task config.json calculator math add "AddInput" "AddOutput" "Add two numbers"

# Validate the configuration
python -m graygems.cli validate config.json

# List configuration details
python -m graygems.cli list config.json
```

### 2. Run the Demo

The demo shows how to use GrayGEMS in a real application:

```bash
# Navigate to demo directory
cd demo

# Install demo dependencies
pip install -r requirements.txt

# Start the demo server
python start_demo.py

# In another terminal, run tests
python test_demo.py
```

## Configuration Format

GrayGEMS uses JSON configuration files to define the entire system:

```json
{
  "name": "My GrayGEMS Instance",
  "version": "1.0.0",
  "description": "A custom GrayGEMS configuration",
  "settings": {
    "default_expiration_days": 30,
    "max_projects_per_user": 100
  },
  "entities": {
    "calculator": {
      "enabled": true,
      "description": "Calculator services",
      "module": "demo.entities.calculator",
      "services": {
        "math": {
          "enabled": true,
          "tasks": {
            "add": {
              "enabled": true,
              "description": "Add two numbers",
              "input_model": "AddInput",
              "output_model": "AddOutput"
            }
          }
        }
      }
    }
  },
  "core_services": {
    "file_utils": {
      "enabled": true,
      "description": "File utility services",
      "module": "graygems.core.tasks.file_utils",
      "tasks": {
        "read_file": {
          "enabled": true,
          "description": "Read a file"
        }
      }
    }
  }
}
```

## CLI Commands

The GrayGEMS CLI provides comprehensive configuration management:

### Configuration Management
- `create` - Create a new configuration file
- `validate` - Validate a configuration file
- `list` - List configuration details

### Entity Management
- `add-entity` - Add a new entity
- `enable entity` - Enable/disable an entity

### Service Management
- `add-service` - Add a new service to an entity
- `enable service` - Enable/disable a service

### Task Management
- `add-task` - Add a new task to a service
- `enable task` - Enable/disable a task

## API Usage

### Create a Project
```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "description": "Test project"}'
```

### Execute a Workflow
```bash
curl -X POST http://localhost:8000/projects/{project_id}/workflow \
  -H "Content-Type: application/json" \
  -H "X-Project-Token: {token}" \
  -d '{
    "workflow": {
      "name": "Calculator Workflow",
      "steps": [
        {
          "id": "add",
          "service": "calculator",
          "task": "add",
          "inputs": {"a": 5, "b": 3},
          "outputs": ["result"]
        }
      ]
    }
  }'
```

## Project Structure

```
GrayGEMS/
├── graygems/                 # Core library
│   ├── core/                # Core components
│   │   ├── config.py        # Configuration management
│   │   ├── config_manager.py # Configuration CLI tools
│   │   ├── registry.py      # Service registry
│   │   ├── workflow.py      # Workflow execution
│   │   ├── project.py       # Project management
│   │   └── error_handler.py # Error handling
│   └── cli.py              # Command-line interface
├── demo/                    # Demo application
│   ├── __main__.py         # Demo server
│   ├── entities/           # Demo entities
│   ├── gems_config.json    # Demo configuration
│   ├── start_demo.py       # Demo starter
│   └── test_demo.py        # Demo tests
└── README.md               # This file
```

## Core Components

### ConfigManager
Manages GrayGEMS configuration files, validates configurations, and provides a CLI interface for configuration management.

### ServiceRegistry
Dynamically registers and manages services based on configuration. Supports importing services from modules and validating task definitions.

### WorkflowManager
Executes workflows with dependency resolution, concurrent task execution, and proper error handling.

### ProjectManager
Manages projects with token-based authentication, project isolation, and lifecycle management.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Demo

The `demo/` directory contains a complete example showing how to use GrayGEMS:

- **Calculator Services** - Basic mathematical operations
- **Text Processing** - Word and character analysis
- **Token Authentication** - Secure project access
- **Workflow Execution** - Complex multi-step workflows
- **Configuration Management** - JSON-based service definition

Run the demo to see GrayGEMS in action:

```bash
cd demo
python start_demo_server.py
```

Then test it with:

```bash
python run_demo_client.py
```

