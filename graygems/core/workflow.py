from typing import Dict, List, Set, Any, Optional, Union
from collections import defaultdict, deque
from pydantic import BaseModel, Field
import logging
import json
import asyncio
from pathlib import Path
from datetime import datetime
import re

from .models import APIRequest, APIResponse, ServiceCall
from .project import Project
from .registry import global_registry, ServiceRegistry
from .error_handler import WorkflowError
from .workflow_dsl import WorkflowDSL, WorkflowTemplate, template_registry

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
        return {
            name: result.model_dump() if hasattr(result, "model_dump") else result
            for name, result in self._results.items()
        }


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
    step_type: str = "service"  # service, condition, parallel, loop


class AdvancedWorkflowStep(BaseModel):
    """Enhanced workflow step with advanced features"""

    step_id: str
    step_type: str = "service"  # service, condition, parallel, loop, sequence
    service_name: Optional[str] = None
    task_name: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    status: str = "pending"
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Advanced features
    condition: Optional[str] = None  # For conditional steps
    if_steps: List[str] = Field(
        default_factory=list
    )  # Steps to execute if condition is true
    else_steps: List[str] = Field(
        default_factory=list
    )  # Steps to execute if condition is false
    parallel_steps: List[str] = Field(
        default_factory=list
    )  # Steps to execute in parallel
    loop_variable: Optional[str] = None  # Variable name for loop iteration
    loop_collection: Optional[Union[str, List[Any]]] = (
        None  # Collection to iterate over
    )
    loop_steps: List[str] = Field(default_factory=list)  # Steps to execute in loop


class WorkflowTransaction(BaseModel):
    """Represents a workflow transaction with full state tracking"""

    transaction_id: str
    project_id: str
    workflow_data: Dict[str, Any]
    steps: Dict[str, AdvancedWorkflowStep] = Field(default_factory=dict)
    global_outputs: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)  # DSL variables


class WorkflowManager:
    """Enhanced workflow manager with DSL support and advanced features"""

    def __init__(self, registry: ServiceRegistry, project_dir: Path):
        self.registry = registry
        self.project_dir = project_dir
        self.transactions: Dict[str, WorkflowTransaction] = {}
        self.dsl_parser = WorkflowDSL()

        # Ensure project directories exist
        self.inputs_dir = project_dir / "inputs"
        self.outputs_dir = project_dir / "outputs"
        self.temp_dir = project_dir / "temp"
        self.logs_dir = project_dir / "logs"

        for dir_path in [
            self.inputs_dir,
            self.outputs_dir,
            self.temp_dir,
            self.logs_dir,
        ]:
            dir_path.mkdir(exist_ok=True)

    def create_transaction(
        self, workflow_data: Dict[str, Any], project_id: str
    ) -> WorkflowTransaction:
        """Create a new workflow transaction"""
        import uuid

        transaction_id = str(uuid.uuid4())
        transaction = WorkflowTransaction(
            transaction_id=transaction_id,
            project_id=project_id,
            workflow_data=workflow_data,
        )

        # Parse workflow and create steps
        self._parse_workflow_steps(transaction, workflow_data)

        self.transactions[transaction_id] = transaction
        logger.info(f"Created workflow transaction: {transaction_id}")

        return transaction

    def create_dsl_transaction(
        self, dsl_code: str, project_id: str, **parameters
    ) -> WorkflowTransaction:
        """Create a transaction from DSL code"""
        # Perform parameter substitution if parameters are provided
        if parameters:
            import re

            substituted_dsl = dsl_code

            for param_name, param_value in parameters.items():
                placeholder = f"${{{param_name}}}"

                # Handle unquoted placeholders in var assignments: var name = ${param}
                unquoted_pattern = re.compile(
                    rf"(var\s+{param_name}\s*=\s*){re.escape(placeholder)}"
                )
                if isinstance(param_value, str):
                    unquoted_replacement = f'"{param_value}"'
                else:
                    unquoted_replacement = str(param_value)
                substituted_dsl = unquoted_pattern.sub(
                    lambda m: m.group(1) + unquoted_replacement, substituted_dsl
                )

                # Handle quoted placeholders in var assignments: var name = "${param}"
                quoted_pattern = re.compile(
                    rf'(var\s+{param_name}\s*=\s*)["\"][^"\"]*{re.escape(placeholder)}[^"\"]*["\"]'
                )
                if isinstance(param_value, str):
                    quoted_replacement = f'"{param_value}"'
                else:
                    quoted_replacement = str(param_value)
                substituted_dsl = quoted_pattern.sub(
                    lambda m: m.group(1) + quoted_replacement, substituted_dsl
                )

                # Replace any remaining placeholders (not in var assignment)
                if isinstance(param_value, str):
                    replacement = f'"{param_value}"'
                else:
                    replacement = str(param_value)
                substituted_dsl = substituted_dsl.replace(placeholder, replacement)

            dsl_code = substituted_dsl

        # Parse DSL code
        workflow_data = self.dsl_parser.parse_workflow(dsl_code)

        # Add parameters to variables
        workflow_data["variables"].update(parameters)

        return self.create_transaction(workflow_data, project_id)

    def create_template_transaction(
        self, template_name: str, project_id: str, **parameters
    ) -> WorkflowTransaction:
        """Create a transaction from a workflow template"""
        template = template_registry.get(template_name)
        if not template:
            raise WorkflowError(f"Template '{template_name}' not found")

        # Compile template with parameters
        workflow_data = template.compile(**parameters)

        return self.create_transaction(workflow_data, project_id)

    def _parse_workflow_steps(
        self, transaction: WorkflowTransaction, workflow_data: Dict[str, Any]
    ):
        """Parse workflow data and create workflow steps from nested structure"""
        steps_data = workflow_data.get("steps", {})
        transaction.variables = workflow_data.get("variables", {})
        
        # Recursively parse the nested structure
        self._parse_nested_steps(transaction, steps_data, parent_id=None)
    
    def _parse_nested_steps(self, transaction: WorkflowTransaction, steps_data: Dict[str, Any], parent_id: Optional[str] = None):
        """Recursively parse nested steps and add them to the transaction"""
        for step_id, step_config in steps_data.items():
            step_type = step_config.get("type", "service")
            
            if step_type == "service":
                step = AdvancedWorkflowStep(
                    step_id=step_id,
                    step_type=step_type,
                    service_name=step_config.get("service"),
                    task_name=step_config.get("task"),
                    inputs=step_config.get("inputs", {}),
                    dependencies=step_config.get("dependencies", []),
                )
                transaction.steps[step_id] = step
                
            elif step_type == "condition":
                step = AdvancedWorkflowStep(
                    step_id=step_id,
                    step_type=step_type,
                    condition=step_config.get("condition"),
                    if_steps=step_config.get("if_steps", []),
                    else_steps=step_config.get("else_steps", []),
                    dependencies=step_config.get("dependencies", []),
                )
                transaction.steps[step_id] = step
                # Recursively parse nested steps (blocks)
                if "if_steps_dict" in step_config:
                    self._parse_nested_steps(transaction, step_config["if_steps_dict"], step_id)
                if "else_steps_dict" in step_config:
                    self._parse_nested_steps(transaction, step_config["else_steps_dict"], step_id)
                # Always add all direct steps in if_steps and else_steps to the transaction
                if "if_steps_dict" in step_config:
                    for sub_id in step_config.get("if_steps", []):
                        sub_step_config = step_config["if_steps_dict"].get(sub_id)
                        if sub_step_config is not None:
                            self._parse_nested_steps(transaction, {sub_id: sub_step_config}, step_id)
                if "else_steps_dict" in step_config:
                    for sub_id in step_config.get("else_steps", []):
                        sub_step_config = step_config["else_steps_dict"].get(sub_id)
                        if sub_step_config is not None:
                            self._parse_nested_steps(transaction, {sub_id: sub_step_config}, step_id)
                    
            elif step_type == "parallel":
                step = AdvancedWorkflowStep(
                    step_id=step_id,
                    step_type=step_type,
                    parallel_steps=list(step_config.get("steps", {}).keys()),
                    dependencies=step_config.get("dependencies", []),
                )
                transaction.steps[step_id] = step
                
                # Recursively parse nested steps
                if "steps" in step_config:
                    self._parse_nested_steps(transaction, step_config["steps"], step_id)
                    
            elif step_type == "loop":
                step = AdvancedWorkflowStep(
                    step_id=step_id,
                    step_type=step_type,
                    loop_variable=step_config.get("variable"),
                    loop_collection=step_config.get("collection"),
                    loop_steps=list(step_config.get("steps", {}).keys()),
                    dependencies=step_config.get("dependencies", []),
                )
                transaction.steps[step_id] = step
                
                # Recursively parse nested steps
                if "steps" in step_config:
                    self._parse_nested_steps(transaction, step_config["steps"], step_id)

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

            # Execute steps by traversing the workflow tree recursively
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
        """Execute workflow steps by traversing the workflow tree recursively"""
        # Find top-level steps (those not referenced by any other step)
        all_referenced_steps = set()
        for step in transaction.steps.values():
            if step.step_type == "condition":
                all_referenced_steps.update(step.if_steps)
                all_referenced_steps.update(step.else_steps)
            elif step.step_type == "parallel":
                all_referenced_steps.update(step.parallel_steps)
            elif step.step_type == "loop":
                all_referenced_steps.update(step.loop_steps)
        
        top_level_steps = [step_id for step_id in transaction.steps.keys() 
                          if step_id not in all_referenced_steps]
        
        # Debug: print all steps and their dependencies
        print(f"DEBUG - Executing workflow with {len(transaction.steps)} steps:")
        for step_id, step in transaction.steps.items():
            print(f"DEBUG - Step {step_id}: type={step.step_type}, deps={step.dependencies}")
        print(f"DEBUG - Top-level steps: {top_level_steps}")
        
        # Execute top-level steps in dependency order
        await self._execute_step_list(transaction, top_level_steps)
    
    async def _execute_step_list(self, transaction: WorkflowTransaction, step_ids: List[str]):
        """Execute a list of steps in dependency order"""
        # Build dependency graph for these steps
        dependency_graph = {}
        for step_id in step_ids:
            step = transaction.steps[step_id]
            dependency_graph[step_id] = step.dependencies.copy()
        
        # Execute steps in topological order
        executed_steps: Set[str] = set()
        
        while len(executed_steps) < len(step_ids):
            # Find steps that can be executed (all dependencies satisfied)
            ready_steps = [
                step_id
                for step_id in step_ids
                if step_id not in executed_steps
                and all(dep in executed_steps for dep in dependency_graph[step_id])
            ]
            
            if not ready_steps:
                # Circular dependency or missing step
                remaining = set(step_ids) - executed_steps
                raise WorkflowError(
                    f"Circular dependency or missing step detected: {remaining}"
                )
            
            print(f"DEBUG - Ready steps: {ready_steps}")
            
            # Execute ready steps concurrently
            tasks = []
            for step_id in ready_steps:
                task = asyncio.create_task(
                    self._execute_advanced_step(transaction, step_id)
                )
                tasks.append(task)
            
            # Wait for all ready steps to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for failures and mark steps as completed
            for step_id, result in zip(ready_steps, results):
                if isinstance(result, Exception):
                    step = transaction.steps[step_id]
                    step.status = "failed"
                    step.error = str(result)
                    step.end_time = datetime.now()
                    raise WorkflowError(f"Step {step_id} failed: {result}")
                
                executed_steps.add(step_id)
                print(f"DEBUG - Completed step: {step_id}")

    async def _execute_advanced_step(
        self, transaction: WorkflowTransaction, step_id: str
    ):
        """Execute a single workflow step with advanced features"""
        step = transaction.steps[step_id]
        step.status = "running"
        step.start_time = datetime.now()

        try:
            if step.step_type == "service":
                await self._execute_service_step(transaction, step)
            elif step.step_type == "condition":
                await self._execute_condition_step(transaction, step)
            elif step.step_type == "parallel":
                await self._execute_parallel_step(transaction, step)
            elif step.step_type == "loop":
                await self._execute_loop_step(transaction, step)
            else:
                raise WorkflowError(f"Unknown step type: {step.step_type}")

            step.status = "completed"
            step.end_time = datetime.now()
            logger.info(f"Completed step {step_id}")

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.end_time = datetime.now()
            logger.error(f"Step {step_id} failed: {e}")
            raise

    async def _execute_service_step(
        self, transaction: WorkflowTransaction, step: AdvancedWorkflowStep
    ):
        """Execute a service step"""
        # Resolve inputs with dependency references
        resolved_inputs = self._resolve_step_inputs(transaction, step)

        # Store resolved inputs in metadata for response
        step.metadata["resolved_inputs"] = resolved_inputs

        # Debug: print inputs for validate tasks
        if step.task_name == "validate":
            print(f"DEBUG - Validate task inputs: {resolved_inputs}")

        # Get service and task
        service = self.registry.get_service(step.service_name)
        if not service:
            raise WorkflowError(f"Service '{step.service_name}' not found")

        task = service.get_task(step.task_name)
        if not task:
            raise WorkflowError(
                f"Task '{step.task_name}' not found in service '{step.service_name}'"
            )

        # Execute task with proper input validation
        logger.info(
            f"Executing step {step.step_id}: {step.service_name}.{step.task_name}"
        )

        # Validate inputs using the service's input model if available
        if service.input_model:
            logger.info(
                f"Service {step.service_name} has input model: {service.input_model}"
            )
            validated_inputs = service.input_model(**resolved_inputs)
            # Convert validated inputs back to dict for task execution
            task_inputs = validated_inputs.model_dump()
            logger.info(f"Validated inputs: {task_inputs}")
        else:
            logger.info(
                f"Service {step.service_name} has no input model, using raw inputs"
            )
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

        # Add to global outputs
        for key, value in step.outputs.items():
            global_key = f"{step.step_id}.{key}"
            transaction.global_outputs[global_key] = value

        # Set step as completed
        step.status = "completed"
        step.end_time = datetime.now()

    async def _execute_condition_step(
        self, transaction: WorkflowTransaction, step: AdvancedWorkflowStep
    ):
        """Execute a conditional step"""
        # Evaluate condition
        condition_result = self._evaluate_condition(transaction, step.condition)

        # Execute appropriate branch
        if condition_result:
            steps_to_execute = step.if_steps
        else:
            steps_to_execute = step.else_steps

        # Execute steps in the selected branch
        if steps_to_execute:
            await self._execute_step_list(transaction, steps_to_execute)

        # Store condition result
        step.outputs = {"condition_result": condition_result}

        # Set step as completed
        step.status = "completed"
        step.end_time = datetime.now()

    async def _execute_parallel_step(
        self, transaction: WorkflowTransaction, step: AdvancedWorkflowStep
    ):
        """Execute steps in parallel"""
        if not step.parallel_steps:
            # No steps to execute in parallel
            step.outputs = {"parallel_completed": True}
            step.status = "completed"
            step.end_time = datetime.now()
            return

        # Execute all parallel steps concurrently
        tasks = []
        for step_id in step.parallel_steps:
            if step_id in transaction.steps:
                task = asyncio.create_task(
                    self._execute_advanced_step(transaction, step_id)
                )
                tasks.append(task)

        # Wait for all parallel steps to complete
        if tasks:
            await asyncio.gather(*tasks)

        # Store parallel execution result
        step.outputs = {"parallel_completed": True}

        # Set step as completed
        step.status = "completed"
        step.end_time = datetime.now()

    async def _execute_loop_step(
        self, transaction: WorkflowTransaction, step: AdvancedWorkflowStep
    ):
        """Execute a loop step"""
        # Get the collection to iterate over
        collection = self._resolve_value(transaction, step.loop_collection)
        if not isinstance(collection, (list, tuple)):
            raise WorkflowError(
                f"Loop collection must be a list or tuple, got {type(collection)}"
            )

        print(f"DEBUG - Loop {step.step_id}: executing {len(collection)} iterations")
        print(f"DEBUG - Loop steps: {step.loop_steps}")

        loop_results = []

        # Execute loop steps for each item
        for i, item in enumerate(collection):
            print(f"DEBUG - Loop iteration {i}: {step.loop_variable} = {item}")
            
            # Set the loop variable in transaction context
            transaction.variables[step.loop_variable] = item

            # Execute all child steps in the loop in order, handling dependencies properly
            if step.loop_steps:
                print(f"DEBUG - Executing loop steps: {step.loop_steps}")
                # Build dependency graph for loop steps
                dependency_graph = {}
                for step_id in step.loop_steps:
                    if step_id in transaction.steps:
                        loop_step = transaction.steps[step_id]
                        dependency_graph[step_id] = loop_step.dependencies.copy()
                
                # Execute loop steps in dependency order
                executed_steps = set()
                top_level_executed = set()
                while len(top_level_executed) < len(step.loop_steps):
                    # Find steps that can be executed (all dependencies satisfied)
                    ready_steps = [
                        step_id
                        for step_id in step.loop_steps
                        if step_id not in top_level_executed
                        and all(dep in executed_steps for dep in dependency_graph.get(step_id, []))
                    ]
                    
                    if not ready_steps:
                        # Circular dependency or missing step
                        remaining = set(step.loop_steps) - top_level_executed
                        raise WorkflowError(
                            f"Circular dependency or missing step in loop: {remaining}"
                        )
                    
                    print(f"DEBUG - Loop ready steps: {ready_steps}")
                    
                    # Execute ready steps concurrently
                    tasks = []
                    for step_id in ready_steps:
                        task = asyncio.create_task(
                            self._execute_advanced_step(transaction, step_id)
                        )
                        tasks.append(task)
                    
                    # Wait for all ready steps to complete
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Check for failures and mark steps as completed
                    for step_id, result in zip(ready_steps, results):
                        if isinstance(result, Exception):
                            loop_step = transaction.steps[step_id]
                            loop_step.status = "failed"
                            loop_step.error = str(result)
                            loop_step.end_time = datetime.now()
                            raise WorkflowError(f"Loop step {step_id} failed: {result}")
                        
                        executed_steps.add(step_id)
                        top_level_executed.add(step_id)
                        print(f"DEBUG - Completed loop step: {step_id}")
                        
                        # Also mark child steps as completed if this is a block step
                        loop_step = transaction.steps[step_id]
                        if loop_step.step_type == "parallel" and loop_step.parallel_steps:
                            executed_steps.update(loop_step.parallel_steps)
                            print(f"DEBUG - Marked parallel child steps as completed: {loop_step.parallel_steps}")
                        elif loop_step.step_type == "condition":
                            if loop_step.if_steps:
                                executed_steps.update(loop_step.if_steps)
                            if loop_step.else_steps:
                                executed_steps.update(loop_step.else_steps)
                            print(f"DEBUG - Marked condition child steps as completed: if={loop_step.if_steps}, else={loop_step.else_steps}")
                
                print(f"DEBUG - Completed all steps in loop iteration {i}")

            # Collect results
            loop_results.append({"item": item, "completed": True})

        # Store loop results
        step.outputs = {
            "loop_results": loop_results,
            "total_iterations": len(collection),
        }

        # Set step as completed
        step.status = "completed"
        step.end_time = datetime.now()

    def _evaluate_condition(
        self, transaction: WorkflowTransaction, condition: str
    ) -> bool:
        """Evaluate a condition expression"""
        if not condition:
            return False

        print(f"DEBUG - Evaluating condition: {condition}")

        # Check if this is a step reference (e.g., "validate.success")
        if "." in condition and not condition.startswith("$"):
            # This looks like a step reference, try to resolve it
            try:
                resolved_condition = self._resolve_dependency_reference(
                    transaction, f"${condition}"
                )
                print(f"DEBUG - Resolved condition reference: {condition} -> {resolved_condition}")
                return bool(resolved_condition)
            except (WorkflowError, KeyError) as e:
                print(f"DEBUG - Failed to resolve condition reference: {condition} -> {e}")
                # If resolution fails, treat as a regular condition
                pass

        # Replace step references with their outputs
        resolved_condition = self._resolve_value(transaction, condition)
        print(f"DEBUG - Resolved condition value: {condition} -> {resolved_condition}")

        # Simple boolean evaluation
        if isinstance(resolved_condition, bool):
            return resolved_condition
        elif isinstance(resolved_condition, str):
            # Check for common boolean patterns
            if resolved_condition.lower() in ["true", "1", "yes", "on"]:
                return True
            elif resolved_condition.lower() in ["false", "0", "no", "off"]:
                return False
            else:
                # Non-empty string is considered True
                return bool(resolved_condition)
        elif isinstance(resolved_condition, (int, float)):
            # Non-zero numbers are True
            return bool(resolved_condition)
        elif isinstance(resolved_condition, (list, dict)):
            # Non-empty collections are True
            return bool(resolved_condition)
        else:
            # Other types - convert to boolean
            return bool(resolved_condition)

    def _build_dependency_graph(
        self, steps: Dict[str, AdvancedWorkflowStep]
    ) -> Dict[str, List[str]]:
        """Build dependency graph for workflow steps"""
        graph = {}
        for step_id, step in steps.items():
            graph[step_id] = step.dependencies.copy()
        return graph

    def _resolve_step_inputs(
        self, transaction: WorkflowTransaction, step: AdvancedWorkflowStep
    ) -> Dict[str, Any]:
        """Resolve step inputs by replacing dependency references with actual values"""
        resolved_inputs = {}

        for key, value in step.inputs.items():
            resolved_inputs[key] = self._resolve_value(transaction, value)

        return resolved_inputs

    def _resolve_value(self, transaction: WorkflowTransaction, value: Any) -> Any:
        """Recursively resolve dependency references in any value"""
        if isinstance(value, str):
            # Check if the entire string is a dependency reference
            if value.startswith("$"):
                return self._resolve_dependency_reference(transaction, value)
            # NEW: If the string matches a variable name, return the variable value
            if value in transaction.variables:
                return transaction.variables[value]
            # Handle EVAL: prefixed strings for string concatenation
            if value.startswith("EVAL:"):
                eval_expr = value[5:]  # Remove EVAL: prefix
                try:
                    # Create a safe evaluation context with transaction variables
                    eval_context = transaction.variables.copy()
                    # Add step outputs to context for evaluation
                    for step_id, step in transaction.steps.items():
                        if hasattr(step, 'outputs') and step.outputs:
                            for output_key, output_value in step.outputs.items():
                                eval_context[f"{step_id}.{output_key}"] = output_value
                    # Evaluate the expression
                    result = eval(eval_expr, {"__builtins__": {}}, eval_context)
                    return result
                except Exception as e:
                    # If evaluation fails, return the original string
                    return value
            # Check for embedded references of the form $step.field
            if "$" in value:
                # Replace embedded references
                def replace_ref(match):
                    ref = match.group(0)
                    return str(self._resolve_dependency_reference(transaction, ref))
                
                # Use regex to find and replace embedded references
                import re
                pattern = r'\$[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_\.]*'
                result = re.sub(pattern, replace_ref, value)
                return result
            return value
        elif isinstance(value, (list, tuple)):
            return [self._resolve_value(transaction, item) for item in value]
        elif isinstance(value, dict):
            return {k: self._resolve_value(transaction, v) for k, v in value.items()}
        else:
            return value

    def _resolve_dependency_reference(
        self, transaction: WorkflowTransaction, reference: str
    ) -> Any:
        """Resolve a dependency reference like '$step_name.output_field'"""
        # Remove the leading '$'
        ref_path = reference[1:]

        # Find the longest matching step ID that exists in the transaction
        parts = ref_path.split(".")
        step_id = None
        field_path = None
        
        # Try to find the longest matching step ID
        for i in range(len(parts) - 1, 0, -1):
            candidate_step_id = ".".join(parts[:i])
            if candidate_step_id in transaction.steps:
                step_id = candidate_step_id
                field_path = ".".join(parts[i:])
                break
        
        if not step_id:
            raise WorkflowError(f"Referenced step not found in reference: {reference}")

        # Get the step
        step = transaction.steps.get(step_id)
        if not step:
            raise WorkflowError(f"Referenced step '{step_id}' not found")

        if step.status != "completed":
            raise WorkflowError(
                f"Referenced step '{step_id}' is not completed (status: {step.status})"
            )

        # Navigate to the field in outputs
        value = step.outputs
        for part in field_path.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                raise WorkflowError(
                    f"Field '{field_path}' not found in step '{step_id}' outputs"
                )

        return value

    def _get_transaction_result(
        self, transaction: WorkflowTransaction
    ) -> Dict[str, Any]:
        """Get the result of a workflow transaction"""
        return {
            "transaction_id": transaction.transaction_id,
            "project_id": transaction.project_id,
            "status": transaction.status,
            "created_at": transaction.created_at.isoformat(),
            "started_at": (
                transaction.started_at.isoformat() if transaction.started_at else None
            ),
            "completed_at": (
                transaction.completed_at.isoformat()
                if transaction.completed_at
                else None
            ),
            "error": transaction.error,
            "steps": {
                step_id: {
                    "status": step.status,
                    "step_type": step.step_type,
                    "service": step.service_name,
                    "task": step.task_name,
                    "inputs": step.metadata.get("resolved_inputs", step.inputs),
                    "outputs": step.outputs,
                    "error": step.error,
                    "start_time": (
                        step.start_time.isoformat() if step.start_time else None
                    ),
                    "end_time": step.end_time.isoformat() if step.end_time else None,
                }
                for step_id, step in transaction.steps.items()
            },
            "outputs": transaction.global_outputs,
            "variables": transaction.variables,
            "metadata": transaction.metadata,
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
                "step_count": len(t.steps),
            }
            for t in self.transactions.values()
        ]

    async def execute_workflow(
        self, project_id: str, workflow: Dict[str, Any], project_dir: Path
    ) -> Dict[str, Any]:
        """Execute a workflow for a project"""
        # Create transaction
        transaction = self.create_transaction(workflow, project_id)

        # Execute transaction
        result = await self.execute_transaction(transaction.transaction_id)

        return result

    async def execute_dsl_workflow(
        self, project_id: str, dsl_code: str, project_dir: Path, **parameters
    ) -> Dict[str, Any]:
        """Execute a workflow defined in DSL"""
        # Create DSL transaction
        transaction = self.create_dsl_transaction(dsl_code, project_id, **parameters)

        # Execute transaction
        result = await self.execute_transaction(transaction.transaction_id)

        return result

    async def execute_template_workflow(
        self, project_id: str, template_name: str, project_dir: Path, **parameters
    ) -> Dict[str, Any]:
        """Execute a workflow from a template"""
        # Create template transaction
        transaction = self.create_template_transaction(
            template_name, project_id, **parameters
        )

        # Execute transaction
        result = await self.execute_transaction(transaction.transaction_id)

        return result
