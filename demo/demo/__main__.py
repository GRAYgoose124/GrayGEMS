#!/usr/bin/env python3
"""
GrayGEMS Demo Server
A demonstration of GrayGEMS capabilities
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import shutil

# Add the demo directory to Python path
demo_dir = Path(__file__).parent
sys.path.insert(0, str(demo_dir))

# Import GrayGEMS core components
from graygems.core.config_manager import ConfigManager
from graygems.core.registry import ServiceRegistry
from graygems.core.workflow import WorkflowManager
from graygems.core.project_manager import ProjectManager
from graygems.core.error_handler import (
    setup_error_handling,
    SuccessResponse,
    ErrorResponse,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GrayGEMS Demo",
    description="A demonstration of GrayGEMS capabilities",
    version="1.0.0",
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup error handling
setup_error_handling(app)

# Demo-specific directories
DEMO_DIR = Path(__file__).parent.parent
PROJECTS_DIR = DEMO_DIR / "projects"

# Ensure directories exist
PROJECTS_DIR.mkdir(exist_ok=True)

# Initialize components
config_manager = ConfigManager()
service_registry = ServiceRegistry()
project_manager = ProjectManager(PROJECTS_DIR)

# Load configuration
config_path = DEMO_DIR / "gems_config.json"
if config_path.exists():
    try:
        config = config_manager.load_config(config_path)
        logger.info(f"✅ Configuration loaded: {config.name} v{config.version}")
        logger.info(f"📋 Entities: {list(config.entities.keys())}")
        logger.info(f"🔧 Core services: {list(config.core_services.keys())}")
        config_manager.register_services(config, service_registry)
        logger.info(f"✅ Configuration loaded successfully")
        logger.info(f"📊 Registered services: {list(service_registry.services.keys())}")
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
else:
    logger.warning("⚠️ No configuration file found, using default services")


# Request models
class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False


class WorkflowRequest(BaseModel):
    workflow: Dict[str, Any]


class DownloadRequest(BaseModel):
    project_id: str
    file_path: str


@app.get("/", response_model=SuccessResponse)
async def root():
    """Root endpoint"""
    return SuccessResponse(
        message="GrayGEMS Demo Server",
        data={
            "version": "1.0.0",
            "description": "A demonstration of GrayGEMS capabilities",
            "docs": "/docs",
            "health": "/health",
        },
    )


@app.get("/health", response_model=SuccessResponse)
async def health_check():
    """Health check endpoint"""
    return SuccessResponse(
        message="GrayGEMS Demo Server is healthy",
        data={
            "status": "healthy",
            "services": len(service_registry.services),
            "projects": len(project_manager.projects),
        },
    )


@app.post("/projects", response_model=SuccessResponse)
async def create_project(request: CreateProjectRequest):
    """Create a new project"""
    try:
        project = project_manager.create_project(request.name, request.description)

        # Set public status if requested
        if request.is_public:
            project.make_public()

        # Get the token from the project (this is only available for new projects)
        try:
            token = project.token
        except ValueError:
            # This shouldn't happen for new projects, but handle it gracefully
            logger.error("Failed to get token from new project")
            raise HTTPException(
                status_code=500, detail="Failed to generate project token"
            )

        return SuccessResponse(
            message="Project created successfully",
            data={
                "project_id": project.project_id,
                "token": token,
                "name": project.name,
                "is_public": project.is_public(),
                "created_at": project.created_at.isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}", response_model=SuccessResponse)
async def get_project(project_id: str, x_project_token: Optional[str] = Header(None)):
    """Get project details"""
    try:
        # Validate project access (token optional for public projects)
        if not project_manager.validate_project_access_optional(
            project_id, x_project_token
        ):
            if x_project_token:
                raise HTTPException(status_code=401, detail="Invalid project token")
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Project token required for private projects",
                )

        project = project_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return SuccessResponse(
            message="Project retrieved successfully",
            data={
                "project_id": project.project_id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
                "status": project.status,
                "is_public": project.is_public(),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/workflow", response_model=SuccessResponse)
async def execute_workflow(
    project_id: str, request: WorkflowRequest, x_project_token: str = Header(None)
):
    """Execute a workflow for a project"""
    try:
        if not x_project_token:
            raise HTTPException(status_code=401, detail="Project token required")

        if not project_manager.validate_token(project_id, x_project_token):
            raise HTTPException(status_code=401, detail="Invalid project token")

        # Update project status
        project_manager.update_project_status(project_id, "running")

        # Get project directory
        project_dir = project_manager.get_project_dir(project_id)
        if not project_dir:
            raise HTTPException(status_code=404, detail="Project directory not found")

        # Create workflow manager
        workflow_manager = WorkflowManager(service_registry, project_dir)

        # Execute workflow
        result = await workflow_manager.execute_workflow(
            project_id=project_id, workflow=request.workflow, project_dir=project_dir
        )

        # Update project status
        project_manager.update_project_status(project_id, "completed")

        return SuccessResponse(message="Workflow executed successfully", data=result)
    except HTTPException:
        raise
    except Exception as e:
        # Update project status on error
        project_manager.update_project_status(project_id, "failed")
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/download/{file_path:path}")
async def download_file(
    project_id: str, file_path: str, x_project_token: Optional[str] = Header(None)
):
    """Download a file from a project"""
    try:
        # Validate project access (token optional for public projects)
        if not project_manager.validate_project_access_optional(
            project_id, x_project_token
        ):
            if x_project_token:
                raise HTTPException(status_code=401, detail="Invalid project token")
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Project token required for private projects",
                )

        project_dir = project_manager.get_project_dir(project_id)
        if not project_dir:
            raise HTTPException(status_code=404, detail="Project directory not found")

        file_path_obj = Path(file_path)

        # Security check: prevent directory traversal
        if ".." in str(file_path_obj):
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Look for the file in multiple locations
        possible_paths = []

        # 1. Check in project directory
        project_file_path = project_dir / file_path_obj
        if project_file_path.exists():
            possible_paths.append(project_file_path)

        # 2. Check for archives in the projects base directory
        if file_path_obj.name.endswith(".zip"):
            projects_base_dir = project_dir.parent
            archive_path = projects_base_dir / file_path_obj.name
            if archive_path.exists():
                possible_paths.append(archive_path)

        if not possible_paths:
            raise HTTPException(status_code=404, detail="File not found")

        # Use the first available path
        full_path = possible_paths[0]

        # Return the file as a downloadable response
        return FileResponse(
            path=full_path,
            filename=file_path_obj.name,
            media_type="application/octet-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/archive", response_model=SuccessResponse)
async def create_project_archive(project_id: str, x_project_token: str = Header(None)):
    """Create a project archive"""
    try:
        if not x_project_token:
            raise HTTPException(status_code=401, detail="Project token required")

        if not project_manager.validate_token(project_id, x_project_token):
            raise HTTPException(status_code=401, detail="Invalid project token")

        project = project_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Create the archive
        archive_path = project.create_archive()

        return SuccessResponse(
            message="Project archive created successfully",
            data={
                "project_id": project_id,
                "archive_path": str(archive_path),
                "archive_filename": archive_path.name,
                "archive_size": (
                    archive_path.stat().st_size if archive_path.exists() else 0
                ),
                "download_url": f"/projects/{project_id}/download/{archive_path.name}",
                "created_at": datetime.now().isoformat(),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create project archive: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services", response_model=SuccessResponse)
async def list_services():
    """List available services"""
    services = {}
    for service_name, service in service_registry.services.items():
        services[service_name] = {
            "description": getattr(service, "description", ""),
            "tasks": list(service.tasks.keys()) if hasattr(service, "tasks") else [],
        }

    return SuccessResponse(
        message="Services retrieved successfully", data={"services": services}
    )


@app.post("/projects/{project_id}/extend", response_model=SuccessResponse)
async def extend_project(
    project_id: str, days: int = 30, x_project_token: str = Header(None)
):
    """Extend project expiration"""
    try:
        if not x_project_token:
            raise HTTPException(status_code=401, detail="Project token required")

        if not project_manager.validate_token(project_id, x_project_token):
            raise HTTPException(status_code=401, detail="Invalid project token")

        success = project_manager.extend_project(project_id, x_project_token, days)
        if not success:
            raise HTTPException(
                status_code=404, detail="Project not found or extension failed"
            )

        project = project_manager.get_project(project_id)
        return SuccessResponse(
            message="Project extended successfully",
            data={
                "project_id": project_id,
                "extended_by_days": days,
                "new_expiration": (
                    project.config.expires_at.isoformat()
                    if project.config.expires_at
                    else None
                ),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extend project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/projects/{project_id}", response_model=SuccessResponse)
async def delete_project(project_id: str, x_project_token: str = Header(None)):
    """Delete a project"""
    try:
        if not x_project_token:
            raise HTTPException(status_code=401, detail="Project token required")

        if not project_manager.validate_token(project_id, x_project_token):
            raise HTTPException(status_code=401, detail="Invalid project token")

        success = project_manager.delete_project(project_id, x_project_token)
        if not success:
            raise HTTPException(
                status_code=404, detail="Project not found or deletion failed"
            )

        return SuccessResponse(
            message="Project deleted successfully",
            data={"project_id": project_id, "deleted_at": datetime.now().isoformat()},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects", response_model=SuccessResponse)
async def list_projects():
    """List all projects (admin endpoint)"""
    try:
        projects = project_manager.list_projects()
        return SuccessResponse(
            message="Projects retrieved successfully",
            data={"projects": projects, "total_count": len(projects)},
        )
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/cleanup", response_model=SuccessResponse)
async def cleanup_expired_projects():
    """Clean up expired projects (admin endpoint)"""
    try:
        cleaned_count = project_manager.cleanup_expired_projects()
        return SuccessResponse(
            message="Cleanup completed successfully",
            data={
                "cleaned_projects": cleaned_count,
                "cleanup_time": datetime.now().isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"Failed to cleanup projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/transactions", response_model=SuccessResponse)
async def list_transactions(project_id: str, x_project_token: str = Header(None)):
    """List transactions for a project"""
    try:
        if not x_project_token:
            raise HTTPException(status_code=401, detail="Project token required")

        if not project_manager.validate_token(project_id, x_project_token):
            raise HTTPException(status_code=401, detail="Invalid project token")

        # Get project directory
        project_dir = project_manager.get_project_dir(project_id)
        if not project_dir:
            raise HTTPException(status_code=404, detail="Project directory not found")

        # Create workflow manager to access transactions
        workflow_manager = WorkflowManager(service_registry, project_dir)
        transactions = workflow_manager.list_transactions()

        return SuccessResponse(
            message="Transactions retrieved successfully",
            data={
                "project_id": project_id,
                "transactions": transactions,
                "total_count": len(transactions),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/make-public", response_model=SuccessResponse)
async def make_project_public(project_id: str, x_project_token: str = Header(None)):
    """Make a project publicly accessible"""
    try:
        if not x_project_token:
            raise HTTPException(status_code=401, detail="Project token required")

        success = project_manager.make_project_public(project_id, x_project_token)
        if not success:
            raise HTTPException(
                status_code=404, detail="Project not found or access denied"
            )

        return SuccessResponse(
            message="Project made public successfully",
            data={
                "project_id": project_id,
                "is_public": True,
                "updated_at": datetime.now().isoformat(),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to make project public: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/make-private", response_model=SuccessResponse)
async def make_project_private(project_id: str, x_project_token: str = Header(None)):
    """Make a project private (requires token)"""
    try:
        if not x_project_token:
            raise HTTPException(status_code=401, detail="Project token required")

        success = project_manager.make_project_private(project_id, x_project_token)
        if not success:
            raise HTTPException(
                status_code=404, detail="Project not found or access denied"
            )

        return SuccessResponse(
            message="Project made private successfully",
            data={
                "project_id": project_id,
                "is_public": False,
                "updated_at": datetime.now().isoformat(),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to make project private: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
