# gems2/core/project.py
import uuid
import shutil
import zipfile
import tempfile
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

class ProjectConfig(BaseModel):
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    base_dir: Optional[Path] = None
    token: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Project:
    def __init__(self, config: Optional[ProjectConfig] = None):
        self.config = config or ProjectConfig()
        self.project_id = self.config.project_id
        
        # Generate token if not provided
        if not self.config.token:
            self.config.token = self._generate_token()
        
        # Set expiration if not provided (default 30 days)
        if not self.config.expires_at:
            self.config.expires_at = datetime.now() + timedelta(days=30)
        
        # Use config base_dir or fallback to local directory
        if self.config.base_dir:
            self.base_dir = self.config.base_dir
        else:
            # Try to use local projects directory, fallback to temp if needed
            local_projects = Path.cwd() / "projects"
            try:
                local_projects.mkdir(exist_ok=True)
                self.base_dir = local_projects
            except (PermissionError, OSError):
                # Fallback to temp directory
                self.base_dir = Path(tempfile.gettempdir()) / "graygems" / "projects"
        
        self.project_dir = self.base_dir / self.project_id
        self._initialize()
    
    @property
    def name(self) -> str:
        """Get project name from metadata"""
        return self.config.metadata.get("name", "Unnamed Project")
    
    @property
    def description(self) -> str:
        """Get project description from metadata"""
        return self.config.metadata.get("description", "")
    
    @property
    def status(self) -> str:
        """Get project status from metadata"""
        return self.config.metadata.get("status", "unknown")
    
    @property
    def token(self) -> str:
        """Get project token"""
        return self.config.token
    
    @property
    def created_at(self) -> datetime:
        """Get project creation time"""
        return self.config.created_at
    
    def _generate_token(self) -> str:
        """Generate a secure token for project access"""
        # Create a unique token based on project ID and timestamp
        token_data = f"{self.project_id}:{time.time()}:{uuid.uuid4()}"
        return hashlib.sha256(token_data.encode()).hexdigest()[:32]
    
    def _initialize(self):
        """Create project directory structure"""
        try:
            self.project_dir.mkdir(parents=True, exist_ok=True)
            (self.project_dir / "inputs").mkdir(exist_ok=True)
            (self.project_dir / "outputs").mkdir(exist_ok=True)
            (self.project_dir / "temp").mkdir(exist_ok=True)
            (self.project_dir / "logs").mkdir(exist_ok=True)
            
            # Save project metadata
            self._save_metadata()
        except (PermissionError, OSError) as e:
            # If we can't create the directory, use a temporary one
            temp_dir = Path(tempfile.mkdtemp(prefix=f"graygems_{self.project_id}_"))
            self.project_dir = temp_dir
            (self.project_dir / "inputs").mkdir(exist_ok=True)
            (self.project_dir / "outputs").mkdir(exist_ok=True)
            (self.project_dir / "temp").mkdir(exist_ok=True)
            (self.project_dir / "logs").mkdir(exist_ok=True)
            self._save_metadata()
    
    def _save_metadata(self):
        """Save project metadata to file"""
        metadata_file = self.project_dir / "project.json"
        metadata = {
            "project_id": self.project_id,
            "token": self.config.token,
            "created_at": self.config.created_at.isoformat(),
            "expires_at": self.config.expires_at.isoformat() if self.config.expires_at else None,
            "metadata": self.config.metadata
        }
        
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load project metadata from file"""
        metadata_file = self.project_dir / "project.json"
        if metadata_file.exists():
            import json
            with open(metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def validate_token(self, token: str) -> bool:
        """Validate if the provided token is valid for this project"""
        if not token or token != self.config.token:
            return False
        
        # Check if project has expired
        if self.config.expires_at and datetime.now() > self.config.expires_at:
            return False
        
        return True
    
    def is_expired(self) -> bool:
        """Check if the project has expired"""
        if not self.config.expires_at:
            return False
        return datetime.now() > self.config.expires_at
    
    def extend_expiration(self, days: int = 30):
        """Extend project expiration"""
        if self.config.expires_at:
            self.config.expires_at = max(self.config.expires_at, datetime.now()) + timedelta(days=days)
        else:
            self.config.expires_at = datetime.now() + timedelta(days=days)
        self._save_metadata()
    
    def get_info(self) -> Dict[str, Any]:
        """Get project information"""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.config.created_at.isoformat(),
            "expires_at": self.config.expires_at.isoformat() if self.config.expires_at else None,
            "is_expired": self.is_expired(),
            "project_dir": str(self.project_dir),
            "metadata": self.config.metadata
        }
    
    def create_archive(self) -> Path:
        """Package project directory into ZIP archive"""
        try:
            archive_path = self.base_dir / f"{self.project_id}.zip"
            archive_path.parent.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            # Fallback to temp directory for archive
            archive_path = Path(tempfile.gettempdir()) / "graygems" / f"{self.project_id}.zip"
            archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.project_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.project_dir)
                    zf.write(file_path, arcname)
        
        return archive_path
    
    def cleanup(self):
        """Remove project directory"""
        try:
            if self.project_dir.exists():
                shutil.rmtree(self.project_dir)
        except (PermissionError, OSError):
            # If we can't remove the directory, just log it
            pass
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to the project"""
        self.config.metadata[key] = value
        self._save_metadata()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the project"""
        return self.config.metadata.get(key, default)
    
    @classmethod
    def load(cls, project_id: str, base_dir: Optional[Path] = None) -> "Project":
        """Load existing project"""
        config = ProjectConfig(project_id=project_id, base_dir=base_dir)
        project = cls(config)
        
        # Load metadata from file
        metadata = project._load_metadata()
        if metadata:
            project.config.token = metadata.get("token")
            project.config.created_at = datetime.fromisoformat(metadata.get("created_at", datetime.now().isoformat()))
            if metadata.get("expires_at"):
                project.config.expires_at = datetime.fromisoformat(metadata["expires_at"])
            project.config.metadata = metadata.get("metadata", {})
        
        return project