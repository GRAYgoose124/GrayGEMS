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
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

# Add the demo directory to Python path
demo_dir = Path(__file__).parent
sys.path.insert(0, str(demo_dir))

# Import GrayGEMS core components
from graygems.core.config_manager import ConfigManager
from graygems.core.registry import ServiceRegistry
from graygems.core.workflow import WorkflowManager
from graygems.core.project_manager import ProjectManager
from graygems.core.error_handler import setup_error_handling, SuccessResponse, ErrorResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GrayGEMS Demo",
    description="A demonstration of GrayGEMS capabilities",
    version="1.0.0"
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
DOWNLOADS_DIR = DEMO_DIR / "downloads"

# Ensure directories exist
PROJECTS_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)

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
            "health": "/health"
        }
    )

@app.get("/health", response_model=SuccessResponse)
async def health_check():
    """Health check endpoint"""
    return SuccessResponse(
        message="GrayGEMS Demo Server is healthy",
        data={
            "status": "healthy",
            "services": len(service_registry.services),
            "projects": len(project_manager.projects)
        }
    )

@app.post("/projects", response_model=SuccessResponse)
async def create_project(request: CreateProjectRequest):
    """Create a new project"""
    try:
        project = project_manager.create_project(request.name, request.description)
        return SuccessResponse(
            message="Project created successfully",
            data={
                "project_id": project.project_id,
                "token": project.token,
                "name": project.name,
                "created_at": project.created_at.isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}", response_model=SuccessResponse)
async def get_project(project_id: str, x_project_token: str = Header(None)):
    """Get project details"""
    try:
        if not x_project_token:
            raise HTTPException(status_code=401, detail="Project token required")
        
        if not project_manager.validate_token(project_id, x_project_token):
            raise HTTPException(status_code=401, detail="Invalid project token")
        
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
                "status": project.status
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projects/{project_id}/workflow", response_model=SuccessResponse)
async def execute_workflow(project_id: str, request: WorkflowRequest, x_project_token: str = Header(None)):
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
            project_id=project_id,
            workflow=request.workflow,
            project_dir=project_dir
        )
        
        # Update project status
        project_manager.update_project_status(project_id, "completed")
        
        return SuccessResponse(
            message="Workflow executed successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        # Update project status on error
        project_manager.update_project_status(project_id, "failed")
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/download/{file_path:path}", response_model=SuccessResponse)
async def download_file(project_id: str, file_path: str, x_project_token: str = Header(None)):
    """Download a file from a project"""
    try:
        if not x_project_token:
            raise HTTPException(status_code=401, detail="Project token required")
        
        if not project_manager.validate_token(project_id, x_project_token):
            raise HTTPException(status_code=401, detail="Invalid project token")
        
        project_dir = project_manager.get_project_dir(project_id)
        file_path_obj = Path(file_path)
        
        # Security check: prevent directory traversal
        if ".." in str(file_path_obj):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        full_path = project_dir / file_path_obj
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # For demo purposes, return file info
        # In a real implementation, you'd return the actual file
        return SuccessResponse(
            message="File download info",
            data={
                "file_path": str(file_path),
                "size": full_path.stat().st_size,
                "exists": True,
                "note": "In a real implementation, this would return the actual file"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/services", response_model=SuccessResponse)
async def list_services():
    """List available services"""
    services = {}
    for service_name, service in service_registry.services.items():
        services[service_name] = {
            "description": getattr(service, 'description', ''),
            "tasks": list(service.tasks.keys()) if hasattr(service, 'tasks') else []
        }
    
    return SuccessResponse(
        message="Services retrieved successfully",
        data={"services": services}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)