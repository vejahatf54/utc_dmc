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


# Review Processing Interfaces
class IReviewFileReader(ABC):
    """Interface for reading Review file information."""

    @abstractmethod
    def get_file_info(self, file_path: str) -> Result[Dict[str, Any]]:
        """Get Review file information including timestamps and metadata."""
        pass

    @abstractmethod
    def validate_file(self, file_path: str) -> Result[bool]:
        """Validate Review file format and accessibility."""
        pass


class IReviewToCsvConverter(IConverter):
    """Interface for Review to CSV conversion operations."""

    @abstractmethod
    def convert_directory(self, review_directory_path: str, output_directory: str,
                          processing_options: Dict[str, Any] = None) -> Result[Dict[str, Any]]:
        """Convert all Review files in a directory to CSV format."""
        pass

    @abstractmethod
    def convert_files(self, review_file_paths: List[str], output_directory: str,
                      processing_options: Dict[str, Any] = None) -> Result[Dict[str, Any]]:
        """Convert specific Review files to CSV format."""
        pass

    @abstractmethod
    def get_directory_info(self, directory_path: str) -> Result[Dict[str, Any]]:
        """Get information about Review files in a directory."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the Review to CSV conversion system."""
        pass

    @abstractmethod
    def cancel_conversion(self) -> Result[bool]:
        """Cancel ongoing conversion operations."""
        pass


class IReviewProcessor(ABC):
    """Interface for Review processing operations using dreview.exe."""

    @abstractmethod
    def process_review_file(self, review_file_path: str, output_csv_path: str,
                            start_time: str, end_time: str, peek_items: List[str] = None,
                            dump_all: bool = False, frequency: float = None) -> Result[Dict[str, Any]]:
        """Process a single Review file to CSV using dreview.exe."""
        pass

    @abstractmethod
    def validate_processing_options(self, start_time: str, end_time: str,
                                    peek_items: List[str] = None) -> Result[bool]:
        """Validate Review processing options."""
        pass


# Archive Processing Interfaces
class IArchiveValidator(IValidator):
    """Interface for archive validation operations."""

    @abstractmethod
    def validate_archive_date(self, archive_date: Any) -> Result[bool]:
        """Validate archive date."""
        pass

    @abstractmethod
    def validate_pipeline_lines(self, pipeline_lines: List[str]) -> Result[bool]:
        """Validate pipeline line selections."""
        pass

    @abstractmethod
    def validate_output_directory(self, output_directory: str) -> Result[bool]:
        """Validate output directory path."""
        pass

    @abstractmethod
    def validate_fetch_request(self, archive_date: Any, pipeline_lines: List[str], 
                               output_directory: str) -> Result[bool]:
        """Validate complete fetch archive request."""
        pass


class IArchiveFileExtractor(ABC):
    """Interface for archive file extraction operations."""

    @abstractmethod
    def extract_archive_file(self, zip_file_path: str, output_directory: str) -> Result[Dict[str, Any]]:
        """Extract a single archive file to output directory."""
        pass

    @abstractmethod
    def extract_multiple_archives(self, zip_file_paths: List[str], 
                                   output_directory: str) -> Result[Dict[str, Any]]:
        """Extract multiple archive files to output directory."""
        pass

    @abstractmethod
    def get_archive_info(self, zip_file_path: str) -> Result[Dict[str, Any]]:
        """Get information about an archive file."""
        pass


class IArchivePathService(ABC):
    """Interface for archive path operations."""

    @abstractmethod
    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """Get list of available pipeline lines from archive structure."""
        pass

    @abstractmethod
    def check_path_accessibility(self) -> Result[bool]:
        """Check if archive path is accessible."""
        pass

    @abstractmethod
    def get_line_archive_path(self, line_id: str, archive_date: Any) -> Result[str]:
        """Get the archive path for a specific line and date."""
        pass

    @abstractmethod
    def find_archive_files(self, line_id: str, archive_date: Any) -> Result[List[str]]:
        """Find all archive files for a specific line and date."""
        pass


class IFetchArchiveService(IConverter):
    """Interface for fetch archive operations."""

    @abstractmethod
    def fetch_archive_data(self, archive_date: Any, line_ids: List[str], 
                           output_directory: str) -> Result[Dict[str, Any]]:
        """Fetch archive data for specified date and pipeline lines."""
        pass

    @abstractmethod
    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """Get list of available pipeline lines."""
        pass

    @abstractmethod
    def validate_fetch_parameters(self, archive_date: Any, line_ids: List[str], 
                                  output_directory: str) -> Result[bool]:
        """Validate parameters for fetch operation."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the archive system."""
        pass


class IFetchArchiveController(IPageController):
    """Interface for fetch archive page controller."""

    @abstractmethod
    def handle_date_selection(self, archive_date: Any) -> Result[Dict[str, Any]]:
        """Handle archive date selection and validation."""
        pass

    @abstractmethod
    def handle_line_selection(self, selected_lines: List[str]) -> Result[Dict[str, Any]]:
        """Handle pipeline line selection and validation."""
        pass

    @abstractmethod
    def handle_output_directory_selection(self, output_directory: str) -> Result[Dict[str, Any]]:
        """Handle output directory selection and validation."""
        pass

    @abstractmethod
    def handle_fetch_request(self, archive_date: Any, selected_lines: List[str], 
                             output_directory: str) -> Result[Dict[str, Any]]:
        """Handle fetch archive request execution."""
        pass

    @abstractmethod
    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """Get available pipeline lines for UI."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for help modal."""
        pass


# Fetch RTU Data Interfaces
class IFetchRtuDataService(ABC):
    """Interface for RTU data fetching service."""

    @abstractmethod
    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """
        Get list of available pipeline lines from data source.
        
        Returns:
            Result containing list of lines with 'label' and 'value' keys
        """
        pass

    @abstractmethod 
    def fetch_rtu_data(self, line_selection: Any, date_range: Any, 
                       output_directory: Any, server_filter: Any = None,
                       max_parallel_workers: int = 4) -> Result[Any]:
        """
        Fetch RTU data for specified parameters.
        
        Args:
            line_selection: Selected pipeline lines (domain object)
            date_range: Date range for data fetching (domain object)
            output_directory: Output directory (domain object)
            server_filter: Optional server filter (domain object)
            max_parallel_workers: Maximum parallel processing workers
            
        Returns:
            Result containing fetch operation results
        """
        pass

    @abstractmethod
    def validate_data_source_availability(self) -> Result[bool]:
        """
        Validate that the RTU data source is accessible.
        
        Returns:
            Result indicating if data source is available
        """
        pass


class IRtuLineProvider(ABC):
    """Interface for providing available RTU pipeline lines."""

    @abstractmethod
    def get_lines(self) -> Result[List[Dict[str, str]]]:
        """
        Get available pipeline lines from data source.
        
        Returns:
            Result containing list of available lines
        """
        pass

    @abstractmethod
    def validate_line_exists(self, line_id: str) -> Result[bool]:
        """
        Validate that a specific line exists in the data source.
        
        Args:
            line_id: Pipeline line identifier
            
        Returns:
            Result indicating if line exists
        """
        pass


class IRtuDateValidator(ABC):
    """Interface for RTU date validation."""

    @abstractmethod
    def validate_single_date(self, date_value: Any) -> Result[Any]:
        """
        Validate a single date for RTU data fetching.
        
        Args:
            date_value: Date value to validate
            
        Returns:
            Result containing validated domain object
        """
        pass

    @abstractmethod
    def validate_date_range(self, start_date: Any, end_date: Any) -> Result[Any]:
        """
        Validate a date range for RTU data fetching.
        
        Args:
            start_date: Start date value
            end_date: End date value
            
        Returns:
            Result containing validated domain object
        """
        pass


class IRtuDataProcessor(ABC):
    """Interface for RTU data processing operations."""

    @abstractmethod
    def process_zip_file(self, file_info: Dict[str, Any], output_dir: str) -> Result[Dict[str, Any]]:
        """
        Process a single RTU zip file.
        
        Args:
            file_info: Information about the zip file to process
            output_dir: Output directory for extracted files
            
        Returns:
            Result containing processing results
        """
        pass

    @abstractmethod
    def process_multiple_files(self, file_list: List[Dict[str, Any]], 
                               output_dir: str, max_workers: int = 4) -> Result[Dict[str, Any]]:
        """
        Process multiple RTU files in parallel.
        
        Args:
            file_list: List of files to process
            output_dir: Output directory for extracted files
            max_workers: Maximum number of parallel workers
            
        Returns:
            Result containing processing results
        """
        pass


class IFetchRtuDataController(IPageController):
    """Interface for Fetch RTU Data page controller."""

    @abstractmethod
    def handle_date_mode_change(self, mode: str) -> Result[Dict[str, Any]]:
        """Handle date mode selection (single/range)."""
        pass

    @abstractmethod
    def handle_single_date_selection(self, date_value: Any) -> Result[Dict[str, Any]]:
        """Handle single date selection and validation."""
        pass

    @abstractmethod
    def handle_date_range_selection(self, start_date: Any, end_date: Any) -> Result[Dict[str, Any]]:
        """Handle date range selection and validation."""
        pass

    @abstractmethod
    def handle_line_selection(self, selected_lines: List[str]) -> Result[Dict[str, Any]]:
        """Handle pipeline line selection and validation."""
        pass

    @abstractmethod
    def handle_output_directory_selection(self, output_directory: str) -> Result[Dict[str, Any]]:
        """Handle output directory selection and validation."""
        pass

    @abstractmethod
    def handle_server_filter_change(self, filter_pattern: str) -> Result[Dict[str, Any]]:
        """Handle server filter pattern changes."""
        pass

    @abstractmethod
    def handle_fetch_request(self, mode: str, single_date: Any, start_date: Any, end_date: Any,
                             selected_lines: List[str], output_directory: str, 
                             server_filter: str = None, max_parallel_workers: int = 4) -> Result[Dict[str, Any]]:
        """Handle RTU data fetch request execution."""
        pass

    @abstractmethod
    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """Get available pipeline lines for UI."""
        pass

    @abstractmethod
    def validate_fetch_form(self, mode: str, single_date: Any, start_date: Any, end_date: Any,
                            selected_lines: List[str], output_directory: str) -> Result[bool]:
        """Validate fetch form inputs."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for help modal."""
        pass
