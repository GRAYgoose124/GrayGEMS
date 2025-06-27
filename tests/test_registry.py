"""
Tests for GrayGEMS Service Registry
"""

import pytest
from unittest.mock import Mock
from graygems.core.registry import ServiceRegistry
from graygems.core.service import Service


class TestServiceRegistry:
    """Test ServiceRegistry functionality"""

    def test_register_service(self, service_registry, mock_service):
        """Test registering a service"""
        service_registry.register("test_service", mock_service)

        assert "test_service" in service_registry.services
        assert service_registry.get("test_service") == mock_service

    def test_register_duplicate_service(self, service_registry, mock_service):
        """Test registering a duplicate service raises error"""
        service_registry.register("test_service", mock_service)

        with pytest.raises(
            ValueError, match="Service 'test_service' already registered"
        ):
            service_registry.register("test_service", mock_service)

    def test_get_nonexistent_service(self, service_registry):
        """Test getting a non-existent service returns None"""
        service = service_registry.get("nonexistent")
        assert service is None

    def test_get_service_alias(self, service_registry, mock_service):
        """Test get_service alias works"""
        service_registry.register("test_service", mock_service)

        service = service_registry.get_service("test_service")
        assert service == mock_service

    def test_list_services(self, service_registry, mock_service):
        """Test listing all services"""
        service_registry.register("service1", mock_service)
        service_registry.register("service2", mock_service)

        services = service_registry.list_services()
        assert "service1" in services
        assert "service2" in services
        assert len(services) == 2

    def test_services_property(self, service_registry, mock_service):
        """Test services property returns copy"""
        service_registry.register("test_service", mock_service)

        services = service_registry.services
        assert "test_service" in services
        assert services["test_service"] == mock_service

        # Test that modifying the copy doesn't affect the registry
        services["test_service"] = None
        assert service_registry.get("test_service") == mock_service

    def test_unregister_service(self, service_registry, mock_service):
        """Test unregistering a service"""
        service_registry.register("test_service", mock_service)

        success = service_registry.unregister("test_service")
        assert success is True
        assert "test_service" not in service_registry.services

    def test_unregister_nonexistent_service(self, service_registry):
        """Test unregistering a non-existent service"""
        success = service_registry.unregister("nonexistent")
        assert success is False

    def test_clear_services(self, service_registry, mock_service):
        """Test clearing all services"""
        service_registry.register("service1", mock_service)
        service_registry.register("service2", mock_service)

        service_registry.clear()
        assert len(service_registry.services) == 0
        assert len(service_registry) == 0

    def test_len_operator(self, service_registry, mock_service):
        """Test len operator"""
        assert len(service_registry) == 0

        service_registry.register("service1", mock_service)
        assert len(service_registry) == 1

        service_registry.register("service2", mock_service)
        assert len(service_registry) == 2

    def test_contains_operator(self, service_registry, mock_service):
        """Test in operator"""
        service_registry.register("test_service", mock_service)

        assert "test_service" in service_registry
        assert "nonexistent" not in service_registry

    def test_multiple_service_types(self, service_registry):
        """Test registering different types of services"""
        service1 = Mock(spec=Service)
        service2 = Mock(spec=Service)

        service_registry.register("file_service", service1)
        service_registry.register("data_service", service2)

        assert service_registry.get("file_service") == service1
        assert service_registry.get("data_service") == service2
        assert len(service_registry) == 2


class TestServiceRegistryIntegration:
    """Test ServiceRegistry integration scenarios"""

    def test_service_lifecycle(self, service_registry, mock_service):
        """Test complete service lifecycle"""
        # Register
        service_registry.register("lifecycle_service", mock_service)
        assert "lifecycle_service" in service_registry

        # Get
        service = service_registry.get("lifecycle_service")
        assert service == mock_service

        # Unregister
        success = service_registry.unregister("lifecycle_service")
        assert success is True
        assert "lifecycle_service" not in service_registry

        # Verify gone
        service = service_registry.get("lifecycle_service")
        assert service is None

    def test_registry_isolation(self):
        """Test that different registry instances are isolated"""
        registry1 = ServiceRegistry()
        registry2 = ServiceRegistry()

        service1 = Mock(spec=Service)
        service2 = Mock(spec=Service)

        registry1.register("test", service1)
        registry2.register("test", service2)

        assert registry1.get("test") == service1
        assert registry2.get("test") == service2
        assert registry1.get("test") != registry2.get("test")

    def test_registry_iteration(self, service_registry, mock_service):
        """Test iterating over registry services"""
        service_registry.register("service1", mock_service)
        service_registry.register("service2", mock_service)

        service_names = list(service_registry.services.keys())
        assert "service1" in service_names
        assert "service2" in service_names
        assert len(service_names) == 2
