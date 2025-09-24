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

    # Register RTU services
    from core.interfaces import IRtuFileReader, IRtuToCSVConverter, IRtuResizer
    from services.rtu_file_reader_service import RtuFileReaderService
    from services.rtu_to_csv_converter_service import RtuToCsvConverterService
    from services.rtu_resizer_service import RtuResizerService

    # Register RTU file reader (singleton - stateless service)
    container.register_singleton(
        IRtuFileReader, RtuFileReaderService, name="rtu_file_reader")

    # Register RTU to CSV converter service
    def rtu_csv_converter_factory():
        file_reader = container.resolve("rtu_file_reader")
        return RtuToCsvConverterService(file_reader)

    container.register_singleton(
        IRtuToCSVConverter, factory=rtu_csv_converter_factory, name="rtu_to_csv_converter")

    # Register RTU resizer service
    def rtu_resizer_factory():
        file_reader = container.resolve("rtu_file_reader")
        return RtuResizerService(file_reader)

    container.register_singleton(
        IRtuResizer, factory=rtu_resizer_factory, name="rtu_resizer")

    # Register RTU controllers (transient - new instance per request)
    from controllers.rtu_to_csv_controller import RtuToCsvPageController
    from controllers.rtu_resizer_controller import RtuResizerPageController

    # Register RTU to CSV controller
    def rtu_csv_controller_factory():
        converter_service = container.resolve("rtu_to_csv_converter")
        file_reader = container.resolve("rtu_file_reader")
        return RtuToCsvPageController(converter_service, file_reader)

    container.register_transient(
        RtuToCsvPageController, factory=rtu_csv_controller_factory, name="rtu_to_csv_controller")

    # Register RTU resizer controller
    def rtu_resizer_controller_factory():
        resizer_service = container.resolve("rtu_resizer")
        file_reader = container.resolve("rtu_file_reader")
        return RtuResizerPageController(resizer_service, file_reader)

    container.register_transient(
        RtuResizerPageController, factory=rtu_resizer_controller_factory, name="rtu_resizer_controller")

    # Register Review services
    from core.interfaces import IReviewFileReader, IReviewToCsvConverter, IReviewProcessor
    from services.review_file_reader_service import ReviewFileReaderService
    from services.review_processor_service import ReviewProcessorService
    from services.review_to_csv_converter_service import ReviewToCsvConverterService

    # Register Review file reader (singleton - stateless service)
    container.register_singleton(
        IReviewFileReader, ReviewFileReaderService, name="review_file_reader")

    # Register Review processor (singleton - manages its own state)
    container.register_singleton(
        IReviewProcessor, ReviewProcessorService, name="review_processor")

    # Register Review to CSV converter service
    def review_csv_converter_factory():
        file_reader = container.resolve("review_file_reader")
        processor = container.resolve("review_processor")
        return ReviewToCsvConverterService(file_reader, processor)

    container.register_singleton(
        IReviewToCsvConverter, factory=review_csv_converter_factory, name="review_to_csv_converter")

    # Register Review controller (transient - new instance per request)
    from controllers.review_to_csv_controller import ReviewToCsvPageController

    def review_csv_controller_factory():
        converter_service = container.resolve("review_to_csv_converter")
        file_reader = container.resolve("review_file_reader")
        return ReviewToCsvPageController(converter_service, file_reader)

    container.register_transient(
        ReviewToCsvPageController, factory=review_csv_controller_factory, name="review_to_csv_controller")

    # Register Archive services
    from core.interfaces import IArchiveValidator, IArchivePathService, IArchiveFileExtractor, IFetchArchiveService, IFetchArchiveController
    from validation.archive_validators import create_fetch_archive_request_validator
    from services.archive_path_service import create_archive_path_service
    from services.archive_file_extractor import create_archive_file_extractor
    from services.fetch_archive_service import FetchArchiveService, LegacyFetchArchiveService
    from controllers.fetch_archive_controller import FetchArchivePageController

    # Register archive validator (singleton - stateless service)
    container.register_singleton(
        IArchiveValidator, factory=create_fetch_archive_request_validator, name="archive_validator")

    # Register archive path service (singleton - manages configuration)
    container.register_singleton(
        IArchivePathService, factory=create_archive_path_service, name="archive_path_service")

    # Register archive file extractor (singleton - stateless service)
    container.register_singleton(
        IArchiveFileExtractor, factory=create_archive_file_extractor, name="archive_file_extractor")

    # Register fetch archive service
    def fetch_archive_service_factory():
        validator = container.resolve("archive_validator")
        path_service = container.resolve("archive_path_service")
        file_extractor = container.resolve("archive_file_extractor")
        return FetchArchiveService(validator, path_service, file_extractor)

    container.register_singleton(
        IFetchArchiveService, factory=fetch_archive_service_factory, name="fetch_archive_service")

    # Register legacy wrapper for backward compatibility
    def legacy_archive_service_factory():
        new_service = container.resolve("fetch_archive_service")
        return LegacyFetchArchiveService(new_service)

    container.register_singleton(
        LegacyFetchArchiveService, factory=legacy_archive_service_factory, name="legacy_fetch_archive_service")

    # Register fetch archive controller (transient - new instance per request)
    def fetch_archive_controller_factory():
        archive_service = container.resolve("fetch_archive_service")
        return FetchArchivePageController(archive_service)

    container.register_transient(
        IFetchArchiveController, factory=fetch_archive_controller_factory, name="fetch_archive_controller")
    container.register_transient(
        FetchArchivePageController, factory=fetch_archive_controller_factory, name="fetch_archive_page_controller")

    # Register RTU Data Services (following clean architecture)
    from core.interfaces import IFetchRtuDataService, IFetchRtuDataController, IRtuLineProvider, IRtuDataProcessor
    from services.fetch_rtu_data_service import FetchRtuDataServiceV2, RtuLineProvider, RtuDataProcessor, LegacyFetchRtuDataService
    from controllers.fetch_rtu_data_controller import FetchRtuDataPageController
    from validation.rtu_validators import create_composite_rtu_validator, CompositeRtuValidator

    # Register RTU line provider (singleton - stateless service)
    container.register_singleton(
        IRtuLineProvider, RtuLineProvider, name="rtu_line_provider")

    # Register RTU data processor (singleton - stateless service)
    container.register_singleton(
        IRtuDataProcessor, RtuDataProcessor, name="rtu_data_processor")

    # Register RTU composite validator (singleton - stateless validator)
    container.register_singleton(
        CompositeRtuValidator, factory=create_composite_rtu_validator, name="rtu_composite_validator")

    # Register fetch RTU data service
    def fetch_rtu_service_factory():
        line_provider = container.resolve("rtu_line_provider")
        data_processor = container.resolve("rtu_data_processor")
        return FetchRtuDataServiceV2(line_provider, data_processor)

    container.register_singleton(
        IFetchRtuDataService, factory=fetch_rtu_service_factory, name="fetch_rtu_service")

    # Register legacy wrapper for backward compatibility
    def legacy_rtu_service_factory():
        new_service = container.resolve("fetch_rtu_service")
        return LegacyFetchRtuDataService(new_service)

    container.register_singleton(
        LegacyFetchRtuDataService, factory=legacy_rtu_service_factory, name="legacy_fetch_rtu_service")

    # Register fetch RTU controller (transient - new instance per request)
    def fetch_rtu_controller_factory():
        rtu_service = container.resolve("fetch_rtu_service")
        composite_validator = container.resolve("rtu_composite_validator")
        return FetchRtuDataPageController(rtu_service, composite_validator)

    container.register_transient(
        IFetchRtuDataController, factory=fetch_rtu_controller_factory, name="fetch_rtu_controller")
    container.register_transient(
        FetchRtuDataPageController, factory=fetch_rtu_controller_factory, name="fetch_rtu_page_controller")

    return container
