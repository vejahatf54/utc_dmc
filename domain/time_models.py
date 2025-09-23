"""
Domain models for SPS Time conversion.
Contains value objects that encapsulate business logic and validation.
"""

from datetime import datetime, timezone, timedelta
from typing import Union
from core.interfaces import IValueObject


class SpsTimestamp(IValueObject):
    """Value object representing an SPS Unix timestamp in minutes."""

    def __init__(self, value: Union[str, float, int]):
        """Initialize SPS timestamp with validation."""
        if isinstance(value, str):
            self._validate_string_value(value)
            self._minutes = float(value.strip())
        elif isinstance(value, (int, float)):
            self._validate_numeric_value(value)
            self._minutes = float(value)
        else:
            raise ValueError(
                "SPS timestamp must be a string, float, or integer")

        self._validate_range(self._minutes)

    @property
    def minutes(self) -> float:
        """Get the timestamp value in minutes."""
        return self._minutes

    @property
    def seconds(self) -> float:
        """Get the timestamp value in seconds."""
        return self._minutes * 60

    @property
    def formatted_value(self) -> str:
        """Get the formatted timestamp value as string."""
        return f"{self._minutes:.6f}"

    def _validate_string_value(self, value: str) -> None:
        """Validate string representation of timestamp."""
        if not value or not value.strip():
            raise ValueError("SPS timestamp cannot be empty")

        try:
            float(value.strip())
        except ValueError:
            raise ValueError("SPS timestamp must be a valid numeric value")

    def _validate_numeric_value(self, value: Union[int, float]) -> None:
        """Validate numeric timestamp value."""
        if not isinstance(value, (int, float)):
            raise ValueError("SPS timestamp must be numeric")

    def _validate_range(self, minutes: float) -> None:
        """Validate timestamp is within reasonable range."""
        # Allow negative values for historical dates before SPS epoch
        # But set reasonable bounds to prevent overflow issues
        min_minutes = -100_000_000  # About 190 years before epoch
        max_minutes = 100_000_000   # About 190 years after epoch

        if minutes < min_minutes or minutes > max_minutes:
            raise ValueError(
                f"SPS timestamp out of reasonable range: {minutes}")

    def __str__(self) -> str:
        return self.formatted_value

    def __repr__(self) -> str:
        return f"SpsTimestamp({self._minutes})"


class StandardDateTime(IValueObject):
    """Value object representing a standard datetime with timezone awareness."""

    def __init__(self, value: Union[str, datetime]):
        """Initialize datetime with validation and timezone handling."""
        if isinstance(value, str):
            self._datetime = self._parse_datetime_string(value)
        elif isinstance(value, datetime):
            self._datetime = value
        else:
            raise ValueError("DateTime must be a string or datetime object")

        self._validate_datetime()

    @property
    def datetime_obj(self) -> datetime:
        """Get the datetime object."""
        return self._datetime

    @property
    def formatted_value(self) -> str:
        """Get the formatted datetime string (YYYY/MM/DD HH:MM:SS)."""
        return self._datetime.strftime("%Y/%m/%d %H:%M:%S")

    @property
    def iso_format(self) -> str:
        """Get the ISO format datetime string."""
        return self._datetime.isoformat()

    def _parse_datetime_string(self, value: str) -> datetime:
        """Parse datetime string in various formats."""
        if not value or not value.strip():
            raise ValueError("DateTime string cannot be empty")

        value = value.strip()

        # Try different datetime formats
        formats = [
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d",
            "%Y-%m-%d"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        raise ValueError(f"Invalid datetime format: {value}. "
                         f"Expected formats: YYYY/MM/DD HH:MM:SS, YYYY-MM-DD HH:MM:SS, "
                         f"YYYY/MM/DD, or YYYY-MM-DD")

    def _validate_datetime(self) -> None:
        """Validate datetime is within reasonable range."""
        # Set reasonable bounds for SPS time conversion
        min_year = 1900
        max_year = 2200

        if self._datetime.year < min_year or self._datetime.year > max_year:
            raise ValueError(
                f"DateTime year out of reasonable range: {self._datetime.year}")

    def to_timezone(self, tz: timezone) -> 'StandardDateTime':
        """Convert to specified timezone."""
        if self._datetime.tzinfo is None:
            # Assume naive datetime is in the specified timezone
            dt_with_tz = self._datetime.replace(tzinfo=tz)
        else:
            # Convert to the specified timezone
            dt_with_tz = self._datetime.astimezone(tz)

        return StandardDateTime(dt_with_tz)

    def __str__(self) -> str:
        return self.formatted_value

    def __repr__(self) -> str:
        return f"StandardDateTime('{self.formatted_value}')"


class SpsTimeConversionResult(IValueObject):
    """Value object representing the result of an SPS time conversion."""

    def __init__(self, sps_timestamp: SpsTimestamp, standard_datetime: StandardDateTime,
                 conversion_message: str = None):
        """Initialize conversion result."""
        self._sps_timestamp = sps_timestamp
        self._standard_datetime = standard_datetime
        self._conversion_message = conversion_message or "Conversion completed successfully"

    @property
    def sps_timestamp(self) -> SpsTimestamp:
        """Get the SPS timestamp."""
        return self._sps_timestamp

    @property
    def standard_datetime(self) -> StandardDateTime:
        """Get the standard datetime."""
        return self._standard_datetime

    @property
    def conversion_message(self) -> str:
        """Get the conversion message."""
        return self._conversion_message

    def to_dict(self) -> dict:
        """Convert to dictionary format for UI compatibility."""
        return {
            "sps_timestamp": self._sps_timestamp.formatted_value,
            "sps_minutes": self._sps_timestamp.minutes,
            "datetime": self._standard_datetime.formatted_value,
            "datetime_obj": self._standard_datetime.datetime_obj,
            "message": self._conversion_message
        }

    def __str__(self) -> str:
        return f"SPS: {self._sps_timestamp} ↔ DateTime: {self._standard_datetime}"

    def __repr__(self) -> str:
        return f"SpsTimeConversionResult({self._sps_timestamp!r}, {self._standard_datetime!r})"


class TimeConversionConstants:
    """Constants used in SPS time conversion calculations."""

    # SPS epoch is December 31, 1967 00:00:00 UTC
    SPS_EPOCH = datetime(1967, 12, 31, 0, 0, 0, tzinfo=timezone.utc)

    # Standard timezone configuration
    @classmethod
    def get_standard_timezone(cls) -> timezone:
        """Get the local standard timezone offset (ignoring daylight saving time)."""
        import time

        # Always use time.timezone which is the standard time offset
        # (time.timezone is the offset for standard time, time.altzone is for DST)
        standard_offset_seconds = time.timezone

        # Convert to hours (negative because time.timezone is west of UTC)
        offset_hours = -standard_offset_seconds / 3600

        return timezone(timedelta(hours=offset_hours))

    @classmethod
    def get_system_info(cls) -> dict:
        """Get information about the SPS time conversion system."""
        return {
            "sps_epoch": "1967-12-31 00:00:00 UTC",
            "description": "SPS Unix timestamp converter - converts between SPS time (minutes since epoch) and datetime",
            "examples": [
                {"sps_minutes": "30000000", "datetime": "2024/04/15 12:00:00"},
                {"sps_minutes": "0", "datetime": "1967/12/31 00:00:00"}
            ],
            "rules": [
                "SPS timestamp is in minutes since December 31, 1967 UTC",
                "DateTime format: YYYY/MM/DD HH:MM:SS",
                "Conversion is bidirectional",
                "Times use fixed timezone offset (ignores daylight saving time)",
                "Timestamps must be numeric values"
            ]
        }
