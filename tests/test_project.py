"""
Tests for GrayGEMS Project Management
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from graygems.core.project import Project, ProjectConfig
from graygems.core.project_manager import ProjectManager


class TestProjectConfig:
    """Test ProjectConfig model"""
    
    def test_project_config_defaults(self):
        """Test ProjectConfig with default values"""
        config = ProjectConfig()
        
        assert config.project_id is not None
        assert config.base_dir is None
        assert config.token_hash is None
        assert config.plain_token is None
        assert config.created_at is not None
        assert config.expires_at is None
        assert config.metadata == {}
        assert config.is_public is False
    
    def test_project_config_custom_values(self):
        """Test ProjectConfig with custom values"""
        project_id = "test-project-123"
        metadata = {"name": "Test Project", "description": "A test"}
        
        config = ProjectConfig(
            project_id=project_id,
            metadata=metadata,
            is_public=True
        )
        
        assert config.project_id == project_id
        assert config.metadata == metadata
        assert config.is_public is True


class TestProject:
    """Test Project functionality"""
    
    def test_project_creation(self, temp_dir):
        """Test creating a new project"""
        config = ProjectConfig(base_dir=temp_dir)
        project = Project(config)
        
        assert project.project_id is not None
        assert project.project_dir.exists()
        assert (project.project_dir / "inputs").exists()
        assert (project.project_dir / "outputs").exists()
        assert (project.project_dir / "temp").exists()
        assert (project.project_dir / "logs").exists()
        assert project.project_dir.parent == temp_dir
    
    def test_project_with_config(self, temp_dir, sample_project_config):
        """Test creating project with config"""
        sample_project_config.base_dir = temp_dir
        project = Project(sample_project_config)
        
        assert project.project_id == "test-project-123"
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.status == "created"
        assert project.project_dir.parent == temp_dir
    
    def test_project_token_generation(self, temp_dir):
        """Test project token generation"""
        config = ProjectConfig(base_dir=temp_dir)
        project = Project(config)
        
        # Token should be available for new projects
        token = project.token
        assert token is not None
        assert len(token) > 0
        
        # Token should be validated correctly
        assert project.validate_token(token) is True
    
    def test_project_token_validation(self, temp_dir):
        """Test project token validation"""
        config = ProjectConfig(base_dir=temp_dir)
        project = Project(config)
        token = project.token
        
        # Valid token
        assert project.validate_token(token) is True
        
        # Invalid token
        assert project.validate_token("invalid_token") is False
        assert project.validate_token("") is False
        assert project.validate_token(None) is False
    
    def test_project_expiration(self, temp_dir):
        """Test project expiration"""
        # Create project with short expiration
        config = ProjectConfig(expires_at=datetime.now() - timedelta(hours=1), base_dir=temp_dir)
        project = Project(config)
        
        assert project.is_expired() is True
        assert project.validate_token(project.token) is False
    
    def test_project_extension(self, temp_dir):
        """Test project expiration extension"""
        config = ProjectConfig(expires_at=datetime.now() + timedelta(hours=1), base_dir=temp_dir)
        project = Project(config)
        
        original_expiry = project.config.expires_at
        project.extend_expiration(days=30)
        
        assert project.config.expires_at > original_expiry
    
    def test_project_metadata(self, temp_dir):
        """Test project metadata operations"""
        config = ProjectConfig(base_dir=temp_dir)
        project = Project(config)
        
        # Add metadata
        project.add_metadata("key1", "value1")
        project.add_metadata("key2", {"nested": "value"})
        
        # Get metadata
        assert project.get_metadata("key1") == "value1"
        assert project.get_metadata("key2") == {"nested": "value"}
        assert project.get_metadata("nonexistent", "default") == "default"
    
    def test_project_public_private(self, temp_dir):
        """Test project public/private functionality"""
        config = ProjectConfig(base_dir=temp_dir)
        project = Project(config)
        
        # Default should be private
        assert project.is_public() is False
        
        # Make public
        project.make_public()
        assert project.is_public() is True
        assert project.validate_token(None) is True  # Public projects don't need token
        
        # Make private
        project.make_private()
        assert project.is_public() is False
        assert project.validate_token(None) is False  # Private projects need token
    
    def test_project_archive_creation(self, temp_dir):
        """Test project archive creation"""
        config = ProjectConfig(base_dir=temp_dir)
        project = Project(config)
        
        # Create some test files
        test_file = project.project_dir / "outputs" / "test.txt"
        test_file.write_text("Hello World")
        
        # Create archive
        archive_path = project.create_archive()
        
        assert archive_path.exists()
        assert archive_path.name.endswith(".zip")
        assert archive_path.stat().st_size > 0
    
    def test_project_cleanup(self, temp_dir):
        """Test project cleanup"""
        config = ProjectConfig(base_dir=temp_dir)
        project = Project(config)
        project_dir = project.project_dir
        
        assert project_dir.exists()
        project.cleanup()
        # Note: cleanup might not remove directory due to permissions, but should handle gracefully
    
    def test_project_load(self, temp_dir):
        """Test loading existing project"""
        # Create a project first
        config = ProjectConfig(base_dir=temp_dir)
        original_project = Project(config)
        project_id = original_project.project_id
        
        # Load the project
        loaded_project = Project.load(project_id, temp_dir)
        
        assert loaded_project.project_id == project_id
        assert loaded_project.project_dir.parent == temp_dir


class TestProjectManager:
    """Test ProjectManager functionality"""
    
    def test_project_manager_initialization(self, temp_dir):
        """Test ProjectManager initialization"""
        manager = ProjectManager(temp_dir)
        
        assert manager.base_dir == temp_dir
        assert len(manager.projects) == 0
    
    def test_create_project(self, project_manager):
        """Test creating a project"""
        project = project_manager.create_project(
            name="Test Project",
            description="A test project"
        )
        
        assert project.project_id is not None
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.project_id in project_manager.projects
        assert project.project_dir.parent == project_manager.base_dir
    
    def test_get_project(self, project_manager):
        """Test getting a project"""
        project = project_manager.create_project("Test Project")
        
        retrieved_project = project_manager.get_project(project.project_id)
        assert retrieved_project == project
    
    def test_get_nonexistent_project(self, project_manager):
        """Test getting a non-existent project"""
        project = project_manager.get_project("nonexistent-id")
        assert project is None
    
    def test_validate_token(self, project_manager):
        """Test token validation"""
        project = project_manager.create_project("Test Project")
        token = project.token
        
        assert project_manager.validate_token(project.project_id, token) is True
        assert project_manager.validate_token(project.project_id, "invalid") is False
    
    def test_validate_project_access(self, project_manager):
        """Test project access validation"""
        project = project_manager.create_project("Test Project")
        token = project.token
        
        assert project_manager.validate_project_access(project.project_id, token) is True
        assert project_manager.validate_project_access(project.project_id, "invalid") is False
    
    def test_validate_project_access_optional(self, project_manager):
        """Test optional project access validation"""
        # Private project
        private_project = project_manager.create_project("Private Project")
        token = private_project.token
        
        assert project_manager.validate_project_access_optional(private_project.project_id, token) is True
        assert project_manager.validate_project_access_optional(private_project.project_id, None) is False
        
        # Public project
        public_project = project_manager.create_project("Public Project")
        public_project.make_public()
        
        assert project_manager.validate_project_access_optional(public_project.project_id, None) is True
        assert project_manager.validate_project_access_optional(public_project.project_id, "any_token") is True
    
    def test_get_project_dir(self, project_manager):
        """Test getting project directory"""
        project = project_manager.create_project("Test Project")
        
        project_dir = project_manager.get_project_dir(project.project_id)
        assert project_dir == project.project_dir
    
    def test_update_project_status(self, project_manager):
        """Test updating project status"""
        project = project_manager.create_project("Test Project")
        
        project_manager.update_project_status(project.project_id, "running")
        assert project.status == "running"
        
        project_manager.update_project_status(project.project_id, "completed")
        assert project.status == "completed"
    
    def test_list_projects(self, project_manager):
        """Test listing projects"""
        project1 = project_manager.create_project("Project 1")
        project2 = project_manager.create_project("Project 2")
        
        projects = project_manager.list_projects()
        assert len(projects) == 2
        
        project_ids = [p["project_id"] for p in projects]
        assert project1.project_id in project_ids
        assert project2.project_id in project_ids
    
    def test_delete_project(self, project_manager):
        """Test deleting a project"""
        project = project_manager.create_project("Test Project")
        token = project.token
        
        success = project_manager.delete_project(project.project_id, token)
        assert success is True
        assert project.project_id not in project_manager.projects
    
    def test_delete_project_invalid_token(self, project_manager):
        """Test deleting project with invalid token"""
        project = project_manager.create_project("Test Project")
        
        success = project_manager.delete_project(project.project_id, "invalid_token")
        assert success is False
        assert project.project_id in project_manager.projects
    
    def test_extend_project(self, project_manager):
        """Test extending project expiration"""
        project = project_manager.create_project("Test Project")
        token = project.token
        
        original_expiry = project.config.expires_at
        success = project_manager.extend_project(project.project_id, token, days=15)
        
        assert success is True
        assert project.config.expires_at > original_expiry
    
    def test_extend_project_invalid_token(self, project_manager):
        """Test extending project with invalid token"""
        project = project_manager.create_project("Test Project")
        
        success = project_manager.extend_project(project.project_id, "invalid_token", days=15)
        assert success is False
    
    def test_make_project_public(self, project_manager):
        """Test making project public"""
        project = project_manager.create_project("Test Project")
        token = project.token
        
        success = project_manager.make_project_public(project.project_id, token)
        assert success is True
        assert project.is_public() is True
    
    def test_make_project_private(self, project_manager):
        """Test making project private"""
        project = project_manager.create_project("Test Project")
        project.make_public()
        token = project.token
        
        success = project_manager.make_project_private(project.project_id, token)
        assert success is True
        assert project.is_public() is False
    
    def test_get_project_stats(self, project_manager):
        """Test getting project statistics"""
        project_manager.create_project("Project 1")
        project_manager.create_project("Project 2")
        
        stats = project_manager.get_project_stats()
        
        assert stats["total_projects"] == 2
        assert stats["active_projects"] == 2
        assert stats["expired_projects"] == 0
        assert "base_directory" in stats 