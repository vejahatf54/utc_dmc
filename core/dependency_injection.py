"""
Dependency injection container for WUTC application.
Simple implementation that manages service lifecycles and dependencies.
"""

from typing import Any, Callable, Dict, Type, TypeVar
from enum import Enum


T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime enumeration."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"


class ServiceDescriptor:
    """Describes how a service should be created and managed."""

    def __init__(self, service_type: Type, implementation: Type = None,
                 factory: Callable = None, instance: Any = None,
                 lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT):
        self.service_type = service_type
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime


class DIContainer:
    """Simple dependency injection container."""

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}

    def register_transient(self, service_type: Type[T], implementation: Type[T] = None,
                           factory: Callable[[], T] = None) -> 'DIContainer':
        """Register a transient service (new instance each time)."""
        if implementation is None and factory is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            lifetime=ServiceLifetime.TRANSIENT
        )
        self._services[service_type] = descriptor
        return self

    def register_singleton(self, service_type: Type[T], implementation: Type[T] = None,
                           factory: Callable[[], T] = None, instance: T = None) -> 'DIContainer':
        """Register a singleton service (same instance every time)."""
        if instance is not None:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                instance=instance,
                lifetime=ServiceLifetime.SINGLETON
            )
        else:
            if implementation is None and factory is None:
                implementation = service_type
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation=implementation,
                factory=factory,
                lifetime=ServiceLifetime.SINGLETON
            )

        self._services[service_type] = descriptor
        return self

    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service instance."""
        if service_type not in self._services:
            raise ValueError(
                f"Service {service_type.__name__} is not registered")

        descriptor = self._services[service_type]

        # Handle pre-created instance
        if descriptor.instance is not None:
            return descriptor.instance

        # Handle singleton
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]

        # Create instance
        if descriptor.factory:
            instance = descriptor.factory()
        else:
            instance = self._create_instance(descriptor.implementation)

        # Cache singleton
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            self._singletons[service_type] = instance

        return instance

    def _create_instance(self, implementation_type: Type[T]) -> T:
        """Create an instance using constructor injection."""
        import inspect

        # Get constructor signature
        signature = inspect.signature(implementation_type.__init__)
        parameters = signature.parameters

        # Skip 'self' parameter
        param_names = [name for name in parameters.keys() if name != 'self']

        # Resolve dependencies
        kwargs = {}
        for param_name in param_names:
            param = parameters[param_name]
            if param.annotation != param.empty:
                # Try to resolve the parameter type
                try:
                    kwargs[param_name] = self.resolve(param.annotation)
                except ValueError:
                    # If we can't resolve it, skip it (assume it has a default value)
                    pass

        return implementation_type(**kwargs)

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services

    def clear(self) -> None:
        """Clear all registrations and singletons."""
        self._services.clear()
        self._singletons.clear()


# Global container instance
_container = DIContainer()


def get_container() -> DIContainer:
    """Get the global DI container instance."""
    return _container


def configure_services() -> DIContainer:
    """Configure all application services. Called at startup."""
    container = get_container()
    container.clear()  # Start fresh

    # Register validators
    from validation.input_validators import create_fid_validator, create_fluid_name_validator
    from core.interfaces import IValidator

    # Note: For now, we'll create validators directly in services
    # In a more complex system, we might register these separately

    # Register core services
    from core.interfaces import IFluidIdConverter
    from services.fluid_id_service import FluidIdConverterService

    container.register_singleton(IFluidIdConverter, FluidIdConverterService)

    # Register controllers (transient - new instance per request)
    from controllers.fluid_id_controller import FluidIdPageController
    container.register_transient(FluidIdPageController)

    return container
