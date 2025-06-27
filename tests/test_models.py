"""
Tests for GrayGEMS core models and API validation
"""

import pytest
from pydantic import ValidationError
from typing import Dict, Any

from graygems.core.models import (
    ServiceCall,
    APIRequest,
    APIResponse,
    FileUtilsInput,
    FileUtilsOutput,
    DataProcessorInput,
    DataProcessorOutput,
)


class TestServiceCall:
    """Test ServiceCall model validation"""

    def test_valid_service_call(self):
        """Test creating a valid ServiceCall"""
        service_call = ServiceCall(
            service="file_utils",
            inputs={"operation": "write", "source_path": "test.txt"},
            given_name="test_service",
        )

        assert service_call.service == "file_utils"
        assert service_call.inputs == {"operation": "write", "source_path": "test.txt"}
        assert service_call.given_name == "test_service"

    def test_service_call_with_empty_inputs(self):
        """Test ServiceCall with empty inputs"""
        service_call = ServiceCall(
            service="test_service", inputs={}, given_name="empty_test"
        )

        assert service_call.inputs == {}

    def test_service_call_with_complex_inputs(self):
        """Test ServiceCall with complex nested inputs"""
        complex_inputs = {
            "operation": "process",
            "data": {"items": [1, 2, 3], "config": {"enabled": True}},
            "parameters": {"timeout": 30},
        }

        service_call = ServiceCall(
            service="data_processor", inputs=complex_inputs, given_name="complex_test"
        )

        assert service_call.inputs == complex_inputs


class TestAPIRequest:
    """Test APIRequest model validation"""

    def test_valid_api_request(self, valid_api_request):
        """Test creating a valid APIRequest"""
        request = APIRequest(**valid_api_request)

        assert len(request.services) == 1
        assert request.services[0].service == "file_utils"
        assert request.services[0].given_name == "write_test"

    def test_api_request_with_multiple_services(self):
        """Test APIRequest with multiple services"""
        request_data = {
            "services": [
                {
                    "service": "file_utils",
                    "inputs": {"operation": "write", "source_path": "file1.txt"},
                    "given_name": "write1",
                },
                {
                    "service": "data_processor",
                    "inputs": {"operation": "filter", "data": {"key": "value"}},
                    "given_name": "process1",
                },
            ]
        }

        request = APIRequest(**request_data)
        assert len(request.services) == 2
        assert request.services[0].given_name == "write1"
        assert request.services[1].given_name == "process1"

    def test_api_request_empty_services(self):
        """Test APIRequest with empty services list"""
        request_data = {"services": []}

        with pytest.raises(ValidationError) as exc_info:
            APIRequest(**request_data)

        # Pydantic v2 error message format
        assert "List should have at least 1 item" in str(exc_info.value)

    def test_api_request_missing_services(self):
        """Test APIRequest with missing services field"""
        with pytest.raises(ValidationError) as exc_info:
            APIRequest()

        assert "services" in str(exc_info.value)


class TestAPIResponse:
    """Test APIResponse model validation"""

    def test_valid_api_response(self):
        """Test creating a valid APIResponse"""
        response = APIResponse(
            results={"test_service": {"output": "success"}},
            project_id="test-project-123",
        )

        assert response.project_id == "test-project-123"
        assert response.results["test_service"]["output"] == "success"

    def test_api_response_with_empty_results(self):
        """Test APIResponse with empty results"""
        response = APIResponse(results={}, project_id="test-project-123")

        assert response.results == {}


class TestFileUtilsInput:
    """Test FileUtilsInput model validation"""

    def test_valid_file_utils_input(self):
        """Test creating a valid FileUtilsInput"""
        input_data = FileUtilsInput(
            operation="write", source_path="test.txt", content="Hello World"
        )

        assert input_data.operation == "write"
        assert input_data.source_path == "test.txt"
        assert input_data.content == "Hello World"

    def test_file_utils_input_optional_fields(self):
        """Test FileUtilsInput with optional fields"""
        input_data = FileUtilsInput(operation="validate")

        assert input_data.operation == "validate"
        assert input_data.source_path is None
        assert input_data.target_path is None
        assert input_data.file_type is None
        assert input_data.content is None

    def test_file_utils_input_invalid_operation(self):
        """Test FileUtilsInput with invalid operation"""
        with pytest.raises(ValidationError):
            FileUtilsInput(operation="invalid_operation")

    def test_file_utils_input_copy_operation(self):
        """Test FileUtilsInput for copy operation"""
        input_data = FileUtilsInput(
            operation="copy", source_path="source.txt", target_path="target.txt"
        )

        assert input_data.operation == "copy"
        assert input_data.source_path == "source.txt"
        assert input_data.target_path == "target.txt"

    def test_file_utils_input_move_operation(self):
        """Test FileUtilsInput for move operation"""
        input_data = FileUtilsInput(
            operation="move", source_path="old.txt", target_path="new.txt"
        )

        assert input_data.operation == "move"
        assert input_data.source_path == "old.txt"
        assert input_data.target_path == "new.txt"

    def test_file_utils_input_delete_operation(self):
        """Test FileUtilsInput for delete operation"""
        input_data = FileUtilsInput(
            operation="delete", source_path="file_to_delete.txt"
        )

        assert input_data.operation == "delete"
        assert input_data.source_path == "file_to_delete.txt"

    def test_file_utils_input_validate_operation(self):
        """Test FileUtilsInput for validate operation"""
        input_data = FileUtilsInput(
            operation="validate", source_path="file.txt", file_type=".txt"
        )

        assert input_data.operation == "validate"
        assert input_data.source_path == "file.txt"
        assert input_data.file_type == ".txt"


class TestFileUtilsOutput:
    """Test FileUtilsOutput model validation"""

    def test_valid_file_utils_output(self):
        """Test creating a valid FileUtilsOutput"""
        output = FileUtilsOutput(
            success=True,
            message="File written successfully",
            file_path="/path/to/file.txt",
            file_size=1024,
        )

        assert output.success is True
        assert output.message == "File written successfully"
        assert output.file_path == "/path/to/file.txt"
        assert output.file_size == 1024

    def test_file_utils_output_failure(self):
        """Test FileUtilsOutput for failure case"""
        output = FileUtilsOutput(success=False, message="File not found")

        assert output.success is False
        assert output.message == "File not found"
        assert output.file_path is None
        assert output.file_size is None

    def test_file_utils_output_optional_fields(self):
        """Test FileUtilsOutput with optional fields"""
        output = FileUtilsOutput(success=True, message="Operation completed")

        assert output.success is True
        assert output.message == "Operation completed"
        assert output.file_path is None
        assert output.file_size is None


class TestDataProcessorInput:
    """Test DataProcessorInput model validation"""

    def test_valid_data_processor_input(self):
        """Test creating a valid DataProcessorInput"""
        input_data = DataProcessorInput(
            operation="filter",
            data={"key1": "value1", "key2": "value2"},
            parameters={"key": "key1", "value": "value1"},
        )

        assert input_data.operation == "filter"
        assert input_data.data == {"key1": "value1", "key2": "value2"}
        assert input_data.parameters == {"key": "key1", "value": "value1"}

    def test_data_processor_input_optional_parameters(self):
        """Test DataProcessorInput with optional parameters"""
        input_data = DataProcessorInput(
            operation="sort",
            data={"items": [1, 2, 3, 4, 5]},  # Fixed: use dict instead of list
        )

        assert input_data.operation == "sort"
        assert input_data.data == {"items": [1, 2, 3, 4, 5]}
        assert input_data.parameters is None

    def test_data_processor_input_complex_data(self):
        """Test DataProcessorInput with complex data structures"""
        complex_data = {
            "users": [
                {"id": 1, "name": "Alice", "age": 30},
                {"id": 2, "name": "Bob", "age": 25},
                {"id": 3, "name": "Charlie", "age": 35},
            ],
            "metadata": {"total_count": 3, "last_updated": "2023-01-01"},
        }

        input_data = DataProcessorInput(
            operation="aggregate",
            data=complex_data,
            parameters={"key": "age", "operation": "avg"},
        )

        assert input_data.operation == "aggregate"
        assert input_data.data == complex_data
        assert input_data.parameters["key"] == "age"
        assert input_data.parameters["operation"] == "avg"

    def test_data_processor_input_empty_data(self):
        """Test DataProcessorInput with empty data (should fail)"""
        with pytest.raises(ValidationError):
            DataProcessorInput(operation="filter", data={})


class TestDataProcessorOutput:
    """Test DataProcessorOutput model validation"""

    def test_valid_data_processor_output(self):
        """Test creating a valid DataProcessorOutput"""
        output = DataProcessorOutput(
            success=True,
            processed_data={"filtered": [1, 2, 3]},
            statistics={"count": 3, "operation": "filter"},
        )

        assert output.success is True
        assert output.processed_data == {"filtered": [1, 2, 3]}
        assert output.statistics["count"] == 3
        assert output.statistics["operation"] == "filter"

    def test_data_processor_output_failure(self):
        """Test DataProcessorOutput for failure case"""
        output = DataProcessorOutput(
            success=False, processed_data={}, statistics={"error": "Invalid operation"}
        )

        assert output.success is False
        assert output.processed_data == {}
        assert output.statistics["error"] == "Invalid operation"

    def test_data_processor_output_optional_statistics(self):
        """Test DataProcessorOutput with optional statistics"""
        output = DataProcessorOutput(success=True, processed_data={"result": "success"})

        assert output.success is True
        assert output.processed_data == {"result": "success"}
        assert output.statistics is None


class TestModelSerialization:
    """Test model serialization and deserialization"""

    def test_service_call_serialization(self):
        """Test ServiceCall model serialization"""
        service_call = ServiceCall(
            service="test_service", inputs={"param": "value"}, given_name="test"
        )

        # Test model_dump
        data = service_call.model_dump()
        assert data["service"] == "test_service"
        assert data["inputs"]["param"] == "value"
        assert data["given_name"] == "test"

        # Test model_dump_json
        json_str = service_call.model_dump_json()
        assert "test_service" in json_str
        assert "param" in json_str

    def test_api_request_serialization(self, valid_api_request):
        """Test APIRequest model serialization"""
        request = APIRequest(**valid_api_request)

        data = request.model_dump()
        assert "services" in data
        assert len(data["services"]) == 1

        json_str = request.model_dump_json()
        assert "file_utils" in json_str

    def test_file_utils_input_serialization(self):
        """Test FileUtilsInput model serialization"""
        input_data = FileUtilsInput(
            operation="write", source_path="test.txt", content="Hello"
        )

        data = input_data.model_dump()
        assert data["operation"] == "write"
        assert data["source_path"] == "test.txt"
        assert data["content"] == "Hello"

    def test_model_validation_with_invalid_data(self):
        """Test model validation with invalid data"""
        # Test ServiceCall with missing required fields
        with pytest.raises(ValidationError) as exc_info:
            ServiceCall(service="test")

        assert "given_name" in str(exc_info.value)

        # Test FileUtilsInput with invalid operation
        with pytest.raises(ValidationError):
            FileUtilsInput(operation="invalid_op")

        # Test APIRequest with invalid structure
        with pytest.raises(ValidationError):
            APIRequest(services="not_a_list")


class TestModelValidation:
    """Test model validation rules"""

    def test_service_call_validation_rules(self):
        """Test ServiceCall validation rules"""
        # Valid service call
        service_call = ServiceCall(
            service="valid_service", inputs={"key": "value"}, given_name="valid_name"
        )
        assert service_call.service == "valid_service"

        # Test with empty service name
        with pytest.raises(ValidationError):
            ServiceCall(service="", inputs={}, given_name="test")

    def test_api_request_validation_rules(self):
        """Test APIRequest validation rules"""
        # Valid request
        request = APIRequest(
            services=[ServiceCall(service="test", inputs={}, given_name="test")]
        )
        assert len(request.services) == 1

        # Test with empty services list
        with pytest.raises(ValidationError):
            APIRequest(services=[])

    def test_file_utils_input_validation_rules(self):
        """Test FileUtilsInput validation rules"""
        # Valid input
        input_data = FileUtilsInput(operation="write")
        assert input_data.operation == "write"

        # Test with invalid operation
        with pytest.raises(ValidationError):
            FileUtilsInput(operation="invalid_operation")

    def test_data_processor_input_validation_rules(self):
        """Test DataProcessorInput validation rules"""
        # Valid input
        input_data = DataProcessorInput(operation="filter", data={"key": "value"})
        assert input_data.operation == "filter"
        assert input_data.data == {"key": "value"}

        # Test with empty data
        with pytest.raises(ValidationError):
            DataProcessorInput(operation="filter", data={})
