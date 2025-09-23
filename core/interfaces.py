"""
Core interfaces and contracts for the WUTC application.
Defines abstract base classes that enforce SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar, Generic, List


# Result pattern for consistent error handling
T = TypeVar('T')


class Result(Generic[T]):
    """Result pattern implementation for error handling without exceptions."""

    def __init__(self, success: bool, data: T = None, error: str = None, message: str = None):
        self._success = success
        self._data = data
        self._error = error
        self._message = message

    @property
    def success(self) -> bool:
        return self._success

    @property
    def data(self) -> T:
        return self._data

    @property
    def error(self) -> str:
        return self._error

    @property
    def message(self) -> str:
        return self._message

    @classmethod
    def ok(cls, data: T, message: str = None) -> 'Result[T]':
        """Create a successful result."""
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(cls, error: str, message: str = None) -> 'Result[T]':
        """Create a failed result."""
        return cls(success=False, error=error, message=message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format for compatibility."""
        result = {
            "success": self._success,
            "message": self._message or ""
        }

        if self._success and self._data is not None:
            if hasattr(self._data, '__dict__'):
                result.update(self._data.__dict__)
            else:
                result["data"] = self._data

        if not self._success and self._error:
            result["error"] = self._error

        return result


# Domain Model Interface
class IValueObject(ABC):
    """Interface for value objects - immutable objects with value equality."""

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))


# Validation Interface
class IValidator(ABC):
    """Interface for input validation."""

    @abstractmethod
    def validate(self, value: Any) -> Result[bool]:
        """Validate the given value and return a Result."""
        pass


# Service Interfaces
class IConverter(ABC):
    """Interface for conversion services."""

    @abstractmethod
    def convert(self, input_value: Any) -> Result[Any]:
        """Convert input value to output format."""
        pass


class IFluidIdConverter(IConverter):
    """Interface for Fluid ID conversion operations."""

    @abstractmethod
    def fid_to_fluid_name(self, fid: str) -> Result[str]:
        """Convert SCADA FID to Fluid Name."""
        pass

    @abstractmethod
    def fluid_name_to_fid(self, fluid_name: str) -> Result[str]:
        """Convert Fluid Name to SCADA FID."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the conversion system."""
        pass


class ISpsTimeConverter(IConverter):
    """Interface for SPS Time conversion operations."""

    @abstractmethod
    def sps_timestamp_to_datetime(self, sps_timestamp: str) -> Result[Dict[str, Any]]:
        """Convert SPS Unix timestamp (in minutes) to DateTime."""
        pass

    @abstractmethod
    def datetime_to_sps_timestamp(self, datetime_str: str) -> Result[Dict[str, Any]]:
        """Convert DateTime string to SPS Unix timestamp (in minutes)."""
        pass

    @abstractmethod
    def get_current_sps_timestamp(self) -> Result[Dict[str, Any]]:
        """Get current datetime as SPS timestamp."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the SPS time conversion system."""
        pass


# UI Controller Interface
class IPageController(ABC):
    """Interface for page controllers that handle UI logic."""

    @abstractmethod
    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle input changes and return UI updates."""
        pass


# Repository Pattern (for future database operations)
class IRepository(ABC, Generic[T]):
    """Generic repository interface for data access."""

    @abstractmethod
    def get_by_id(self, id: Any) -> Result[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    def save(self, entity: T) -> Result[T]:
        """Save entity."""
        pass


# Configuration Interface
class IConfigurable(ABC):
    """Interface for configurable components."""

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the component with given settings."""
        pass


# CSV to RTU Conversion Interfaces
class ICsvValidator(IValidator):
    """Interface for CSV file validation."""

    @abstractmethod
    def validate_file_structure(self, file_path: str) -> Result[Dict[str, Any]]:
        """Validate CSV file structure and return metadata."""
        pass

    @abstractmethod
    def validate_file_content(self, content: str, filename: str) -> Result[Dict[str, Any]]:
        """Validate CSV content from upload and return metadata."""
        pass


class IRtuDataWriter(ABC):
    """Interface for writing RTU data files."""

    @abstractmethod
    def write_rtu_data(self, data_points: list, output_path: str) -> Result[Dict[str, Any]]:
        """Write RTU data points to file."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if RTU writer is available (sps_api installed)."""
        pass


class ICsvToRtuConverter(IConverter):
    """Interface for CSV to RTU conversion operations."""

    @abstractmethod
    def convert_file(self, csv_file_path: str, output_directory: str) -> Result[Dict[str, Any]]:
        """Convert a single CSV file to RTU format."""
        pass

    @abstractmethod
    def convert_multiple_files(self, csv_file_paths: list, output_directory: str) -> Result[Dict[str, Any]]:
        """Convert multiple CSV files to RTU format."""
        pass

    @abstractmethod
    def validate_conversion_request(self, csv_file_path: str, output_directory: str) -> Result[bool]:
        """Validate a conversion request before processing."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the conversion system."""
        pass


# Factory Interface
class IFactory(ABC, Generic[T]):
    """Interface for factory classes."""

    @abstractmethod
    def create(self, *args, **kwargs) -> T:
        """Create an instance of type T."""
        pass


# RTU Processing Interfaces
class IRtuFileReader(ABC):
    """Interface for reading RTU file information."""

    @abstractmethod
    def get_file_info(self, file_path: str) -> Result[Dict[str, Any]]:
        """Get RTU file information including timestamps and counts."""
        pass

    @abstractmethod
    def validate_file(self, file_path: str) -> Result[bool]:
        """Validate RTU file format and accessibility."""
        pass


class IRtuProcessor(ABC):
    """Interface for RTU processing operations."""

    @abstractmethod
    def resize_rtu(self, input_file: str, output_file: str, start_time: str = None,
                   end_time: str = None, tag_mapping_file: str = None) -> Result[Dict[str, Any]]:
        """Resize RTU file with optional time range and tag mapping."""
        pass

    @abstractmethod
    def export_csv_flat(self, input_file: str, output_file: str, start_time: str = None,
                        end_time: str = None, tags_file: str = None, enable_sampling: bool = False,
                        sample_interval: int = 60, sample_mode: str = "actual") -> Result[Dict[str, Any]]:
        """Export RTU data to CSV format with filtering and sampling options."""
        pass


class IRtuToCSVConverter(IConverter):
    """Interface for RTU to CSV conversion operations."""

    @abstractmethod
    def convert_file(self, rtu_file_path: str, output_directory: str,
                     processing_options: Dict[str, Any] = None) -> Result[Dict[str, Any]]:
        """Convert a single RTU file to CSV format."""
        pass

    @abstractmethod
    def convert_multiple_files(self, rtu_file_paths: List[str], output_directory: str,
                               processing_options: Dict[str, Any] = None) -> Result[Dict[str, Any]]:
        """Convert multiple RTU files to CSV format."""
        pass

    @abstractmethod
    def get_file_info(self, file_path: str) -> Result[Dict[str, Any]]:
        """Get RTU file information."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the RTU to CSV conversion system."""
        pass


class IRtuResizer(IConverter):
    """Interface for RTU file resizing operations."""

    @abstractmethod
    def resize_file(self, input_file_path: str, output_file_path: str,
                    start_time: str = None, end_time: str = None,
                    tag_mapping_file: str = None) -> Result[Dict[str, Any]]:
        """Resize RTU file by time range with optional tag mapping."""
        pass

    @abstractmethod
    def get_file_info(self, file_path: str) -> Result[Dict[str, Any]]:
        """Get RTU file information for resizing operations."""
        pass

    @abstractmethod
    def validate_resize_request(self, input_file_path: str, output_file_path: str,
                                start_time: str = None, end_time: str = None) -> Result[bool]:
        """Validate a resize request before processing."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the RTU resizing system."""
        pass
