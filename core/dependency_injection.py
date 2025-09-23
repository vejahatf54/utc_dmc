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
        self._string_services: Dict[str, Type] = {}  # String to Type mapping

    @classmethod
    def get_instance(cls) -> 'DIContainer':
        """Get the singleton instance of the DI container."""
        return _container

    def register_transient(self, service_type: Type[T], implementation: Type[T] = None,
                           factory: Callable[[], T] = None, name: str = None) -> 'DIContainer':
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

        # Also register by string name if provided
        if name:
            self._string_services[name] = service_type

        return self

    def register_singleton(self, service_type: Type[T], implementation: Type[T] = None,
                           factory: Callable[[], T] = None, instance: T = None, name: str = None) -> 'DIContainer':
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

        # Also register by string name if provided
        if name:
            self._string_services[name] = service_type

        return self

    def resolve(self, service_type) -> Any:
        """Resolve a service instance by type or string name."""
        # Handle string-based resolution
        if isinstance(service_type, str):
            if service_type not in self._string_services:
                raise ValueError(f"Service '{service_type}' is not registered")
            service_type = self._string_services[service_type]

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
        self._string_services.clear()


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
    from validation.input_validators import (
        create_fid_validator, create_fluid_name_validator,
        create_sps_timestamp_validator, create_datetime_validator
    )
    from core.interfaces import IValidator

    # Note: For now, we'll create validators directly in services
    # In a more complex system, we might register these separately

    # Register core services
    from core.interfaces import IFluidIdConverter, ISpsTimeConverter
    from services.fluid_id_service import FluidIdConverterService
    from services.sps_time_converter_service import SpsTimeConverterService

    container.register_singleton(IFluidIdConverter, FluidIdConverterService)

    # Register SPS Time Converter service with validators
    def sps_service_factory(): return SpsTimeConverterService(
        timestamp_validator=create_sps_timestamp_validator(),
        datetime_validator=create_datetime_validator()
    )
    container.register_singleton(
        ISpsTimeConverter, factory=sps_service_factory)
    container.register_singleton(
        SpsTimeConverterService, factory=sps_service_factory, name="SpsTimeConverterService")

    # Register CSV to RTU services
    from core.interfaces import ICsvToRtuConverter, ICsvValidator, IRtuDataWriter
    from services.csv_to_rtu_service import (
        CsvToRtuConverterService, SpsRtuDataWriter, MockRtuDataWriter
    )
    from validation.csv_validators import CsvToRtuValidator

    # Register CSV validators
    container.register_singleton(
        ICsvValidator, CsvToRtuValidator, name="csv_validator")

    # Register RTU data writer (use real sps_api writer if available, otherwise mock)
    def rtu_writer_factory():
        writer = SpsRtuDataWriter()
        if writer.is_available():
            return writer
        else:
            return MockRtuDataWriter()

    container.register_singleton(
        IRtuDataWriter, factory=rtu_writer_factory, name="rtu_writer")

    # Register CSV to RTU converter service
    def csv_converter_factory():
        csv_validator = container.resolve("csv_validator")
        rtu_writer = container.resolve("rtu_writer")
        return CsvToRtuConverterService(csv_validator, rtu_writer)

    container.register_singleton(
        ICsvToRtuConverter, factory=csv_converter_factory, name="csv_to_rtu_converter")

    # Register controllers (transient - new instance per request)
    from controllers.fluid_id_controller import FluidIdPageController
    from controllers.sps_time_controller import SpsTimeConverterPageController
    from controllers.csv_to_rtu_controller import CsvToRtuPageController

    container.register_transient(
        FluidIdPageController, name="FluidIdPageController")
    container.register_transient(
        SpsTimeConverterPageController, name="SpsTimeConverterPageController")

    # Register CSV to RTU controller
    def csv_controller_factory():
        converter_service = container.resolve("csv_to_rtu_converter")
        csv_validator = container.resolve("csv_validator")
        return CsvToRtuPageController(converter_service, csv_validator)

    container.register_transient(
        CsvToRtuPageController, factory=csv_controller_factory, name="csv_to_rtu_controller")

    return container
