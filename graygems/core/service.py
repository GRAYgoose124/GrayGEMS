from typing import Generic, TypeVar, Type, List, Callable, Optional, Dict, Any
from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel

InputT = TypeVar('InputT', bound=BaseModel)
OutputT = TypeVar('OutputT', bound=BaseModel)

class Task(ABC):
    """Base class for all tasks"""
    
    @abstractmethod
    async def execute(self, inputs: Dict[str, Any], project_dir: Path) -> Dict[str, Any]:
        """Execute the task with inputs and project directory"""
        pass

class Service(Generic[InputT, OutputT], ABC):
    """Generic service wrapper for tasks"""
    
    def __init__(
        self,
        input_model: Type[InputT],
        output_model: Type[OutputT],
        task_func: Optional[Callable] = None,
        dependencies: Optional[List[str]] = None,
        description: str = ""
    ):
        self.input_model = input_model
        self.output_model = output_model
        self.task_func = task_func
        self.dependencies = dependencies or []
        self.description = description
        self.tasks: Dict[str, Task] = {}
    
    def add_task(self, name: str, task: Task):
        """Add a task to this service"""
        self.tasks[name] = task
    
    def get_task(self, name: str) -> Optional[Task]:
        """Get a task by name"""
        return self.tasks.get(name)
    
    def list_tasks(self) -> List[str]:
        """List all task names"""
        return list(self.tasks.keys())
    
    def execute(self, inputs: InputT, project: "Project", context: Optional[dict] = None) -> OutputT:
        """Execute the service with validated inputs and project context"""
        if self.task_func is None:
            return self._execute(inputs, project, context)
        
        # Check if task needs project_dir
        import inspect
        sig = inspect.signature(self.task_func)
        
        if 'project_dir' in sig.parameters:
            result = self.task_func(**inputs.model_dump(), project_dir=project.project_dir)
        else:
            result = self.task_func(**inputs.model_dump())
        
        # Wrap result in output model if needed
        if isinstance(result, self.output_model):
            return result
        elif isinstance(result, dict):
            return self.output_model(**result)
        else:
            return self.output_model(result=result)
    
    def _execute(self, inputs: InputT, project: "Project", context: Optional[dict] = None) -> OutputT:
        """Override for custom execution logic"""
        pass
