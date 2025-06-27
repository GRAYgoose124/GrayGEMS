# GrayGEMS Demo

This directory contains a complete example of how to use GrayGEMS to build a JSON request/response execution API.

## Quick Start

### 1. Start the Demo Server

```bash
python start_demo.py
```

The server will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 2. Test the API

```bash
python test_demo.py
```

## Demo Features

### Services
- **Calculator**: Add, multiply, and calculate mean
- **Text Processor**: Word count and character analysis
- **Core Services**: File utilities and data processing

### Project Management
- Token-based authentication
- Project isolation
- Automatic expiration
- Metadata support

### Workflow Execution
- Dependency resolution
- Concurrent execution
- Transaction tracking
- Error handling

## Configuration

The demo uses `gems_config.json` to define services and tasks. This shows how to configure GrayGEMS for your own applications.

## Structure

```
demo/
├── __main__.py              # FastAPI application
├── start_demo.py            # Server starter script
├── test_demo.py             # Test script
├── gems_config.json         # Service configuration
├── README.md               # This file
└── entities/               # Example services
    ├── calculator/         # Calculator services
    └── text_processor/     # Text processing services
```

## Example Usage

### Create a Project
```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"name": "My Project"}, "expiration_days": 30}'
```

### Execute a Workflow
```bash
curl -X POST http://localhost:8000/projects/{project_id}/workflow \
  -H "Content-Type: application/json" \
  -H "X-Project-Token: {token}" \
  -d '{
    "workflow_data": {
      "steps": {
        "add": {
          "service": "calculator",
          "task": "add",
          "inputs": {"a": 5, "b": 3},
          "dependencies": []
        }
      }
    }
  }'
```

This demo shows how to integrate GrayGEMS into your own applications to build powerful workflow execution APIs. 