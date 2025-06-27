# gems2/core/models.py
from typing import Dict, Any, List, Literal, Union, Optional
from pydantic import BaseModel, Field, model_validator
from pydantic import Discriminator

class ServiceCall(BaseModel):
    """Service call specification"""
    service: str
    inputs: Dict[str, Any]
    given_name: str

class APIRequest(BaseModel):
    """API request model"""
    services: List["ServiceCall"]
    
    @model_validator(mode='after')
    def validate_services(self):
        """Validate service calls using discriminator pattern"""
        try:
            from .registry import global_registry
            
            for service_call in self.services:
                service = global_registry.get(service_call.service)
                if not service:
                    # Don't raise error here, let the workflow handle it
                    continue
                
                # Validate inputs against service's InputModel
                try:
                    service.input_model(**service_call.inputs)
                except Exception as e:
                    # Don't raise error here, let the workflow handle it
                    continue
            
            return self
        except Exception:
            # If validation fails, still return self to avoid breaking the API
            return self

class APIResponse(BaseModel):
    """API response model"""
    results: Dict[str, Any]
    project_id: str

# Core service models
class FileUtilsInput(BaseModel):
    """Input model for file utility operations"""
    operation: str  # "copy", "move", "delete", "validate", "write"
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
    operation: str  # "filter", "sort", "aggregate", "transform"
    data: Dict[str, Any]
    parameters: Optional[Dict[str, Any]] = None

class DataProcessorOutput(BaseModel):
    """Output model for data processing operations"""
    success: bool
    processed_data: Dict[str, Any]
    statistics: Optional[Dict[str, Any]] = None