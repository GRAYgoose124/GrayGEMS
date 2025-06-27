from typing import Dict, List, Set, Any, Optional
from collections import defaultdict, deque
from pydantic import BaseModel, Field
import logging
import json
import asyncio
from pathlib import Path
from datetime import datetime

from .models import APIRequest, APIResponse, ServiceCall
from .project import Project
from .registry import global_registry, ServiceRegistry
from .error_handler import WorkflowError

logger = logging.getLogger(__name__)

class TransactionContext:
    """Stores intermediate results during workflow execution"""
    
    def __init__(self):
        self._results: Dict[str, BaseModel] = {}
    
    def set(self, name: str, result: BaseModel):
        self._results[name] = result
    
    def get(self, name: str) -> BaseModel:
        if name not in self._results:
            raise KeyError(f"Result '{name}' not found in context")
        return self._results[name]
    
    def get_all(self) -> Dict[str, Any]:
        """Get all results as serializable dictionaries"""
        return {name: result.model_dump() if hasattr(result, 'model_dump') else result 
                for name, result in self._results.items()}

class WorkflowStep(BaseModel):
    """Represents a single step in a workflow"""
    step_id: str
    service_name: str
    task_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkflowTransaction(BaseModel):
    """Represents a workflow transaction with full state tracking"""
    transaction_id: str
    project_id: str
    workflow_data: Dict[str, Any]
    steps: Dict[str, WorkflowStep] = Field(default_factory=dict)
    global_outputs: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkflowManager:
    """Enhanced workflow manager with better transaction handling"""
    
    def __init__(self, registry: ServiceRegistry, project_dir: Path):
        self.registry = registry
        self.project_dir = project_dir
        self.transactions: Dict[str, WorkflowTransaction] = {}
        
        # Ensure project directories exist
        self.inputs_dir = project_dir / "inputs"
        self.outputs_dir = project_dir / "outputs"
        self.temp_dir = project_dir / "temp"
        self.logs_dir = project_dir / "logs"
        
        for dir_path in [self.inputs_dir, self.outputs_dir, self.temp_dir, self.logs_dir]:
            dir_path.mkdir(exist_ok=True)
    
    def create_transaction(self, workflow_data: Dict[str, Any], project_id: str) -> WorkflowTransaction:
        """Create a new workflow transaction"""
        import uuid
        
        transaction_id = str(uuid.uuid4())
        transaction = WorkflowTransaction(
            transaction_id=transaction_id,
            project_id=project_id,
            workflow_data=workflow_data
        )
        
        # Parse workflow and create steps
        self._parse_workflow_steps(transaction, workflow_data)
        
        self.transactions[transaction_id] = transaction
        logger.info(f"Created workflow transaction: {transaction_id}")
        
        return transaction
    
    def _parse_workflow_steps(self, transaction: WorkflowTransaction, workflow_data: Dict[str, Any]):
        """Parse workflow data and create workflow steps"""
        steps_data = workflow_data.get("steps", {})
        
        for step_id, step_config in steps_data.items():
            step = WorkflowStep(
                step_id=step_id,
                service_name=step_config.get("service"),
                task_name=step_config.get("task"),
                inputs=step_config.get("inputs", {}),
                dependencies=step_config.get("dependencies", [])
            )
            transaction.steps[step_id] = step
    
    async def execute_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Execute a workflow transaction"""
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            raise WorkflowError(f"Transaction {transaction_id} not found")
        
        if transaction.status in ["running", "completed"]:
            return self._get_transaction_result(transaction)
        
        try:
            transaction.status = "running"
            transaction.started_at = datetime.now()
            
            # Execute steps in dependency order
            await self._execute_steps(transaction)
            
            transaction.status = "completed"
            transaction.completed_at = datetime.now()
            
            logger.info(f"Completed workflow transaction: {transaction_id}")
            return self._get_transaction_result(transaction)
            
        except Exception as e:
            transaction.status = "failed"
            transaction.error = str(e)
            transaction.completed_at = datetime.now()
            logger.error(f"Workflow transaction {transaction_id} failed: {e}")
            raise
    
    async def _execute_steps(self, transaction: WorkflowTransaction):
        """Execute workflow steps in dependency order"""
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(transaction.steps)
        
        # Execute steps in topological order
        executed_steps: Set[str] = set()
        
        while len(executed_steps) < len(transaction.steps):
            # Find steps that can be executed (all dependencies satisfied)
            ready_steps = [
                step_id for step_id, deps in dependency_graph.items()
                if step_id not in executed_steps and all(dep in executed_steps for dep in deps)
            ]
            
            if not ready_steps:
                # Circular dependency or missing step
                remaining = set(transaction.steps.keys()) - executed_steps
                raise WorkflowError(f"Circular dependency or missing step detected: {remaining}")
            
            # Execute ready steps concurrently
            tasks = []
            for step_id in ready_steps:
                task = asyncio.create_task(self._execute_step(transaction, step_id))
                tasks.append(task)
            
            # Wait for all ready steps to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for failures
            for step_id, result in zip(ready_steps, results):
                if isinstance(result, Exception):
                    step = transaction.steps[step_id]
                    step.status = "failed"
                    step.error = str(result)
                    step.end_time = datetime.now()
                    raise WorkflowError(f"Step {step_id} failed: {result}")
                
                executed_steps.add(step_id)
    
    def _build_dependency_graph(self, steps: Dict[str, WorkflowStep]) -> Dict[str, List[str]]:
        """Build dependency graph for workflow steps"""
        graph = {}
        for step_id, step in steps.items():
            graph[step_id] = step.dependencies.copy()
        return graph
    
    async def _execute_step(self, transaction: WorkflowTransaction, step_id: str):
        """Execute a single workflow step"""
        step = transaction.steps[step_id]
        step.status = "running"
        step.start_time = datetime.now()
        
        try:
            # Resolve inputs with dependency references
            resolved_inputs = self._resolve_step_inputs(transaction, step)
            
            # Get service and task
            service = self.registry.get_service(step.service_name)
            if not service:
                raise WorkflowError(f"Service '{step.service_name}' not found")
            
            task = service.get_task(step.task_name)
            if not task:
                raise WorkflowError(f"Task '{step.task_name}' not found in service '{step.service_name}'")
            
            # Execute task with proper input validation
            logger.info(f"Executing step {step_id}: {step.service_name}.{step.task_name}")
            
            # Validate inputs using the service's input model if available
            if service.input_model:
                logger.info(f"Service {step.service_name} has input model: {service.input_model}")
                validated_inputs = service.input_model(**resolved_inputs)
                # Convert validated inputs back to dict for task execution
                task_inputs = validated_inputs.model_dump()
                logger.info(f"Validated inputs: {task_inputs}")
            else:
                logger.info(f"Service {step.service_name} has no input model, using raw inputs")
                task_inputs = resolved_inputs
            
            # Execute the task directly
            result = await task.execute(task_inputs, self.project_dir)
            
            # Store outputs
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            else:
                result_dict = result
            # For core services, just store the whole result as outputs
            step.outputs = result_dict.get("outputs", result_dict)
            step.status = "completed"
            step.end_time = datetime.now()
            
            # Add to global outputs
            for key, value in step.outputs.items():
                global_key = f"{step_id}.{key}"
                transaction.global_outputs[global_key] = value
            
            logger.info(f"Completed step {step_id}")
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.end_time = datetime.now()
            logger.error(f"Step {step_id} failed: {e}")
            raise
    
    def _resolve_step_inputs(self, transaction: WorkflowTransaction, step: WorkflowStep) -> Dict[str, Any]:
        """Resolve step inputs by replacing dependency references with actual values"""
        resolved_inputs = {}
        
        for key, value in step.inputs.items():
            if isinstance(value, str) and value.startswith("$"):
                # This is a dependency reference
                resolved_value = self._resolve_dependency_reference(transaction, value)
                resolved_inputs[key] = resolved_value
            else:
                resolved_inputs[key] = value
        
        return resolved_inputs
    
    def _resolve_dependency_reference(self, transaction: WorkflowTransaction, reference: str) -> Any:
        """Resolve a dependency reference like '$step_name.output_field'"""
        # Remove the leading '$'
        ref_path = reference[1:]
        
        # Split by dots to get step and field
        parts = ref_path.split(".")
        if len(parts) < 2:
            raise WorkflowError(f"Invalid dependency reference: {reference}")
        
        step_id = parts[0]
        field_path = ".".join(parts[1:])
        
        # Get the step
        step = transaction.steps.get(step_id)
        if not step:
            raise WorkflowError(f"Referenced step '{step_id}' not found")
        
        if step.status != "completed":
            raise WorkflowError(f"Referenced step '{step_id}' is not completed (status: {step.status})")
        
        # Navigate to the field in outputs
        value = step.outputs
        for part in field_path.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                raise WorkflowError(f"Field '{field_path}' not found in step '{step_id}' outputs")
        
        return value
    
    def _get_transaction_result(self, transaction: WorkflowTransaction) -> Dict[str, Any]:
        """Get the result of a workflow transaction"""
        return {
            "transaction_id": transaction.transaction_id,
            "project_id": transaction.project_id,
            "status": transaction.status,
            "created_at": transaction.created_at.isoformat(),
            "started_at": transaction.started_at.isoformat() if transaction.started_at else None,
            "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
            "error": transaction.error,
            "steps": {
                step_id: {
                    "status": step.status,
                    "service": step.service_name,
                    "task": step.task_name,
                    "inputs": step.inputs,
                    "outputs": step.outputs,
                    "error": step.error,
                    "start_time": step.start_time.isoformat() if step.start_time else None,
                    "end_time": step.end_time.isoformat() if step.end_time else None
                }
                for step_id, step in transaction.steps.items()
            },
            "outputs": transaction.global_outputs,
            "metadata": transaction.metadata
        }
    
    def get_transaction(self, transaction_id: str) -> Optional[WorkflowTransaction]:
        """Get a workflow transaction by ID"""
        return self.transactions.get(transaction_id)
    
    def list_transactions(self) -> List[Dict[str, Any]]:
        """List all transactions"""
        return [
            {
                "transaction_id": t.transaction_id,
                "project_id": t.project_id,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "step_count": len(t.steps)
            }
            for t in self.transactions.values()
        ]
    
    async def execute_workflow(self, project_id: str, workflow: Dict[str, Any], project_dir: Path) -> Dict[str, Any]:
        """Execute a workflow for a project"""
        # Create transaction
        transaction = self.create_transaction(workflow, project_id)
        
        # Execute transaction
        result = await self.execute_transaction(transaction.transaction_id)
        
        return result
