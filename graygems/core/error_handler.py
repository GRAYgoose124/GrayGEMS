import traceback
import logging
from typing import Dict, Any, Optional, Union
from fastapi import HTTPException, Request, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GrayGEMSError(Exception):
    """Base exception for GrayGEMS errors"""

    def __init__(
        self,
        message: str,
        error_type: str = "graygems_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}


class WorkflowError(GrayGEMSError):
    """Exception raised during workflow execution"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "workflow_error", details)


class ConfigurationError(GrayGEMSError):
    """Exception raised during configuration loading/validation"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "configuration_error", details)


class ProjectError(GrayGEMSError):
    """Exception raised during project operations"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "project_error", details)


class ServiceError(GrayGEMSError):
    """Exception raised during service execution"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "service_error", details)


class ErrorResponse(BaseModel):
    """Standard error response model"""

    success: bool = False
    error: str
    error_type: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response model"""

    success: bool = True
    data: Dict[str, Any]
    message: Optional[str] = None


def setup_error_handling(app: FastAPI):
    """Setup global error handling for FastAPI app"""

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for all unhandled exceptions"""
        return GrayGemsErrorHandler.handle_exception(request, exc)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handler for HTTP exceptions"""
        return GrayGemsErrorHandler.create_error_response(
            error=exc,
            error_type="http_error",
            status_code=exc.status_code,
            details={"status_code": exc.status_code},
        )

    @app.exception_handler(ValueError)
    async def validation_exception_handler(request: Request, exc: ValueError):
        """Handler for validation errors"""
        return GrayGemsErrorHandler.create_error_response(
            error=exc,
            error_type="validation_error",
            status_code=400,
            details={"field": "input"},
        )

    logger.info("✅ Error handling setup completed")


class GrayGemsErrorHandler:
    """Centralized error handling for GrayGEMS API"""

    @staticmethod
    def create_error_response(
        error: Exception,
        error_type: str = "internal_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> JSONResponse:
        """Create a standardized error response"""
        error_message = str(error) if error else "Unknown error occurred"

        # Log the error with appropriate level based on status code
        if status_code >= 500:
            # Server errors - log as error with traceback
            logger.error(f"GrayGEMS Server Error [{error_type}]: {error_message}")
            if error:
                logger.error(f"Traceback: {traceback.format_exc()}")
        elif status_code >= 400:
            # Client errors - log as warning without traceback (expected behavior)
            logger.warning(f"GrayGEMS Client Error [{error_type}]: {error_message}")
        else:
            # Other errors - log as info
            logger.info(f"GrayGEMS Error [{error_type}]: {error_message}")

        error_response = ErrorResponse(
            success=False,
            error=error_message,
            error_type=error_type,
            details=details,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=status_code, content=error_response.model_dump()
        )

    @staticmethod
    def create_success_response(
        data: Dict[str, Any], message: Optional[str] = None, status_code: int = 200
    ) -> JSONResponse:
        """Create a standardized success response"""
        success_response = SuccessResponse(success=True, data=data, message=message)

        return JSONResponse(
            status_code=status_code, content=success_response.model_dump()
        )

    @staticmethod
    def handle_exception(request: Request, exc: Exception) -> JSONResponse:
        """Global exception handler for FastAPI"""

        # Determine error type and status code
        if isinstance(exc, HTTPException):
            error_type = "http_error"
            status_code = exc.status_code
            details = {"status_code": exc.status_code}
        elif isinstance(exc, ValueError):
            error_type = "validation_error"
            status_code = 400
            details = {"field": "input"}
        elif isinstance(exc, KeyError):
            error_type = "missing_field"
            status_code = 400
            details = {"missing_field": str(exc)}
        elif isinstance(exc, FileNotFoundError):
            error_type = "file_not_found"
            status_code = 404
            details = {"file_path": str(exc)}
        elif isinstance(exc, PermissionError):
            error_type = "permission_error"
            status_code = 403
            details = {"operation": "file_access"}
        else:
            error_type = "internal_error"
            status_code = 500
            details = {"exception_type": type(exc).__name__}

        return GrayGemsErrorHandler.create_error_response(
            error=exc, error_type=error_type, status_code=status_code, details=details
        )


def validate_json_response(response: Any) -> bool:
    """Validate that a response can be serialized to JSON"""
    try:
        if hasattr(response, "model_dump"):
            # Pydantic model
            response.model_dump()
        elif isinstance(response, dict):
            # Dictionary
            import json

            json.dumps(response)
        elif hasattr(response, "dict"):
            # FastAPI response
            response.dict()
        else:
            # Try to serialize
            import json

            json.dumps(response)
        return True
    except Exception as e:
        logger.error(f"Invalid JSON response: {e}")
        return False
