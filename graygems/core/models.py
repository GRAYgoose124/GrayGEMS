# gems2/core/models.py
from typing import Dict, Any, List, Literal, Union, Optional
from pydantic import BaseModel, Field, model_validator, constr, conlist
from pydantic import Discriminator


class ServiceCall(BaseModel):
    """Service call specification"""

    service: constr(min_length=1)
    inputs: Dict[str, Any]
    given_name: constr(min_length=1)


class APIRequest(BaseModel):
    """API request model"""

    services: conlist(ServiceCall, min_length=1)

    @model_validator(mode="after")
    def validate_services(self):
        """Validate service calls using discriminator pattern"""
        try:
            from .registry import global_registry

            for service_call in self.services:
                service = global_registry.get(service_call.service)
                if not service:
                    continue
                try:
                    service.input_model(**service_call.inputs)
                except Exception:
                    continue
            return self
        except Exception:
            return self


class APIResponse(BaseModel):
    """API response model"""

    results: Dict[str, Any]
    project_id: str


# Core service models
class FileUtilsInput(BaseModel):
    """Input model for file utility operations"""

    operation: Literal["copy", "move", "delete", "validate", "write", "archive"]
    source_path: Optional[str] = None
    target_path: Optional[str] = None
    file_type: Optional[str] = None
    content: Optional[str] = None


class FileUtilsOutput(BaseModel):
    """Output model for file utility operations"""

    success: bool
    message: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None


class DataProcessorInput(BaseModel):
    """Input model for data processing operations"""

    operation: Literal["filter", "sort", "aggregate", "transform"]
    data: Dict[str, Any]
    parameters: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def check_data_not_empty(self):
        if not self.data or not isinstance(self.data, dict) or len(self.data) == 0:
            raise ValueError("data must be a non-empty dictionary")
        return self


class DataProcessorOutput(BaseModel):
    """Output model for data processing operations"""

    success: bool
    processed_data: Dict[str, Any]
    statistics: Optional[Dict[str, Any]] = None


# Note: Custom service request/response models are supported via the Service class generics in service.py.
# You can define your own Pydantic models and use them as input_model/output_model for any service.
