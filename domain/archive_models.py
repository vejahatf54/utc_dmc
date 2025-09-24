"""
Domain models for Archive processing.
Contains value objects that encapsulate business logic and validation for Archive operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass
from pathlib import Path
from core.interfaces import IValueObject, Result


class ArchiveDate(IValueObject):
    """Value object representing an archive date with validation."""

    def __init__(self, archive_date: datetime):
        if not isinstance(archive_date, (datetime, date)):
            raise ValueError("Archive date must be a datetime or date object")

        self._validate_date(archive_date)
        
        # Convert date to datetime if needed
        if isinstance(archive_date, date):
            self._value = datetime.combine(archive_date, datetime.min.time())
        else:
            self._value = archive_date

    @property
    def value(self) -> datetime:
        """Get the archive date value."""
        return self._value

    @property
    def date_obj(self) -> date:
        """Get the date object."""
        return self._value.date()

    @property
    def folder_name(self) -> str:
        """Get the folder name format for archives (YYYYMMDD)."""
        return self._value.strftime('%Y%m%d')

    @property
    def display_format(self) -> str:
        """Get the human-readable format."""
        return self._value.strftime('%B %d, %Y')

    @property
    def iso_format(self) -> str:
        """Get the ISO format string."""
        return self._value.strftime('%Y-%m-%d')

    def _validate_date(self, archive_date: datetime) -> None:
        """Validate archive date."""
        # Convert to datetime for comparison if needed
        now = datetime.now()
        if isinstance(archive_date, date) and not isinstance(archive_date, datetime):
            # For date objects, compare just the date part
            if archive_date > now.date():
                raise ValueError("Archive date cannot be in the future")
        else:
            # For datetime objects, compare the full datetime
            if archive_date > now:
                raise ValueError("Archive date cannot be in the future")

        # Archive dates should be reasonable (not too far in the past)
        min_date = datetime(2000, 1, 1)
        if isinstance(archive_date, date) and not isinstance(archive_date, datetime):
            # For date objects, compare against the date part
            if archive_date < min_date.date():
                raise ValueError("Archive date cannot be before 2000-01-01")
        else:
            # For datetime objects, compare the full datetime
            if archive_date < min_date:
                raise ValueError(f"Archive date cannot be before {min_date.strftime('%Y-%m-%d')}")

    def __str__(self) -> str:
        return self.iso_format

    def __repr__(self) -> str:
        return f"ArchiveDate('{self.iso_format}')"


class PipelineLine(IValueObject):
    """Value object representing a pipeline line identifier."""

    def __init__(self, line_id: str):
        if not isinstance(line_id, str):
            raise ValueError("Pipeline line ID must be a string")

        self._validate_line_id(line_id)
        self._value = line_id.strip()

    @property
    def value(self) -> str:
        """Get the line ID value."""
        return self._value

    @property
    def display_label(self) -> str:
        """Get the display label for UI."""
        return self._value

    def _validate_line_id(self, line_id: str) -> None:
        """Validate pipeline line ID."""
        if not line_id or not line_id.strip():
            raise ValueError("Pipeline line ID cannot be empty")

        cleaned_id = line_id.strip()
        if not cleaned_id:
            raise ValueError("Pipeline line ID cannot be whitespace only")

        # Basic validation - can be extended as needed
        if len(cleaned_id) > 50:
            raise ValueError("Pipeline line ID cannot exceed 50 characters")

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"PipelineLine('{self._value}')"


class ArchivePath(IValueObject):
    """Value object representing an archive UNC path with validation."""

    def __init__(self, archive_path: str):
        if not isinstance(archive_path, str):
            raise ValueError("Archive path must be a string")

        self._validate_path(archive_path)
        self._value = archive_path.strip()

    @property
    def value(self) -> str:
        """Get the archive path value."""
        return self._value

    @property
    def path_obj(self) -> Path:
        """Get the Path object."""
        return Path(self._value)

    def exists(self) -> bool:
        """Check if the archive path exists and is accessible."""
        try:
            return self.path_obj.exists() and self.path_obj.is_dir()
        except Exception:
            return False

    def get_line_path(self, line_id: str) -> Path:
        """Get the path for a specific pipeline line."""
        return Path(self._value) / line_id

    def get_date_path(self, line_id: str, archive_date: ArchiveDate) -> Path:
        """Get the path for a specific line and date."""
        return self.get_line_path(line_id) / archive_date.folder_name

    def _validate_path(self, archive_path: str) -> None:
        """Validate archive path."""
        if not archive_path or not archive_path.strip():
            raise ValueError("Archive path cannot be empty")

        # Basic path validation
        try:
            Path(archive_path)
        except Exception as e:
            raise ValueError(f"Invalid archive path format: {str(e)}")

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"ArchivePath('{self._value}')"


class OutputDirectory(IValueObject):
    """Value object representing an output directory path with validation."""

    def __init__(self, directory_path: str):
        if not isinstance(directory_path, str):
            raise ValueError("Output directory path must be a string")

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
        return self.path_obj.exists()

    def create_if_not_exists(self) -> None:
        """Create the directory if it doesn't exist."""
        self.path_obj.mkdir(parents=True, exist_ok=True)

    def get_line_output_path(self, line_id: str, archive_date: ArchiveDate) -> Path:
        """Get the output path for a specific line and date."""
        return self.path_obj / f"{line_id}_{archive_date.folder_name}"

    def _validate_directory(self, directory_path: str) -> None:
        """Validate output directory path."""
        if not directory_path or not directory_path.strip():
            raise ValueError("Output directory path cannot be empty")

        # Check if path is valid
        try:
            path_obj = Path(directory_path)
            # Try to create parent directories to test permissions
            path_obj.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise ValueError(f"Permission denied accessing directory: {directory_path}")
        except Exception as e:
            raise ValueError(f"Invalid directory path: {str(e)}")

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"OutputDirectory('{self._value}')"


@dataclass(frozen=True)
class ArchiveFileInfo:
    """Immutable data structure representing archive file information."""
    original_zip: str
    original_filename: str
    extracted_file: str
    filename: str
    size_bytes: int


@dataclass(frozen=True)
class FetchArchiveRequest:
    """Immutable data structure representing a fetch archive request."""
    archive_date: ArchiveDate
    pipeline_lines: List[PipelineLine]
    output_directory: OutputDirectory
    
    def __post_init__(self):
        """Validate the request after initialization."""
        if not self.pipeline_lines:
            raise ValueError("At least one pipeline line must be specified")
        
        if len(self.pipeline_lines) == 0:
            raise ValueError("Pipeline lines list cannot be empty")


@dataclass(frozen=True)
class FetchArchiveResult:
    """Immutable data structure representing fetch archive operation results."""
    success: bool
    files: List[ArchiveFileInfo]
    failed_lines: List[Dict[str, str]]
    message: str
    output_directory: str
    fetch_date: str
    requested_lines: List[str]
    
    @property
    def files_count(self) -> int:
        """Get the number of successfully processed files."""
        return len(self.files)
    
    @property
    def failed_count(self) -> int:
        """Get the number of failed lines."""
        return len(self.failed_lines)
    
    @property
    def processed_lines_count(self) -> int:
        """Get the number of successfully processed lines."""
        return len(self.requested_lines) - self.failed_count


class ArchiveConversionConstants:
    """Constants and system information for archive operations."""
    
    # File extensions
    ARCHIVE_EXTENSIONS = ['.zip']
    
    # Date formats
    FOLDER_DATE_FORMAT = '%Y%m%d'
    DISPLAY_DATE_FORMAT = '%B %d, %Y'
    ISO_DATE_FORMAT = '%Y-%m-%d'
    
    # Archive configuration
    DEFAULT_TIMEOUT = 30
    MAX_FILENAME_LENGTH = 255
    
    @classmethod
    def get_system_info(cls) -> Dict[str, Any]:
        """Get system information for archive operations."""
        return {
            'supported_archive_formats': cls.ARCHIVE_EXTENSIONS,
            'folder_date_format': cls.FOLDER_DATE_FORMAT,
            'display_date_format': cls.DISPLAY_DATE_FORMAT,
            'iso_date_format': cls.ISO_DATE_FORMAT,
            'default_timeout': cls.DEFAULT_TIMEOUT,
            'max_filename_length': cls.MAX_FILENAME_LENGTH
        }