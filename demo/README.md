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
# Run comprehensive tests
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

### File Management
- **File Downloads**: Direct file downloads from project directories
- **Archive Creation**: ZIP archives with metadata
- **Client Downloads**: Test scripts save files to `demo/downloads/` for organization

## Configuration

The demo uses `gems_config.json` to define services and tasks. This shows how to configure GrayGEMS for your own applications.

## Structure

```
demo/
├── __main__.py              # FastAPI application
├── start_demo.py            # Server starter script
├── test_demo.py             # Comprehensive test script
├── gems_config.json         # Service configuration
├── README.md               # This file
├── downloads/              # Downloaded files (created by test scripts)
├── projects/               # Project directories (created by server)
└── entities/               # Example services
    ├── calculator/         # Calculator services
    └── text_processor/     # Text processing services
```

## Architecture

### Server Side
- **Projects Directory**: Server manages project files in `demo/projects/`
- **File Storage**: All project files and archives stored in project directories
- **Download Endpoints**: Serve files directly from project directories

### Client Side
- **Downloads Directory**: Test scripts save downloaded files to `demo/downloads/`
- **File Organization**: Client-side organization of downloaded files
- **Test Results**: API responses saved to `demo/test_results/`

## Example Usage

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
      "steps": {
        "add": {
          "service": "calculator.math",
          "task": "add",
          "inputs": {"a": 5, "b": 3},
          "dependencies": []
        }
      }
    }
  }'
```

### Download Files
```bash
# Download a specific file
curl -X GET http://localhost:8000/projects/{project_id}/download/outputs/result.txt \
  -H "X-Project-Token: {token}" \
  --output downloaded_file.txt

# Create and download project archive
curl -X POST http://localhost:8000/projects/{project_id}/archive \
  -H "X-Project-Token: {token}"

curl -X GET http://localhost:8000/projects/{project_id}/download/{archive_filename} \
  -H "X-Project-Token: {token}" \
  --output project_archive.zip
```

## Improvements Made

### 1. Enhanced File Downloads
- Files are now returned as actual downloadable content instead of metadata
- Proper content-type headers for different file types
- Direct file serving from project directories
- Client-side file organization in downloads directory

### 2. Improved Archive Functionality
- Archives are created with proper ZIP compression
- Archive metadata is included in the ZIP file
- Archives stored in project directories
- Better error handling and validation

### 3. Correct Architecture
- Server only manages project directories
- Client handles downloads directory organization
- Clear separation of server and client responsibilities
- Proper file path handling and security

### 4. Enhanced Error Handling
- Better error messages and logging
- Proper HTTP status codes
- Graceful fallbacks for file operations
- Security improvements for file paths

This demo shows how to integrate GrayGEMS into your own applications to build powerful workflow execution APIs with robust file management capabilities. 