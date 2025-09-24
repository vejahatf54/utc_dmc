"""
Domain models for Review processing.
Contains value objects that encapsulate business logic and validation for Review operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass
from pathlib import Path
from core.interfaces import IValueObject, Result
import re


class ReviewFilePath(IValueObject):
    """Value object representing a Review file path with validation."""

    def __init__(self, file_path: str):
        if not isinstance(file_path, str):
            raise ValueError("Review file path must be a string")

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

    @property
    def csv_filename(self) -> str:
        """Get the corresponding CSV filename."""
        return f"{self.path_obj.stem}.csv"

    def exists(self) -> bool:
        """Check if the file exists."""
        return self.path_obj.exists()

    def _validate_path(self, file_path: str) -> None:
        """Validate Review file path."""
        if not file_path or not file_path.strip():
            raise ValueError("Review file path cannot be empty")

        path_obj = Path(file_path)
        if path_obj.suffix.lower() != '.review':
            raise ValueError("File must have .review extension")


class ReviewDirectoryPath(IValueObject):
    """Value object representing a Review directory path with validation."""

    def __init__(self, directory_path: str):
        if not isinstance(directory_path, str):
            raise ValueError("Review directory path must be a string")

        self._validate_directory(directory_path)
        self._value = str(Path(directory_path).resolve())

    @property
    def value(self) -> str:
        """Get the directory path value."""
        return self._value

    @property
    def path_obj(self) -> Path:
        """Get the Path object."""
        return Path(self._value)

    def exists(self) -> bool:
        """Check if the directory exists."""
        return self.path_obj.exists() and self.path_obj.is_dir()

    def get_review_files(self) -> List[ReviewFilePath]:
        """Get all Review files in the directory."""
        if not self.exists():
            return []

        review_files = []
        for file_path in self.path_obj.glob("*.review"):
            try:
                review_files.append(ReviewFilePath(str(file_path)))
            except ValueError:
                # Skip invalid files
                continue

        return review_files

    def _validate_directory(self, directory_path: str) -> None:
        """Validate Review directory path."""
        if not directory_path or not directory_path.strip():
            raise ValueError("Review directory path cannot be empty")


class ReviewTimeRange(IValueObject):
    """Value object representing a time range for Review processing."""

    def __init__(self, start_time: str, end_time: str):
        self._validate_and_parse_times(start_time, end_time)
        self._start_time = start_time
        self._end_time = end_time

    @property
    def start_time(self) -> str:
        """Get the start time."""
        return self._start_time

    @property
    def end_time(self) -> str:
        """Get the end time."""
        return self._end_time

    @property
    def start_datetime(self) -> datetime:
        """Get start time as datetime object."""
        return self._parse_time_string(self._start_time)

    @property
    def end_datetime(self) -> datetime:
        """Get end time as datetime object."""
        return self._parse_time_string(self._end_time)

    def format_for_dreview(self) -> tuple[str, str]:
        """Format times for dreview.exe command (yy/MM/dd_HH:mm:ss)."""
        start_dt = self.start_datetime
        end_dt = self.end_datetime

        start_formatted = start_dt.strftime('%y/%m/%d_%H:%M:%S')
        end_formatted = end_dt.strftime('%y/%m/%d_%H:%M:%S')

        return start_formatted, end_formatted

    def is_valid_range(self) -> bool:
        """Check if the time range is valid (start < end)."""
        return self.start_datetime < self.end_datetime

    def _validate_and_parse_times(self, start_time: str, end_time: str) -> None:
        """Validate and parse time strings."""
        if not start_time or not end_time:
            raise ValueError("Start time and end time are required")

        start_dt = self._parse_time_string(start_time)
        end_dt = self._parse_time_string(end_time)

        if start_dt >= end_dt:
            raise ValueError("Start time must be before end time")

    def _parse_time_string(self, time_str: str) -> datetime:
        """Parse time string to datetime object."""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
            '%y/%m/%d_%H:%M:%S'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Could not parse datetime: {time_str}")


class ReviewPeekFile(IValueObject):
    """Value object representing peek file content for Review filtering."""

    def __init__(self, peek_items: List[str]):
        if peek_items is None:
            peek_items = []

        self._validate_peek_items(peek_items)
        self._peek_items = [item.strip()
                            for item in peek_items if item.strip()]

    @property
    def peek_items(self) -> List[str]:
        """Get the peek items list."""
        return self._peek_items.copy()

    @property
    def has_items(self) -> bool:
        """Check if peek file has items."""
        return len(self._peek_items) > 0

    @property
    def items_count(self) -> int:
        """Get the number of peek items."""
        return len(self._peek_items)

    def format_for_dreview(self) -> str:
        """Format peek items for dreview.exe command."""
        if not self._peek_items:
            return ""
        return ",".join(self._peek_items)

    @classmethod
    def from_file_content(cls, file_content: str) -> 'ReviewPeekFile':
        """Create from peek file content."""
        lines = [line.strip() for line in file_content.splitlines()
                 if line.strip() and not line.strip().startswith("#")]
        return cls(lines)

    @classmethod
    def from_uploaded_file(cls, file_dict: Dict[str, Any]) -> 'ReviewPeekFile':
        """Create from uploaded file dictionary."""
        if 'tags' in file_dict:
            return cls(file_dict['tags'])
        elif 'content' in file_dict:
            import base64
            content = base64.b64decode(file_dict['content']).decode('utf-8')
            return cls.from_file_content(content)
        else:
            return cls([])

    def _validate_peek_items(self, peek_items: List[str]) -> None:
        """Validate peek items."""
        if not isinstance(peek_items, list):
            raise ValueError("Peek items must be a list")

        for item in peek_items:
            if not isinstance(item, str):
                raise ValueError("All peek items must be strings")


class ReviewProcessingOptions(IValueObject):
    """Value object representing processing options for Review conversion."""

    def __init__(self,
                 time_range: ReviewTimeRange,
                 peek_file: ReviewPeekFile,
                 dump_all: bool = False,
                 frequency_minutes: Optional[float] = None,
                 merged_filename: str = "MergedReviewData.csv",
                 parallel_processing: bool = True):

        self._validate_options(time_range, peek_file,
                               dump_all, frequency_minutes)

        self._time_range = time_range
        self._peek_file = peek_file
        self._dump_all = dump_all
        self._frequency_minutes = frequency_minutes
        self._merged_filename = merged_filename
        self._parallel_processing = parallel_processing

    @property
    def time_range(self) -> ReviewTimeRange:
        """Get the time range."""
        return self._time_range

    @property
    def peek_file(self) -> ReviewPeekFile:
        """Get the peek file."""
        return self._peek_file

    @property
    def dump_all(self) -> bool:
        """Get dump all flag."""
        return self._dump_all

    @property
    def frequency_minutes(self) -> Optional[float]:
        """Get frequency in minutes."""
        return self._frequency_minutes

    @property
    def merged_filename(self) -> str:
        """Get merged filename."""
        return self._merged_filename

    @property
    def parallel_processing(self) -> bool:
        """Get parallel processing flag."""
        return self._parallel_processing

    def get_dreview_duration_arg(self) -> str:
        """Get duration argument for dreview.exe."""
        if self._dump_all:
            return ""
        elif self._frequency_minutes is not None:
            return f"-DT={self._frequency_minutes}"
        else:
            return ""

    def _validate_options(self, time_range: ReviewTimeRange, peek_file: ReviewPeekFile,
                          dump_all: bool, frequency_minutes: Optional[float]) -> None:
        """Validate processing options."""
        if not isinstance(time_range, ReviewTimeRange):
            raise ValueError("Time range must be a ReviewTimeRange instance")

        if not isinstance(peek_file, ReviewPeekFile):
            raise ValueError("Peek file must be a ReviewPeekFile instance")

        if not isinstance(dump_all, bool):
            raise ValueError("Dump all must be a boolean")

        if not dump_all and frequency_minutes is not None:
            if not isinstance(frequency_minutes, (int, float)) or frequency_minutes <= 0:
                raise ValueError("Frequency minutes must be a positive number")


@dataclass(frozen=True)
class ReviewFileInfo:
    """Information about a Review file."""
    file_path: str
    filename: str
    file_size_bytes: int
    last_modified: datetime
    exists: bool
    is_valid: bool = True
    error_message: str = ""

    @classmethod
    def from_file_path(cls, file_path: str) -> 'ReviewFileInfo':
        """Create ReviewFileInfo from file path."""
        try:
            review_path = ReviewFilePath(file_path)
            path_obj = review_path.path_obj

            if path_obj.exists():
                stat = path_obj.stat()
                return cls(
                    file_path=file_path,
                    filename=path_obj.name,
                    file_size_bytes=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                    exists=True,
                    is_valid=True
                )
            else:
                return cls(
                    file_path=file_path,
                    filename=Path(file_path).name,
                    file_size_bytes=0,
                    last_modified=datetime.min,
                    exists=False,
                    is_valid=False,
                    error_message="File does not exist"
                )
        except Exception as e:
            return cls(
                file_path=file_path,
                filename=Path(file_path).name,
                file_size_bytes=0,
                last_modified=datetime.min,
                exists=False,
                is_valid=False,
                error_message=str(e)
            )


@dataclass(frozen=True)
class ReviewConversionResult:
    """Result of Review conversion operation."""
    success: bool
    output_directory: str
    processed_files_count: int
    merged_file_path: str = ""
    processing_time_seconds: float = 0.0
    error_message: str = ""
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            object.__setattr__(self, 'warnings', [])


class ReviewConversionConstants:
    """Constants for Review conversion operations."""

    # File extensions
    REVIEW_EXTENSION = ".review"
    CSV_EXTENSION = ".csv"

    # Default values
    DEFAULT_MERGED_FILENAME = "MergedReviewData.csv"
    DEFAULT_FREQUENCY_MINUTES = 60.0

    # dreview.exe command components
    DREVIEW_EXECUTABLE = "dreview.exe"
    MATCH_ARG_PREFIX = "-match="
    TIME_BEGIN_PREFIX = "-TBEGIN="
    TIME_END_PREFIX = "-TEND="
    DURATION_PREFIX = "-DT="

    # Validation patterns
    TIME_FORMAT_PATTERNS = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d',
        '%y/%m/%d_%H:%M:%S'
    ]

    # System information
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get system information for Review processing."""
        return {
            "component": "Review to CSV Converter",
            "version": "2.0.0",
            "architecture": "Clean Architecture with SOLID Principles",
            "supported_formats": [ReviewConversionConstants.REVIEW_EXTENSION],
            "output_format": ReviewConversionConstants.CSV_EXTENSION,
            "dependencies": ["dreview.exe", "pandas"],
            "features": [
                "Parallel processing",
                "Time range filtering",
                "Peek file filtering",
                "Automatic CSV merging",
                "Background processing",
                "Detailed logging"
            ]
        }
