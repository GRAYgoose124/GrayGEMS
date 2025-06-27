"""
Tests for GrayGEMS Workflow Management
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from graygems.core.workflow import WorkflowManager
from graygems.core.models import APIRequest, ServiceCall
from graygems.core.service import Service
from pathlib import Path
import asyncio

@pytest.fixture
def workflow_manager(service_registry, tmp_path):
    return WorkflowManager(service_registry, tmp_path)

class TestWorkflowManager:
    """Test WorkflowManager functionality"""
    
    def test_workflow_manager_initialization(self, service_registry, temp_dir):
        """Test WorkflowManager initialization"""
        workflow_manager = WorkflowManager(service_registry, temp_dir)
        
        assert workflow_manager.registry == service_registry
        assert workflow_manager.project_dir == temp_dir
    
    @pytest.mark.asyncio
    async def test_execute_workflow_and_get_transaction(self, workflow_manager, service_registry):
        """Test executing a workflow and getting transaction details"""
        # Register a mock service and task
        mock_service = Mock(spec=Service)
        mock_task = AsyncMock()
        mock_task.execute = AsyncMock(return_value={"outputs": {"result": 42}})
        mock_service.get_task.return_value = mock_task
        mock_service.input_model = None
        service_registry.register("test_service", mock_service)
        
        workflow = {
            "steps": {
                "step1": {
                    "service": "test_service",
                    "task": "mock_task",
                    "inputs": {"a": 1, "b": 2},
                    "dependencies": []
                }
            }
        }
        project_id = "proj-123"
        result = await workflow_manager.execute_workflow(project_id, workflow, workflow_manager.project_dir)
        assert result["project_id"] == project_id
        assert result["status"] == "completed"
        assert "step1" in result["steps"]
        assert result["steps"]["step1"]["outputs"]["result"] == 42
        # get_transaction
        tx_id = result["transaction_id"]
        tx = workflow_manager.get_transaction(tx_id)
        assert tx is not None
        assert tx.project_id == project_id
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_missing_service(self, workflow_manager):
        """Test executing workflow with missing service"""
        workflow = {
            "steps": {
                "step1": {
                    "service": "nonexistent",
                    "task": "mock_task",
                    "inputs": {},
                    "dependencies": []
                }
            }
        }
        project_id = "proj-err"
        with pytest.raises(Exception):
            await workflow_manager.execute_workflow(project_id, workflow, workflow_manager.project_dir)
    
    def test_list_transactions(self, workflow_manager, service_registry):
        """Test listing transactions"""
        # Register a mock service and task
        mock_service = Mock(spec=Service)
        mock_task = AsyncMock()
        mock_task.execute = AsyncMock(return_value={"outputs": {"result": 1}})
        mock_service.get_task.return_value = mock_task
        mock_service.input_model = None
        service_registry.register("test_service", mock_service)
        # Create a transaction
        workflow = {
            "steps": {
                "step1": {
                    "service": "test_service",
                    "task": "mock_task",
                    "inputs": {"a": 1},
                    "dependencies": []
                }
            }
        }
        project_id = "proj-list"
        # Run in event loop using asyncio.run instead of deprecated get_event_loop
        asyncio.run(
            workflow_manager.execute_workflow(project_id, workflow, workflow_manager.project_dir)
        )
        txs = workflow_manager.list_transactions()
        assert len(txs) > 0
        assert any(tx["project_id"] == project_id for tx in txs)
    
    def test_get_transaction_returns_none_for_invalid_id(self, workflow_manager):
        """Test getting transaction with invalid ID"""
        assert workflow_manager.get_transaction("not-a-real-id") is None 