import logging
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
from .project import Project, ProjectConfig

logger = logging.getLogger(__name__)

class ProjectManager:
    """Manages projects with token-based authentication"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.cwd() / "projects"
        self.projects: Dict[str, Project] = {}
        self.token_to_project: Dict[str, str] = {}  # token -> project_id mapping
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing projects
        self._load_existing_projects()
    
    def _load_existing_projects(self):
        """Load existing projects from disk"""
        try:
            for project_dir in self.base_dir.iterdir():
                if project_dir.is_dir():
                    try:
                        project = Project.load(project_dir.name, self.base_dir)
                        self.projects[project.project_id] = project
                        if project.config.token:
                            self.token_to_project[project.config.token] = project.project_id
                        logger.info(f"Loaded existing project: {project.project_id}")
                    except Exception as e:
                        logger.warning(f"Failed to load project {project_dir.name}: {e}")
        except Exception as e:
            logger.error(f"Failed to load existing projects: {e}")
    
    def create_project(self, name: str, description: Optional[str] = None, expiration_days: int = 30) -> Project:
        """Create a new project with token authentication"""
        metadata = {
            "name": name,
            "description": description or "",
            "status": "created"
        }
        
        config = ProjectConfig(
            base_dir=self.base_dir,
            expires_at=datetime.now() + timedelta(days=expiration_days),
            metadata=metadata
        )
        
        project = Project(config)
        self.projects[project.project_id] = project
        self.token_to_project[project.config.token] = project.project_id
        
        logger.info(f"Created new project: {project.project_id} with token: {project.config.token[:8]}...")
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        return self.projects.get(project_id)
    
    def get_project_by_token(self, token: str) -> Optional[Project]:
        """Get project by token with validation"""
        if token not in self.token_to_project:
            return None
        
        project_id = self.token_to_project[token]
        project = self.projects.get(project_id)
        
        if not project:
            return None
        
        # Validate token
        if not project.validate_token(token):
            return None
        
        return project
    
    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID (alias for get_project)"""
        return self.get_project(project_id)
    
    def validate_token(self, project_id: str, token: str) -> bool:
        """Validate if token has access to project"""
        project = self.projects.get(project_id)
        if not project:
            return False
        
        return project.validate_token(token)
    
    def validate_project_access(self, project_id: str, token: str) -> bool:
        """Validate if token has access to project (alias for validate_token)"""
        return self.validate_token(project_id, token)
    
    def get_project_dir(self, project_id: str) -> Optional[Path]:
        """Get project directory path"""
        project = self.projects.get(project_id)
        if project:
            return project.project_dir
        return None
    
    def update_project_status(self, project_id: str, status: str):
        """Update project status"""
        project = self.projects.get(project_id)
        if project:
            project.add_metadata("status", status)
            logger.info(f"Updated project {project_id} status to: {status}")
    
    def list_projects(self) -> List[Dict]:
        """List all projects (without sensitive data)"""
        project_list = []
        for project in self.projects.values():
            info = project.get_info()
            # Don't include token in list
            info.pop("token", None)
            project_list.append(info)
        return project_list
    
    def delete_project(self, project_id: str, token: str) -> bool:
        """Delete project with token validation"""
        if not self.validate_project_access(project_id, token):
            return False
        
        project = self.projects.pop(project_id, None)
        if project and project.config.token:
            self.token_to_project.pop(project.config.token, None)
        
        if project:
            project.cleanup()
            logger.info(f"Deleted project: {project_id}")
            return True
        
        return False
    
    def extend_project(self, project_id: str, token: str, days: int = 30) -> bool:
        """Extend project expiration with token validation"""
        if not self.validate_project_access(project_id, token):
            return False
        
        project = self.projects.get(project_id)
        if project:
            project.extend_expiration(days)
            logger.info(f"Extended project {project_id} by {days} days")
            return True
        
        return False
    
    def cleanup_expired_projects(self) -> int:
        """Clean up expired projects and return count of cleaned projects"""
        expired_projects = []
        
        for project_id, project in self.projects.items():
            if project.is_expired():
                expired_projects.append(project_id)
        
        for project_id in expired_projects:
            project = self.projects.pop(project_id)
            if project.config.token:
                self.token_to_project.pop(project.config.token, None)
            project.cleanup()
            logger.info(f"Cleaned up expired project: {project_id}")
        
        return len(expired_projects)
    
    def get_project_stats(self) -> Dict:
        """Get statistics about projects"""
        total_projects = len(self.projects)
        expired_projects = sum(1 for p in self.projects.values() if p.is_expired())
        active_projects = total_projects - expired_projects
        
        return {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "expired_projects": expired_projects,
            "base_directory": str(self.base_dir)
        } 