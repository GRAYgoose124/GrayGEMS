"""
GrayGEMS Configuration Manager
Helps users set up and configure GrayGEMS instances
"""

import json
import logging
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .registry import ServiceRegistry
from .service import Service, Task

logger = logging.getLogger(__name__)


class ServiceConfig(BaseModel):
    """Configuration for a single service"""

    enabled: bool = True
    description: str = ""
    input_model: Optional[str] = None
    output_model: Optional[str] = None
    task_func: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)


class EntityConfig(BaseModel):
    """Configuration for an entity (group of services)"""

    enabled: bool = True
    description: str = ""
    module: str
    services: Dict[str, ServiceConfig] = Field(default_factory=dict)


class CoreServiceConfig(BaseModel):
    """Configuration for core services"""

    enabled: bool = True
    description: str = ""
    module: str
    tasks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class GrayGEMSConfig(BaseModel):
    """Main GrayGEMS configuration"""

    name: str
    version: str
    description: str = ""
    settings: Dict[str, Any] = Field(default_factory=dict)
    entities: Dict[str, EntityConfig] = Field(default_factory=dict)
    core_services: Dict[str, CoreServiceConfig] = Field(default_factory=dict)


class ConfigManager:
    """Manages GrayGEMS configuration files"""

    def __init__(self):
        self.config: Optional[GrayGEMSConfig] = None
        self._loaded_modules: Dict[str, Any] = {}

    def create_config(
        self,
        config_path: Path,
        name: str = "GrayGEMS Configuration",
        version: str = "1.0.0",
    ) -> GrayGEMSConfig:
        """Create a new GrayGEMS configuration file"""
        config = GrayGEMSConfig(
            name=name,
            version=version,
            description=f"Configuration for {name}",
            settings={
                "default_expiration_days": 30,
                "max_projects_per_user": 100,
                "auto_cleanup_expired": True,
            },
        )

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Save configuration
        self.save_config(config, config_path)
        logger.info(f"Created new configuration: {config_path}")

        return config

    def load_config(self, config_path: Path) -> GrayGEMSConfig:
        """Load configuration from file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            data = json.load(f)

        self.config = GrayGEMSConfig(**data)
        logger.info(f"Loaded configuration: {config_path}")

        return self.config

    def save_config(self, config: GrayGEMSConfig, config_path: Path):
        """Save configuration to file"""
        with open(config_path, "w") as f:
            json.dump(config.dict(), f, indent=2)

        logger.info(f"Saved configuration: {config_path}")

    def register_services(self, config: GrayGEMSConfig, registry: ServiceRegistry):
        """Register all services from configuration"""
        if not config:
            logger.warning("No configuration provided for service registration")
            return

        # Register core services first
        for service_name, service_config in config.core_services.items():
            if not service_config.enabled:
                continue

            try:
                # Import the module
                module = self._import_module(service_config.module)

                # Create service instance
                service = Service(
                    input_model=None,  # Will be set by tasks
                    output_model=None,  # Will be set by tasks
                    description=service_config.description,
                )

                # Set input/output models for known core services
                if service_name == "file_utils":
                    from .models import FileUtilsInput, FileUtilsOutput

                    service.input_model = FileUtilsInput
                    service.output_model = FileUtilsOutput
                    logger.info(f"Set input/output models for file_utils service")
                elif service_name == "data_processor":
                    from .models import DataProcessorInput, DataProcessorOutput

                    service.input_model = DataProcessorInput
                    service.output_model = DataProcessorOutput
                    logger.info(f"Set input/output models for data_processor service")

                # Register tasks
                for task_name, task_config in service_config.tasks.items():
                    if not task_config.get("enabled", True):
                        continue

                    # Set input/output models from task configuration
                    input_model_name = task_config.get("input_model")
                    output_model_name = task_config.get("output_model")

                    if input_model_name and service.input_model is None:
                        # Import the input model
                        if input_model_name == "FileUtilsInput":
                            from .models import FileUtilsInput

                            service.input_model = FileUtilsInput
                        elif input_model_name == "DataProcessorInput":
                            from .models import DataProcessorInput

                            service.input_model = DataProcessorInput

                    if output_model_name and service.output_model is None:
                        # Import the output model
                        if output_model_name == "FileUtilsOutput":
                            from .models import FileUtilsOutput

                            service.output_model = FileUtilsOutput
                        elif output_model_name == "DataProcessorOutput":
                            from .models import DataProcessorOutput

                            service.output_model = DataProcessorOutput

                    # Import task class or function
                    task_item = getattr(module, task_name, None)
                    if task_item:
                        if isinstance(task_item, type) and issubclass(task_item, Task):
                            # It's a Task class
                            task = task_item()
                            service.add_task(task_name, task)
                        elif callable(task_item):
                            # It's a function, create a wrapper task
                            from .service import Task

                            class FunctionTask(Task):
                                def __init__(self, func, input_model=None):
                                    self.func = func
                                    self.input_model = input_model

                                async def execute(
                                    self, inputs: Dict[str, Any], project_dir: Path
                                ) -> Dict[str, Any]:
                                    import asyncio

                                    # Validate/convert inputs to the input_model if available
                                    if self.input_model:
                                        model_inputs = self.input_model(**inputs)
                                        call_inputs = model_inputs
                                    else:
                                        call_inputs = inputs
                                    if asyncio.iscoroutinefunction(self.func):
                                        result = await self.func(
                                            call_inputs, project_dir
                                        )
                                    else:
                                        result = self.func(call_inputs, project_dir)
                                    return result

                            task = FunctionTask(task_item, service.input_model)
                            service.add_task(task_name, task)

                registry.register(service_name, service)
                logger.info(f"Registered core service: {service_name}")

            except Exception as e:
                logger.error(f"Failed to register core service {service_name}: {e}")

        # Register entity services
        for entity_name, entity_config in config.entities.items():
            if not entity_config.enabled:
                continue

            try:
                # Import the module
                module = self._import_module(entity_config.module)

                # Register services for this entity
                for service_name, service_config in entity_config.services.items():
                    if not service_config.enabled:
                        continue

                    # Create service instance
                    service = Service(
                        input_model=None,  # Will be set by tasks
                        output_model=None,  # Will be set by tasks
                        description=service_config.description,
                    )

                    # Register the task specified in task_func
                    if service_config.task_func:
                        task_name = service_config.task_func
                        task_item = getattr(module, task_name, None)
                        if task_item:
                            if isinstance(task_item, type) and issubclass(
                                task_item, Task
                            ):
                                # It's a Task class
                                task = task_item()
                                service.add_task(task_name, task)
                            elif callable(task_item):
                                # It's a function, create a wrapper task
                                from .service import Task

                                class FunctionTask(Task):
                                    def __init__(self, func, input_model=None):
                                        self.func = func
                                        self.input_model = input_model

                                    async def execute(
                                        self, inputs: Dict[str, Any], project_dir: Path
                                    ) -> Dict[str, Any]:
                                        import asyncio

                                        # Validate/convert inputs to the input_model if available
                                        if self.input_model:
                                            model_inputs = self.input_model(**inputs)
                                            call_inputs = model_inputs
                                        else:
                                            call_inputs = inputs
                                        if asyncio.iscoroutinefunction(self.func):
                                            result = await self.func(
                                                call_inputs, project_dir
                                            )
                                        else:
                                            result = self.func(call_inputs, project_dir)
                                        return result

                                task = FunctionTask(task_item, service.input_model)
                                service.add_task(task_name, task)

                    # Register with entity prefix
                    full_service_name = f"{entity_name}.{service_name}"
                    registry.register(full_service_name, service)
                    logger.info(f"Registered entity service: {full_service_name}")

            except Exception as e:
                logger.error(f"Failed to register entity {entity_name}: {e}")

    def _import_module(self, module_path: str) -> Any:
        """Import a module, caching the result"""
        if module_path in self._loaded_modules:
            return self._loaded_modules[module_path]

        try:
            module = importlib.import_module(module_path)
            self._loaded_modules[module_path] = module
            return module
        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {e}")
            raise

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        if not self.config:
            errors.append("No configuration loaded")
            return errors

        # Validate entities
        for entity_name, entity in self.config.entities.items():
            if not entity.enabled:
                continue

            if not entity.module:
                errors.append(f"Entity '{entity_name}' missing module")

            # Validate services
            for service_name, service_config in entity.services.items():
                if not service_config.get("enabled", True):
                    continue

                for task_name, task_config in service_config.get("tasks", {}).items():
                    if not task_config.get("enabled", True):
                        continue

                    if not task_config.get("input_model"):
                        errors.append(
                            f"Task '{entity_name}.{service_name}.{task_name}' missing input_model"
                        )

                    if not task_config.get("output_model"):
                        errors.append(
                            f"Task '{entity_name}.{service_name}.{task_name}' missing output_model"
                        )

        # Validate core services
        for service_name, service in self.config.core_services.items():
            if not service.enabled:
                continue

            if not service.module:
                errors.append(f"Core service '{service_name}' missing module")

        return errors

    def add_entity(self, entity_name: str, description: str, module: str) -> bool:
        """Add a new entity to the configuration"""
        if not self.config:
            return False

        self.config.entities[entity_name] = EntityConfig(
            enabled=True, description=description, module=module
        )

        logger.info(f"Added entity: {entity_name}")
        return True

    def add_service(
        self, entity_name: str, service_name: str, description: str
    ) -> bool:
        """Add a new service to an entity"""
        if not self.config or entity_name not in self.config.entities:
            return False

        if service_name not in self.config.entities[entity_name].services:
            self.config.entities[entity_name].services[service_name] = {}

        logger.info(f"Added service: {entity_name}.{service_name}")
        return True

    def add_task(
        self,
        entity_name: str,
        service_name: str,
        task_name: str,
        input_model: str,
        output_model: str,
        description: str = "",
    ) -> bool:
        """Add a new task to a service"""
        if not self.config or entity_name not in self.config.entities:
            return False

        if service_name not in self.config.entities[entity_name].services:
            self.config.entities[entity_name].services[service_name] = {}

        if "tasks" not in self.config.entities[entity_name].services[service_name]:
            self.config.entities[entity_name].services[service_name]["tasks"] = {}

        self.config.entities[entity_name].services[service_name]["tasks"][task_name] = {
            "enabled": True,
            "description": description,
            "input_model": input_model,
            "output_model": output_model,
        }

        logger.info(f"Added task: {entity_name}.{service_name}.{task_name}")
        return True

    def enable_entity(self, entity_name: str, enabled: bool = True) -> bool:
        """Enable or disable an entity"""
        if not self.config or entity_name not in self.config.entities:
            return False

        self.config.entities[entity_name].enabled = enabled
        logger.info(f"{'Enabled' if enabled else 'Disabled'} entity: {entity_name}")
        return True

    def enable_service(
        self, entity_name: str, service_name: str, enabled: bool = True
    ) -> bool:
        """Enable or disable a service"""
        if not self.config or entity_name not in self.config.entities:
            return False

        if service_name not in self.config.entities[entity_name].services:
            return False

        self.config.entities[entity_name].services[service_name]["enabled"] = enabled
        logger.info(
            f"{'Enabled' if enabled else 'Disabled'} service: {entity_name}.{service_name}"
        )
        return True

    def enable_task(
        self, entity_name: str, service_name: str, task_name: str, enabled: bool = True
    ) -> bool:
        """Enable or disable a task"""
        if not self.config or entity_name not in self.config.entities:
            return False

        if service_name not in self.config.entities[entity_name].services:
            return False

        if "tasks" not in self.config.entities[entity_name].services[service_name]:
            return False

        if (
            task_name
            not in self.config.entities[entity_name].services[service_name]["tasks"]
        ):
            return False

        self.config.entities[entity_name].services[service_name]["tasks"][task_name][
            "enabled"
        ] = enabled
        logger.info(
            f"{'Enabled' if enabled else 'Disabled'} task: {entity_name}.{service_name}.{task_name}"
        )
        return True

    def list_entities(self) -> List[str]:
        """List all entities in the configuration"""
        if not self.config:
            return []

        return list(self.config.entities.keys())

    def list_services(self, entity_name: str) -> List[str]:
        """List all services in an entity"""
        if not self.config or entity_name not in self.config.entities:
            return []

        return list(self.config.entities[entity_name].services.keys())

    def list_tasks(self, entity_name: str, service_name: str) -> List[str]:
        """List all tasks in a service"""
        if not self.config or entity_name not in self.config.entities:
            return []

        if service_name not in self.config.entities[entity_name].services:
            return []

        tasks = (
            self.config.entities[entity_name].services[service_name].get("tasks", {})
        )
        return list(tasks.keys())

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the configuration"""
        if not self.config:
            return {}

        summary = {
            "name": self.config.name,
            "version": self.config.version,
            "description": self.config.description,
            "entities": {},
            "core_services": {},
        }

        # Entity summary
        for entity_name, entity in self.config.entities.items():
            summary["entities"][entity_name] = {
                "enabled": entity.enabled,
                "description": entity.description,
                "services": {},
            }

            for service_name, service_config in entity.services.items():
                summary["entities"][entity_name]["services"][service_name] = {
                    "enabled": service_config.get("enabled", True),
                    "tasks": list(service_config.get("tasks", {}).keys()),
                }

        # Core services summary
        for service_name, service in self.config.core_services.items():
            summary["core_services"][service_name] = {
                "enabled": service.enabled,
                "description": service.description,
                "tasks": list(service.tasks.keys()),
            }

        return summary
