"""
SPS Time Converter service following SOLID principles and clean architecture.
Implements ISpsTimeConverter interface with dependency injection support.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from core.interfaces import ISpsTimeConverter, IValidator, Result
from domain.time_models import SpsTimestamp, StandardDateTime, SpsTimeConversionResult, TimeConversionConstants


class SpsTimeConverterService(ISpsTimeConverter):
    """Service for converting between SPS Unix timestamp (in minutes) and DateTime."""

    def __init__(self, timestamp_validator: IValidator = None, datetime_validator: IValidator = None):
        """Initialize with dependency injection for validators."""
        self._timestamp_validator = timestamp_validator
        self._datetime_validator = datetime_validator
        self._local_timezone = TimeConversionConstants.get_standard_timezone()

    def sps_timestamp_to_datetime(self, sps_timestamp: str) -> Result[Dict[str, Any]]:
        """Convert SPS Unix timestamp (in minutes) to DateTime."""
        try:
            # Validate input if validator is provided
            if self._timestamp_validator:
                validation_result = self._timestamp_validator.validate(
                    sps_timestamp)
                if not validation_result.success:
                    return Result.fail(validation_result.error, validation_result.message)

            # Create domain objects
            sps_ts = SpsTimestamp(sps_timestamp)

            # Convert to UTC datetime
            utc_datetime = self._convert_sps_to_utc_datetime(sps_ts)

            # Convert to local time (ignoring daylight saving time)
            local_datetime = utc_datetime.astimezone(self._local_timezone)
            standard_dt = StandardDateTime(local_datetime)

            # Create result object
            conversion_result = SpsTimeConversionResult(
                sps_ts,
                standard_dt,
                f"Converted SPS timestamp '{sps_timestamp}' minutes to '{standard_dt.formatted_value}'"
            )

            return Result.ok(conversion_result.to_dict(), conversion_result.conversion_message)

        except ValueError as e:
            return Result.fail(str(e), "Invalid SPS timestamp format or value")
        except Exception as e:
            return Result.fail(f"Conversion error: {str(e)}", "An unexpected error occurred during conversion")

    def datetime_to_sps_timestamp(self, datetime_str: str) -> Result[Dict[str, Any]]:
        """Convert DateTime string to SPS Unix timestamp (in minutes)."""
        try:
            # Validate input if validator is provided
            if self._datetime_validator:
                validation_result = self._datetime_validator.validate(
                    datetime_str)
                if not validation_result.success:
                    return Result.fail(validation_result.error, validation_result.message)

            # Create domain objects
            standard_dt = StandardDateTime(datetime_str)

            # Convert to UTC (assuming input is in fixed local time, no DST)
            local_tz = standard_dt.datetime_obj.replace(
                tzinfo=self._local_timezone)
            utc_dt = local_tz.astimezone(timezone.utc)

            # Calculate SPS timestamp
            sps_ts = self._convert_utc_datetime_to_sps(utc_dt)

            # Create result object
            conversion_result = SpsTimeConversionResult(
                sps_ts,
                standard_dt,
                f"Converted datetime '{datetime_str}' to SPS timestamp '{sps_ts.formatted_value}' minutes"
            )

            # Return compatible format for existing UI
            result_dict = conversion_result.to_dict()
            result_dict["sps_timestamp"] = sps_ts.formatted_value
            result_dict["sps_timestamp_float"] = sps_ts.minutes

            return Result.ok(result_dict, conversion_result.conversion_message)

        except ValueError as e:
            return Result.fail(str(e), "Invalid datetime format or value")
        except Exception as e:
            return Result.fail(f"Conversion error: {str(e)}", "An unexpected error occurred during conversion")

    def get_current_sps_timestamp(self) -> Result[Dict[str, Any]]:
        """Get current datetime as SPS timestamp (using fixed timezone, no DST)."""
        try:
            current_utc = datetime.now(timezone.utc)
            sps_ts = self._convert_utc_datetime_to_sps(current_utc)

            # Convert current time to fixed local time for display
            current_local = current_utc.astimezone(self._local_timezone)
            standard_dt = StandardDateTime(current_local)

            conversion_result = SpsTimeConversionResult(
                sps_ts,
                standard_dt,
                f"Current SPS timestamp: {sps_ts.formatted_value} minutes"
            )

            # Return compatible format for existing UI
            result_dict = conversion_result.to_dict()
            result_dict["sps_timestamp"] = sps_ts.formatted_value
            result_dict["current_datetime"] = standard_dt.formatted_value

            return Result.ok(result_dict, conversion_result.conversion_message)

        except Exception as e:
            return Result.fail(f"Error getting current timestamp: {str(e)}", "Failed to get current timestamp")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the SPS time conversion system."""
        try:
            system_info = TimeConversionConstants.get_system_info()
            return Result.ok({"system_info": system_info}, "System information retrieved successfully")
        except Exception as e:
            return Result.fail(f"Error getting system info: {str(e)}", "Failed to retrieve system information")

    def convert(self, input_value: Any) -> Result[Any]:
        """Generic convert method for IConverter interface."""
        if isinstance(input_value, dict):
            if "sps_timestamp" in input_value:
                return self.sps_timestamp_to_datetime(str(input_value["sps_timestamp"]))
            elif "datetime" in input_value:
                return self.datetime_to_sps_timestamp(str(input_value["datetime"]))

        return Result.fail("Invalid input format", "Input must contain either 'sps_timestamp' or 'datetime' key")

    def _convert_sps_to_utc_datetime(self, sps_timestamp: SpsTimestamp) -> datetime:
        """Convert SPS timestamp to UTC datetime."""
        return TimeConversionConstants.SPS_EPOCH + timedelta(seconds=sps_timestamp.seconds)

    def _convert_utc_datetime_to_sps(self, utc_datetime: datetime) -> SpsTimestamp:
        """Convert UTC datetime to SPS timestamp."""
        time_diff = utc_datetime - TimeConversionConstants.SPS_EPOCH
        minutes = time_diff.total_seconds() / 60
        return SpsTimestamp(minutes)


class LegacySpsTimeConverterService:
    """Legacy wrapper service for backward compatibility."""

    def __init__(self, modern_service: SpsTimeConverterService):
        """Initialize with modern service."""
        self._modern_service = modern_service

    def sps_timestamp_to_datetime(self, sps_minutes: str) -> Dict[str, Any]:
        """Convert SPS Unix timestamp (in minutes) to DateTime - legacy format."""
        result = self._modern_service.sps_timestamp_to_datetime(sps_minutes)

        if result.success:
            return {
                "success": True,
                **result.data
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": result.message
            }

    def datetime_to_sps_timestamp(self, datetime_str: str) -> Dict[str, Any]:
        """Convert DateTime string to SPS Unix timestamp (in minutes) - legacy format."""
        result = self._modern_service.datetime_to_sps_timestamp(datetime_str)

        if result.success:
            return {
                "success": True,
                **result.data
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": result.message
            }

    def get_current_sps_timestamp(self) -> Dict[str, Any]:
        """Get current datetime as SPS timestamp - legacy format."""
        result = self._modern_service.get_current_sps_timestamp()

        if result.success:
            return {
                "success": True,
                **result.data
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": result.message
            }

    def get_conversion_info(self) -> Dict[str, Any]:
        """Get information about the SPS time conversion system - legacy format."""
        result = self._modern_service.get_system_info()

        if result.success:
            return {
                "success": True,
                **result.data
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": result.message
            }
