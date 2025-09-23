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
