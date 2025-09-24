"""
Domain models for RTU processing.
Contains value objects that encapsulate business logic and validation for RTU operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass
from pathlib import Path
from core.interfaces import IValueObject, Result


class RtuFilePath(IValueObject):
    """Value object representing an RTU file path with validation."""

    def __init__(self, file_path: str):
        if not isinstance(file_path, str):
            raise ValueError("RTU file path must be a string")

        self._validate_path(file_path)
        self._value = str(Path(file_path).resolve())

    @property
    def value(self) -> str:
        """Get the file path value."""
        return self._value

    @property
    def path_obj(self) -> Path:
        """Get the Path object."""
        return Path(self._value)

    @property
    def filename(self) -> str:
        """Get the filename without path."""
        return self.path_obj.name

    @property
    def extension(self) -> str:
        """Get the file extension."""
        return self.path_obj.suffix

    def exists(self) -> bool:
        """Check if the file exists."""
        return self.path_obj.exists()

    def _validate_path(self, file_path: str) -> None:
        """Validate RTU file path."""
        if not file_path or not file_path.strip():
            raise ValueError("RTU file path cannot be empty")

        path_obj = Path(file_path)

        # Check if it's a valid RTU file extension
        if path_obj.suffix.lower() not in ['.dt', '.rtu']:
            raise ValueError(
                f"Invalid RTU file extension: {path_obj.suffix}. Expected .dt or .rtu")

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"RtuFilePath('{self._value}')"


class RtuTimeRange(IValueObject):
    """Value object representing a time range for RTU processing."""

    def __init__(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
        self._validate_time_range(start_time, end_time)
        self._start_time = start_time
        self._end_time = end_time

    @property
    def start_time(self) -> Optional[datetime]:
        """Get the start time."""
        return self._start_time

    @property
    def end_time(self) -> Optional[datetime]:
        """Get the end time."""
        return self._end_time

    @property
    def has_start_time(self) -> bool:
        """Check if start time is specified."""
        return self._start_time is not None

    @property
    def has_end_time(self) -> bool:
        """Check if end time is specified."""
        return self._end_time is not None

    @property
    def is_complete_range(self) -> bool:
        """Check if both start and end times are specified."""
        return self.has_start_time and self.has_end_time

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get the duration in seconds if both times are specified."""
        if self.is_complete_range:
            return (self._end_time - self._start_time).total_seconds()
        return None

    def _validate_time_range(self, start_time: Optional[datetime], end_time: Optional[datetime]) -> None:
        """Validate the time range."""
        if start_time is not None and end_time is not None:
            if start_time >= end_time:
                raise ValueError("Start time must be before end time")

    def format_start_time(self, format_str: str = "%d/%m/%y %H:%M:%S") -> str:
        """Format start time as string."""
        return self._start_time.strftime(format_str) if self._start_time else ""

    def format_end_time(self, format_str: str = "%d/%m/%y %H:%M:%S") -> str:
        """Format end time as string."""
        return self._end_time.strftime(format_str) if self._end_time else ""

    def __str__(self) -> str:
        if self.is_complete_range:
            return f"{self.format_start_time()} to {self.format_end_time()}"
        elif self.has_start_time:
            return f"From {self.format_start_time()}"
        elif self.has_end_time:
            return f"Until {self.format_end_time()}"
        else:
            return "Full range"

    def __repr__(self) -> str:
        return f"RtuTimeRange(start_time={self._start_time}, end_time={self._end_time})"


class RtuFileInfo(IValueObject):
    """Value object representing RTU file information."""

    def __init__(self, file_path: str, first_timestamp: datetime, last_timestamp: datetime,
                 total_points: int = 0, tags_count: int = 0):
        self._file_path = RtuFilePath(file_path)
        self._validate_timestamps(first_timestamp, last_timestamp)
        self._validate_counts(total_points, tags_count)

        self._first_timestamp = first_timestamp
        self._last_timestamp = last_timestamp
        self._total_points = total_points
        self._tags_count = tags_count

    @property
    def file_path(self) -> RtuFilePath:
        """Get the file path value object."""
        return self._file_path

    @property
    def first_timestamp(self) -> datetime:
        """Get the first timestamp."""
        return self._first_timestamp

    @property
    def last_timestamp(self) -> datetime:
        """Get the last timestamp."""
        return self._last_timestamp

    @property
    def total_points(self) -> int:
        """Get the total number of data points."""
        return self._total_points

    @property
    def tags_count(self) -> int:
        """Get the number of tags."""
        return self._tags_count

    @property
    def time_range(self) -> RtuTimeRange:
        """Get the time range of the file."""
        return RtuTimeRange(self._first_timestamp, self._last_timestamp)

    @property
    def duration_seconds(self) -> float:
        """Get the duration of the file in seconds."""
        return (self._last_timestamp - self._first_timestamp).total_seconds()

    def _validate_timestamps(self, first_timestamp: datetime, last_timestamp: datetime) -> None:
        """Validate timestamps."""
        if not isinstance(first_timestamp, datetime):
            raise ValueError("First timestamp must be a datetime object")
        if not isinstance(last_timestamp, datetime):
            raise ValueError("Last timestamp must be a datetime object")
        if first_timestamp > last_timestamp:
            raise ValueError(
                "First timestamp must be before or equal to last timestamp")

    def _validate_counts(self, total_points: int, tags_count: int) -> None:
        """Validate count values."""
        if not isinstance(total_points, int) or total_points < 0:
            raise ValueError("Total points must be a non-negative integer")
        if not isinstance(tags_count, int) or tags_count < 0:
            raise ValueError("Tags count must be a non-negative integer")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'file_path': str(self._file_path),
            'filename': self._file_path.filename,
            'first_timestamp': self._first_timestamp,
            'last_timestamp': self._last_timestamp,
            'total_points': self._total_points,
            'tags_count': self._tags_count,
            'duration_seconds': self.duration_seconds
        }

    def __str__(self) -> str:
        return f"RTU File: {self._file_path.filename} ({self._total_points} points, {self._tags_count} tags)"

    def __repr__(self) -> str:
        return (f"RtuFileInfo(file_path='{self._file_path}', "
                f"first_timestamp={self._first_timestamp}, last_timestamp={self._last_timestamp}, "
                f"total_points={self._total_points}, tags_count={self._tags_count})")


@dataclass(frozen=True)
class RtuProcessingOptions:
    """Immutable configuration for RTU processing operations."""

    # File filtering options
    enable_peek_file_filtering: bool = False
    peek_file_pattern: str = "*.dt"

    # Time filtering options
    time_range: Optional[RtuTimeRange] = None

    # Tag filtering options
    tags_file: Optional[str] = None
    selected_tags: Optional[List[str]] = None

    # Sampling options
    enable_sampling: bool = False
    sample_interval: int = 60  # seconds
    sample_mode: str = "actual"  # "actual" or "interpolated"

    # Output options
    output_format: str = "csv"  # "csv" or "rtu"
    output_directory: Optional[str] = None

    # Processing options
    enable_parallel_processing: bool = True
    max_workers: Optional[int] = None

    # Tag renaming options
    tag_mapping_file: Optional[str] = None
    tag_renaming_enabled: bool = False

    def __post_init__(self):
        """Validate options after initialization."""
        if self.sample_interval <= 0:
            raise ValueError("Sample interval must be positive")

        if self.sample_mode not in ["actual", "interpolated"]:
            raise ValueError("Sample mode must be 'actual' or 'interpolated'")

        if self.output_format not in ["csv", "rtu"]:
            raise ValueError("Output format must be 'csv' or 'rtu'")

        if self.max_workers is not None and self.max_workers <= 0:
            raise ValueError("Max workers must be positive")


@dataclass(frozen=True)
class RtuConversionConstants:
    """Constants and system information for RTU processing."""

    # Supported file extensions
    SUPPORTED_INPUT_EXTENSIONS: tuple = ('.dt', '.rtu')
    SUPPORTED_OUTPUT_EXTENSIONS: tuple = ('.csv', '.dt', '.rtu')

    # Default values
    DEFAULT_SAMPLE_INTERVAL: int = 60
    DEFAULT_MAX_WORKERS: int = 4
    DEFAULT_OUTPUT_FORMAT: str = "csv"

    # Time format strings
    TIME_FORMAT_DMY: str = "%d/%m/%y %H:%M:%S"
    TIME_FORMAT_YMD: str = "%Y-%m-%d %H:%M:%S"
    TIME_FORMAT_ISO: str = "%Y-%m-%dT%H:%M:%S"

    # File size limits (in bytes)
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024 * 1024  # 10 GB

    # Processing limits
    MAX_PARALLEL_FILES: int = 10

    @classmethod
    def get_system_info(cls) -> Dict[str, Any]:
        """Get system information for RTU processing."""
        return {
            'supported_input_extensions': cls.SUPPORTED_INPUT_EXTENSIONS,
            'supported_output_extensions': cls.SUPPORTED_OUTPUT_EXTENSIONS,
            'default_sample_interval': cls.DEFAULT_SAMPLE_INTERVAL,
            'default_max_workers': cls.DEFAULT_MAX_WORKERS,
            'max_file_size_mb': cls.MAX_FILE_SIZE_BYTES // (1024 * 1024),
            'max_parallel_files': cls.MAX_PARALLEL_FILES,
            'time_formats': {
                'dmy': cls.TIME_FORMAT_DMY,
                'ymd': cls.TIME_FORMAT_YMD,
                'iso': cls.TIME_FORMAT_ISO
            }
        }


# Fetch RTU Data Domain Models
class RtuDate(IValueObject):
    """Value object representing an RTU fetch date with validation."""

    def __init__(self, rtu_date: date):
        if not isinstance(rtu_date, date):
            raise ValueError("RTU date must be a date object")

        self._validate_date(rtu_date)
        self._value = rtu_date

    @property
    def value(self) -> date:
        """Get the date value."""
        return self._value

    @property
    def folder_name(self) -> str:
        """Get the folder name format for RTU data (YYYYMMDD)."""
        return self._value.strftime('%Y%m%d')

    @property
    def display_format(self) -> str:
        """Get the human-readable format."""
        return self._value.strftime('%B %d, %Y')

    @property
    def iso_format(self) -> str:
        """Get the ISO format string."""
        return self._value.strftime('%Y-%m-%d')

    def _validate_date(self, rtu_date: date) -> None:
        """Validate RTU date."""
        if rtu_date > date.today():
            raise ValueError("RTU date cannot be in the future")

        # RTU dates should be reasonable (not too far in the past)
        min_date = date(2000, 1, 1)
        if rtu_date < min_date:
            raise ValueError(f"RTU date cannot be before {min_date.strftime('%Y-%m-%d')}")

    def __str__(self) -> str:
        return self.iso_format

    def __repr__(self) -> str:
        return f"RtuDate('{self.iso_format}')"


class RtuDateRange(IValueObject):
    """Value object representing a date range for RTU data fetching."""

    def __init__(self, start_date: date, end_date: date = None):
        if end_date is None:
            end_date = date.today()
        
        self._validate_date_range(start_date, end_date)
        self._start_date = RtuDate(start_date)
        self._end_date = RtuDate(end_date)

    @property
    def start_date(self) -> RtuDate:
        """Get the start date."""
        return self._start_date

    @property
    def end_date(self) -> RtuDate:
        """Get the end date."""
        return self._end_date

    @property
    def is_single_date(self) -> bool:
        """Check if this represents a single date range (start to today)."""
        return self._end_date.value == date.today()

    @property
    def day_count(self) -> int:
        """Get the number of days in the range."""
        return (self._end_date.value - self._start_date.value).days + 1

    @property
    def date_list(self) -> List[date]:
        """Get list of all dates in the range."""
        dates = []
        current = self._start_date.value
        while current <= self._end_date.value:
            dates.append(current)
            current = date.fromordinal(current.toordinal() + 1)
        return dates

    def _validate_date_range(self, start_date: date, end_date: date) -> None:
        """Validate the date range."""
        if not isinstance(start_date, date):
            raise ValueError("Start date must be a date object")
        if not isinstance(end_date, date):
            raise ValueError("End date must be a date object")
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date")

    def contains_date(self, check_date: date) -> bool:
        """Check if the range contains the specified date."""
        return self._start_date.value <= check_date <= self._end_date.value

    def __str__(self) -> str:
        if self.is_single_date:
            return f"From {self._start_date.display_format} to Today"
        else:
            return f"{self._start_date.display_format} to {self._end_date.display_format}"

    def __repr__(self) -> str:
        return f"RtuDateRange(start_date={self._start_date.value}, end_date={self._end_date.value})"


class RtuServerFilter(IValueObject):
    """Value object representing a server filter for RTU data."""

    def __init__(self, pattern: str = None):
        self._validate_pattern(pattern)
        self._pattern = pattern.strip() if pattern else None

    @property
    def pattern(self) -> Optional[str]:
        """Get the filter pattern."""
        return self._pattern

    @property
    def is_empty(self) -> bool:
        """Check if filter is empty (no filtering)."""
        return self._pattern is None or self._pattern == ""

    @property
    def is_wildcard(self) -> bool:
        """Check if pattern contains wildcards."""
        return self._pattern and '*' in self._pattern

    def _validate_pattern(self, pattern: str) -> None:
        """Validate server filter pattern."""
        if pattern is not None and not isinstance(pattern, str):
            raise ValueError("Server filter pattern must be a string or None")

        if pattern and len(pattern.strip()) == 0:
            pattern = None  # Treat empty string as None

    def matches(self, server_name: str) -> bool:
        """Check if server name matches the filter pattern."""
        if self.is_empty:
            return True  # No filter means all servers match

        if not server_name:
            return False

        import re
        
        # Convert to lowercase for case-insensitive matching
        server_name_lower = server_name.lower()
        pattern_lower = self._pattern.lower()
        
        # Escape special regex characters except *
        escaped_pattern = re.escape(pattern_lower).replace(r'\*', '.*')
        
        # Add anchors to match the entire string
        regex_pattern = f'^{escaped_pattern}$'
        
        return bool(re.match(regex_pattern, server_name_lower))

    def __str__(self) -> str:
        return self._pattern if self._pattern else "No filter"

    def __repr__(self) -> str:
        return f"RtuServerFilter('{self._pattern}')"


class RtuLineSelection(IValueObject):
    """Value object representing selected pipeline lines for RTU data fetch."""

    def __init__(self, line_ids: List[str]):
        self._validate_line_ids(line_ids)
        self._line_ids = [line_id.strip() for line_id in line_ids]

    @property
    def line_ids(self) -> List[str]:
        """Get the list of line IDs."""
        return self._line_ids.copy()

    @property
    def count(self) -> int:
        """Get the number of selected lines."""
        return len(self._line_ids)

    @property
    def is_empty(self) -> bool:
        """Check if no lines are selected."""
        return self.count == 0

    def _validate_line_ids(self, line_ids: List[str]) -> None:
        """Validate line IDs."""
        if not isinstance(line_ids, list):
            raise ValueError("Line IDs must be a list")

        if len(line_ids) == 0:
            raise ValueError("At least one line must be selected")

        for line_id in line_ids:
            if not isinstance(line_id, str):
                raise ValueError("All line IDs must be strings")
            if not line_id.strip():
                raise ValueError("Line IDs cannot be empty")

    def contains_line(self, line_id: str) -> bool:
        """Check if the selection contains the specified line."""
        return line_id in self._line_ids

    def __str__(self) -> str:
        if self.count == 1:
            return f"1 line: {self._line_ids[0]}"
        else:
            return f"{self.count} lines: {', '.join(self._line_ids[:3])}" + ("..." if self.count > 3 else "")

    def __repr__(self) -> str:
        return f"RtuLineSelection({self._line_ids})"


class RtuOutputDirectory(IValueObject):
    """Value object representing output directory for RTU data with validation."""

    def __init__(self, directory_path: str):
        self._validate_directory(directory_path)
        self._path = Path(directory_path).resolve()

    @property
    def path(self) -> Path:
        """Get the directory path."""
        return self._path

    @property
    def path_str(self) -> str:
        """Get the directory path as string."""
        return str(self._path)

    @property
    def exists(self) -> bool:
        """Check if directory exists."""
        return self._path.exists() and self._path.is_dir()

    @property
    def is_writable(self) -> bool:
        """Check if directory is writable."""
        try:
            # Try to create the directory if it doesn't exist
            if not self.exists:
                self._path.mkdir(parents=True, exist_ok=True)
            
            # Test write access by creating a temporary file
            test_file = self._path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False

    def _validate_directory(self, directory_path: str) -> None:
        """Validate directory path."""
        if not isinstance(directory_path, str):
            raise ValueError("Directory path must be a string")

        if not directory_path.strip():
            raise ValueError("Directory path cannot be empty")

        # Check for invalid characters (basic validation, excluding drive letters)
        invalid_chars = ['<', '>', '"', '|', '?', '*']
        # Allow colon only as part of drive letter (e.g., C:)
        path_without_drive = directory_path[2:] if len(directory_path) > 2 and directory_path[1] == ':' else directory_path
        if any(char in path_without_drive for char in invalid_chars):
            raise ValueError(f"Directory path contains invalid characters: {directory_path}")

    def create_line_subdirectory(self, line_id: str) -> 'RtuOutputDirectory':
        """Create a subdirectory for a specific line."""
        line_path = self._path / line_id
        return RtuOutputDirectory(str(line_path))

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return f"RtuOutputDirectory('{self._path}')"


class RtuFetchResult(IValueObject):
    """Value object representing the result of an RTU data fetch operation."""

    def __init__(self, success: bool, message: str, 
                 lines_processed: int = 0, 
                 total_files_extracted: int = 0,
                 extraction_errors: List[str] = None,
                 missing_dates: List[str] = None):
        self._success = success
        self._message = message
        self._lines_processed = max(0, lines_processed)
        self._total_files_extracted = max(0, total_files_extracted)
        self._extraction_errors = extraction_errors or []
        self._missing_dates = missing_dates or []

    @property
    def success(self) -> bool:
        """Check if the fetch operation was successful."""
        return self._success

    @property
    def message(self) -> str:
        """Get the result message."""
        return self._message

    @property
    def lines_processed(self) -> int:
        """Get the number of lines processed."""
        return self._lines_processed

    @property
    def total_files_extracted(self) -> int:
        """Get the total number of files extracted."""
        return self._total_files_extracted

    @property
    def extraction_errors(self) -> List[str]:
        """Get the list of extraction errors."""
        return self._extraction_errors.copy()

    @property
    def missing_dates(self) -> List[str]:
        """Get the list of missing dates."""
        return self._missing_dates.copy()

    @property
    def has_errors(self) -> bool:
        """Check if there were any extraction errors."""
        return len(self._extraction_errors) > 0

    @property
    def has_missing_dates(self) -> bool:
        """Check if there were any missing dates."""
        return len(self._missing_dates) > 0

    @property
    def summary_text(self) -> str:
        """Get a summary text for the result."""
        if self._success:
            text = f"Success! {self._total_files_extracted} files extracted for {self._lines_processed} lines"
            if self.has_errors:
                text += f" (with {len(self._extraction_errors)} errors)"
            return text
        else:
            return f"Failed: {self._message}"

    @classmethod
    def create_success(cls, lines_processed: int, total_files_extracted: int, 
                       extraction_errors: List[str] = None, missing_dates: List[str] = None) -> 'RtuFetchResult':
        """Create a successful result."""
        message = f"RTU data extraction completed successfully"
        return cls(True, message, lines_processed, total_files_extracted, extraction_errors, missing_dates)

    @classmethod
    def create_failure(cls, message: str) -> 'RtuFetchResult':
        """Create a failed result."""
        return cls(False, message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'success': self._success,
            'message': self._message,
            'summary': {
                'lines_processed': self._lines_processed,
                'total_files_extracted': self._total_files_extracted
            },
            'extraction_errors': self._extraction_errors,
            'missing_dates': self._missing_dates
        }

    def __str__(self) -> str:
        return self.summary_text

    def __repr__(self) -> str:
        return f"RtuFetchResult(success={self._success}, lines_processed={self._lines_processed}, total_files_extracted={self._total_files_extracted})"


@dataclass(frozen=True)
class RtuFetchConstants:
    """Constants for RTU data fetching operations."""

    # File patterns
    ZIP_FILE_PATTERN: str = r'^(.+)_(\d{8})_(\d{4})_(.+)\.zip$'
    DT_FILE_EXTENSION: str = '.dt'
    
    # Default values
    DEFAULT_MAX_PARALLEL_WORKERS: int = 4
    MAX_PARALLEL_WORKERS: int = 8
    MIN_PARALLEL_WORKERS: int = 1
    
    # Timeouts
    DEFAULT_TIMEOUT_SECONDS: int = 300
    MAX_TIMEOUT_SECONDS: int = 3600
    
    # Directory names
    DEFAULT_OUTPUT_SUBDIR: str = "rtu_data"
    
    @classmethod
    def get_system_info(cls) -> Dict[str, Any]:
        """Get system information for RTU fetch operations."""
        return {
            'zip_file_pattern': cls.ZIP_FILE_PATTERN,
            'dt_file_extension': cls.DT_FILE_EXTENSION,
            'default_max_parallel_workers': cls.DEFAULT_MAX_PARALLEL_WORKERS,
            'max_parallel_workers': cls.MAX_PARALLEL_WORKERS,
            'default_timeout_seconds': cls.DEFAULT_TIMEOUT_SECONDS,
            'max_timeout_seconds': cls.MAX_TIMEOUT_SECONDS
        }
