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
                        logger.info(f"Loaded existing project: {project.project_id}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to load project {project_dir.name}: {e}"
                        )
        except Exception as e:
            logger.error(f"Failed to load existing projects: {e}")

    def create_project(
        self, name: str, description: Optional[str] = None, expiration_days: int = 30
    ) -> Project:
        """Create a new project with token authentication"""
        metadata = {"name": name, "description": description or "", "status": "created"}

        config = ProjectConfig(
            base_dir=self.base_dir,
            expires_at=datetime.now() + timedelta(days=expiration_days),
            metadata=metadata,
        )

        project = Project(config)
        self.projects[project.project_id] = project

        # Get the plain token for return (this is the only time it's available)
        plain_token = project.token

        logger.info(
            f"Created new project: {project.project_id} with token: {plain_token[:8]}..."
        )
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        return self.projects.get(project_id)

    def get_project_by_token(self, token: str) -> Optional[Project]:
        """Get project by token with validation"""
        # Search through all projects to find one with matching token
        for project in self.projects.values():
            if project.validate_token(token):
                return project
        return None

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

    def validate_project_access_optional(
        self, project_id: str, token: Optional[str] = None
    ) -> bool:
        """Validate project access with optional token (for public projects)"""
        project = self.projects.get(project_id)
        if not project:
            return False

        # Public projects don't require a token
        if project.is_public():
            return True

        # Private projects require a valid token
        if not token:
            return False

        return project.validate_token(token)

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
            project_list.append(info)
        return project_list

    def delete_project(self, project_id: str, token: str) -> bool:
        """Delete project with token validation"""
        if not self.validate_project_access(project_id, token):
            return False

        project = self.projects.pop(project_id, None)

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
            "base_directory": str(self.base_dir),
        }

    def make_project_public(self, project_id: str, token: str) -> bool:
        """Make a project publicly accessible (requires token for authorization)"""
        if not self.validate_project_access(project_id, token):
            return False

        project = self.projects.get(project_id)
        if project:
            project.make_public()
            logger.info(f"Made project {project_id} public")
            return True

        return False

    def make_project_private(self, project_id: str, token: str) -> bool:
        """Make a project private (requires token for authorization)"""
        if not self.validate_project_access(project_id, token):
            return False

        project = self.projects.get(project_id)
        if project:
            project.make_private()
            logger.info(f"Made project {project_id} private")
            return True

        return False
