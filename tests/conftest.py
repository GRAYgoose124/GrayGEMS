"""
Pytest configuration and common fixtures for GrayGEMS tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

from graygems.core.registry import ServiceRegistry
from graygems.core.config_manager import ConfigManager
from graygems.core.project_manager import ProjectManager
from graygems.core.workflow import WorkflowManager
from graygems.core.project import Project, ProjectConfig
from graygems.core.service import Service, Task
from graygems.core.models import FileUtilsInput, FileUtilsOutput, DataProcessorInput, DataProcessorOutput


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp(prefix="graygems_test_"))
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def test_config_data():
    """Sample configuration data for testing"""
    return {
        "name": "Test GrayGEMS Configuration",
        "version": "1.0.0",
        "description": "Test configuration for unit tests",
        "settings": {
            "default_expiration_days": 30,
            "max_projects_per_user": 100,
            "auto_cleanup_expired": True
        },
        "entities": {
            "calculator": {
                "enabled": True,
                "description": "Calculator services",
                "module": "demo.entities.calculator.calculator_tasks",
                "services": {
                    "math": {
                        "enabled": True,
                        "description": "Basic mathematical operations",
                        "input_model": "MathInput",
                        "output_model": "MathOutput",
                        "task_func": "add",
                        "dependencies": []
                    }
                }
            }
        },
        "core_services": {
            "file_utils": {
                "enabled": True,
                "description": "Core file utility operations",
                "module": "graygems.core.tasks.file_utils",
                "tasks": {
                    "process_file": {
                        "enabled": True,
                        "description": "Process file operations",
                        "input_model": "FileUtilsInput",
                        "output_model": "FileUtilsOutput"
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_service():
    """Create a mock service for testing"""
    service = Mock(spec=Service)
    service.description = "Test Service"
    service.input_model = None
    service.output_model = None
    service.tasks = {}
    service.get_task.return_value = None
    return service


@pytest.fixture
def mock_task():
    """Create a mock task for testing"""
    task = Mock(spec=Task)
    task.execute = Mock()
    return task


@pytest.fixture
def service_registry():
    """Create a fresh service registry for testing"""
    return ServiceRegistry()


@pytest.fixture
def config_manager():
    """Create a fresh config manager for testing"""
    return ConfigManager()


@pytest.fixture
def project_manager(temp_dir):
    """Create a project manager with temporary directory"""
    return ProjectManager(temp_dir)


@pytest.fixture
def workflow_manager(service_registry, temp_dir):
    """Create a workflow manager for testing"""
    return WorkflowManager(service_registry, temp_dir)


@pytest.fixture
def sample_project_config():
    """Create a sample project configuration"""
    return ProjectConfig(
        project_id="test-project-123",
        metadata={
            "name": "Test Project",
            "description": "A test project",
            "status": "created"
        }
    )


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing"""
    return {
        "name": "Test Workflow",
        "steps": {
            "add": {
                "service": "calculator.math",
                "task": "add",
                "inputs": {"a": 5, "b": 3},
                "dependencies": []
            },
            "multiply": {
                "service": "calculator.math",
                "task": "multiply",
                "inputs": {"a": "$add.result", "b": 2},
                "dependencies": ["add"]
            }
        }
    }


@pytest.fixture
def valid_api_request():
    """Valid API request for testing"""
    return {
        "services": [
            {
                "service": "file_utils",
                "inputs": {
                    "operation": "write",
                    "source_path": "test.txt",
                    "content": "Hello World"
                },
                "given_name": "write_test"
            }
        ]
    }


@pytest.fixture
def invalid_api_request():
    """Invalid API request for testing"""
    return {
        "services": [
            {
                "service": "nonexistent_service",
                "inputs": {"invalid": "data"},
                "given_name": "invalid_test"
            }
        ]
    }


@pytest.fixture
def file_utils_input():
    """Valid FileUtilsInput for testing"""
    return FileUtilsInput(
        operation="write",
        source_path="test.txt",
        content="Test content"
    )


@pytest.fixture
def data_processor_input():
    """Valid DataProcessorInput for testing"""
    return DataProcessorInput(
        operation="filter",
        data={"key1": "value1", "key2": "value2"},
        parameters={"key": "key1", "value": "value1"}
    )


class AsyncMock(Mock):
    """Mock that supports async/await"""
    
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@pytest.fixture
def async_task():
    """Create an async mock task for testing"""
    task = AsyncMock(spec=Task)
    task.execute = AsyncMock()
    return task 