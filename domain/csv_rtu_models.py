"""
Domain models for CSV to RTU conversion.
Contains value objects and business entities following Domain-Driven Design principles.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from core.interfaces import IValueObject


class CsvFileMetadata(IValueObject):
    """Value object representing CSV file metadata."""

    def __init__(self, filename: str, size: int, rows: int, columns: int, first_column: str):
        if not filename or not filename.strip():
            raise ValueError("Filename cannot be empty")
        if size < 0:
            raise ValueError("File size cannot be negative")
        if rows < 0:
            raise ValueError("Row count cannot be negative")
        if columns < 0:
            raise ValueError("Column count cannot be negative")
        if not first_column or not first_column.strip():
            raise ValueError("First column name cannot be empty")

        self._filename = filename.strip()
        self._size = size
        self._rows = rows
        self._columns = columns
        self._first_column = first_column.strip()

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def size(self) -> int:
        return self._size

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def columns(self) -> int:
        return self._columns

    @property
    def first_column(self) -> str:
        return self._first_column

    @property
    def tag_count(self) -> int:
        """Number of tag columns (excluding timestamp column)."""
        return max(0, self._columns - 1)

    @property
    def total_points(self) -> int:
        """Total data points to be converted."""
        return self.tag_count * self._rows

    @property
    def size_kb(self) -> float:
        """File size in kilobytes."""
        return self._size / 1024.0

    def __str__(self) -> str:
        return f"CsvFileMetadata(filename='{self._filename}', rows={self._rows}, columns={self._columns})"

    def __repr__(self) -> str:
        return self.__str__()


class RtuTimestamp(IValueObject):
    """Value object representing a validated RTU timestamp."""

    def __init__(self, timestamp: datetime):
        if timestamp is None:
            raise ValueError("Timestamp cannot be None")
        if not isinstance(timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")

        self._timestamp = timestamp

    @property
    def value(self) -> datetime:
        return self._timestamp

    @property
    def iso_format(self) -> str:
        """Get timestamp in ISO format."""
        return self._timestamp.isoformat()

    @classmethod
    def from_string(cls, timestamp_str: str) -> 'RtuTimestamp':
        """Create RtuTimestamp from string with common format parsing."""
        if not timestamp_str or not timestamp_str.strip():
            raise ValueError("Timestamp string cannot be empty")

        timestamp_str = timestamp_str.strip()

        try:
            # Try ISO format with T
            if "T" in timestamp_str:
                # Handle Zulu suffix
                if timestamp_str.endswith("Z"):
                    timestamp_str = timestamp_str[:-1] + "+00:00"
                timestamp = datetime.fromisoformat(timestamp_str)
            else:
                # Try multiple common formats
                formats_to_try = [
                    "%Y-%m-%d %H:%M:%S",    # Standard format: 2021-09-01 00:00:00
                    "%m/%d/%Y %H:%M:%S",    # PI export format: 9/1/2021 0:00:00
                    "%m-%d-%Y %H:%M:%S",    # Alternative format: 9-1-2021 0:00:00
                    "%Y/%m/%d %H:%M:%S",    # Alternative format: 2021/09/01 0:00:00
                    "%d/%m/%Y %H:%M:%S",    # European format: 1/9/2021 0:00:00
                    "%Y-%m-%d %H:%M",       # Without seconds: 2021-09-01 00:00
                    "%m/%d/%Y %H:%M",       # PI format without seconds: 9/1/2021 0:00
                ]

                timestamp = None
                for fmt in formats_to_try:
                    try:
                        timestamp = datetime.strptime(timestamp_str, fmt)
                        break
                    except ValueError:
                        continue

                if timestamp is None:
                    raise ValueError(
                        f"Could not parse timestamp with any supported format")

            return cls(timestamp)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid timestamp format: {timestamp_str}. Supported formats include: MM/DD/YYYY HH:MM:SS, YYYY-MM-DD HH:MM:SS") from e

    @classmethod
    def now(cls) -> 'RtuTimestamp':
        """Create RtuTimestamp for current time."""
        return cls(datetime.now())

    def __str__(self) -> str:
        return f"RtuTimestamp({self._timestamp})"

    def __repr__(self) -> str:
        return self.__str__()


class RtuDataPoint(IValueObject):
    """Value object representing a single RTU data point."""

    def __init__(self, timestamp: RtuTimestamp, tag_name: str, value: float, quality: int):
        if timestamp is None:
            raise ValueError("Timestamp cannot be None")
        if not isinstance(timestamp, RtuTimestamp):
            raise ValueError("Timestamp must be RtuTimestamp instance")
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")
        if not isinstance(value, (int, float)):
            raise ValueError("Value must be numeric")
        if quality not in [0, 1]:
            raise ValueError("Quality must be 0 (bad) or 1 (good)")

        self._timestamp = timestamp
        self._tag_name = tag_name.strip()
        self._value = float(value)
        self._quality = quality

    @property
    def timestamp(self) -> RtuTimestamp:
        return self._timestamp

    @property
    def tag_name(self) -> str:
        return self._tag_name

    @property
    def value(self) -> float:
        return self._value

    @property
    def quality(self) -> int:
        return self._quality

    @property
    def is_good_quality(self) -> bool:
        """Check if data point has good quality."""
        return self._quality == 1

    @classmethod
    def from_csv_data(cls, timestamp_str: str, tag_name: str, value_str: str) -> 'RtuDataPoint':
        """Create RtuDataPoint from CSV data with validation and quality assessment."""
        timestamp = RtuTimestamp.from_string(timestamp_str)

        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")

        tag_name = tag_name.strip()

        # Parse value and determine quality
        try:
            if value_str is None:
                value, quality = 0.0, 0
            else:
                value_str = str(value_str).strip()
                if value_str and value_str.lower() not in {"nan", "null", "none", ""}:
                    value, quality = float(value_str), 1
                else:
                    value, quality = 0.0, 0
        except (ValueError, TypeError):
            value, quality = 0.0, 0

        return cls(timestamp, tag_name, value, quality)

    def __str__(self) -> str:
        return f"RtuDataPoint(tag='{self._tag_name}', value={self._value}, quality={self._quality})"

    def __repr__(self) -> str:
        return self.__str__()


class ConversionRequest(IValueObject):
    """Value object representing a CSV to RTU conversion request."""

    def __init__(self, csv_file_path: str, output_directory: str, metadata: CsvFileMetadata):
        if not csv_file_path or not csv_file_path.strip():
            raise ValueError("CSV file path cannot be empty")
        if not output_directory or not output_directory.strip():
            raise ValueError("Output directory cannot be empty")
        if metadata is None:
            raise ValueError("Metadata cannot be None")
        if not isinstance(metadata, CsvFileMetadata):
            raise ValueError("Metadata must be CsvFileMetadata instance")

        self._csv_file_path = csv_file_path.strip()
        self._output_directory = output_directory.strip()
        self._metadata = metadata

    @property
    def csv_file_path(self) -> str:
        return self._csv_file_path

    @property
    def output_directory(self) -> str:
        return self._output_directory

    @property
    def metadata(self) -> CsvFileMetadata:
        return self._metadata

    @property
    def expected_rtu_filename(self) -> str:
        """Expected RTU output filename."""
        import os
        base_name = os.path.basename(self._csv_file_path)
        return base_name.replace(".csv", ".dt")

    @property
    def expected_rtu_path(self) -> str:
        """Expected full RTU output path."""
        import os
        return os.path.join(self._output_directory, self.expected_rtu_filename).replace('\\', '/')

    def __str__(self) -> str:
        return f"ConversionRequest(csv='{self._csv_file_path}', output='{self._output_directory}')"

    def __repr__(self) -> str:
        return self.__str__()


class ConversionResult(IValueObject):
    """Value object representing the result of a CSV to RTU conversion."""

    def __init__(self, request: ConversionRequest, success: bool,
                 records_processed: int = 0, tags_written: int = 0,
                 error_message: str = None, rtu_file_path: str = None):
        if request is None:
            raise ValueError("Request cannot be None")
        if not isinstance(request, ConversionRequest):
            raise ValueError("Request must be ConversionRequest instance")
        if records_processed < 0:
            raise ValueError("Records processed cannot be negative")
        if tags_written < 0:
            raise ValueError("Tags written cannot be negative")

        self._request = request
        self._success = success
        self._records_processed = records_processed
        self._tags_written = tags_written
        self._error_message = error_message
        self._rtu_file_path = rtu_file_path

    @property
    def request(self) -> ConversionRequest:
        return self._request

    @property
    def success(self) -> bool:
        return self._success

    @property
    def records_processed(self) -> int:
        return self._records_processed

    @property
    def tags_written(self) -> int:
        return self._tags_written

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def rtu_file_path(self) -> str:
        return self._rtu_file_path

    @property
    def filename(self) -> str:
        """Get the filename from the request."""
        return self._request.metadata.filename

    @property
    def output_filename(self) -> str:
        """Get the RTU output filename."""
        import os
        if self._rtu_file_path:
            return os.path.basename(self._rtu_file_path)
        return self._request.expected_rtu_filename

    @classmethod
    def create_success(cls, request: ConversionRequest, records_processed: int,
                       tags_written: int, rtu_file_path: str) -> 'ConversionResult':
        """Create a successful conversion result."""
        return cls(request, True, records_processed, tags_written,
                   None, rtu_file_path)

    @classmethod
    def create_failure(cls, request: ConversionRequest, error_message: str) -> 'ConversionResult':
        """Create a failed conversion result."""
        return cls(request, False, 0, 0, error_message, None)

    def __str__(self) -> str:
        status = "Success" if self._success else "Failed"
        return f"ConversionResult({status}, {self._records_processed} records, {self._tags_written} tags)"

    def __repr__(self) -> str:
        return self.__str__()


class ConversionConstants:
    """Constants used in CSV to RTU conversion."""

    # Supported file extensions
    SUPPORTED_CSV_EXTENSIONS = ['.csv']
    RTU_EXTENSION = '.dt'

    # Quality values
    QUALITY_GOOD = 1
    QUALITY_BAD = 0

    # Default values
    DEFAULT_OUTPUT_DIR = 'RTU_Output'

    # Validation limits
    MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB
    MIN_COLUMNS = 2  # At least timestamp + 1 tag
    MAX_COLUMNS = 1000  # Reasonable limit

    # Error messages
    SPS_API_NOT_AVAILABLE = "sps_api is not available. Please install it to use RTU conversion."
    EMPTY_CSV_FILE = "CSV file is empty"
    INVALID_CSV_FORMAT = "Invalid CSV format"
    OUTPUT_DIR_ERROR = "Could not create output directory"
