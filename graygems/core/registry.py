from typing import Dict, Optional, List
from .service import Service


class ServiceRegistry:
    """Central registry for all services"""

    def __init__(self):
        self._services: Dict[str, Service] = {}

    def register(self, name: str, service: Service):
        """Register a service with a unique name"""
        if name in self._services:
            raise ValueError(f"Service '{name}' already registered")
        self._services[name] = service

    def get(self, name: str) -> Optional[Service]:
        """Retrieve a service by name"""
        return self._services.get(name)

    def get_service(self, name: str) -> Optional[Service]:
        """Alias for get method"""
        return self.get(name)

    def list_services(self) -> List[str]:
        """List all registered service names"""
        return list(self._services.keys())

    @property
    def services(self) -> Dict[str, Service]:
        """Get all registered services"""
        return self._services.copy()

    def unregister(self, name: str) -> bool:
        """Unregister a service by name"""
        if name in self._services:
            del self._services[name]
            return True
        return False

    def clear(self):
        """Clear all registered services"""
        self._services.clear()

    def __len__(self) -> int:
        """Return number of registered services"""
        return len(self._services)

    def __contains__(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self._services


global_registry = ServiceRegistry()
