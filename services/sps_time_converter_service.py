"""
SPS Time Converter service for DMC application.
Converts between SPS Unix timestamp (in minutes) and DateTime.
Based on TimeConversionHelper.cs from UTC_Core project.
Ignores daylight saving time by using fixed UTC offset.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict


class SpsTimeConverterService:
    """Service for converting between SPS Unix timestamp (in minutes) and DateTime."""

    # SPS epoch is December 31, 1967 00:00:00 UTC
    SPS_EPOCH = datetime(1967, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
    
    def __init__(self):
        """Initialize with automatic detection of standard timezone offset (no DST)."""
        self.LOCAL_TIMEZONE = self._get_standard_timezone()
    
    def _get_standard_timezone(self) -> timezone:
        """Get the local standard timezone offset (ignoring daylight saving time)."""
        import time
        
        # Always use time.timezone which is the standard time offset
        # (time.timezone is the offset for standard time, time.altzone is for DST)
        standard_offset_seconds = time.timezone
        
        # Convert to hours (negative because time.timezone is west of UTC)
        offset_hours = -standard_offset_seconds / 3600
        
        return timezone(timedelta(hours=offset_hours))

    def sps_timestamp_to_datetime(self, sps_minutes: str) -> Dict[str, Any]:
        """Convert SPS Unix timestamp (in minutes) to DateTime."""
        try:
            # Convert string to float (minutes)
            minutes = float(sps_minutes)
            
            # Convert minutes to seconds
            seconds = minutes * 60
            
            # Add seconds to SPS epoch and convert to fixed local time (no DST)
            utc_datetime = self.SPS_EPOCH.replace(tzinfo=timezone.utc) + \
                          timedelta(seconds=seconds)
            
            # Convert to fixed local time (ignoring daylight saving time)
            local_datetime = utc_datetime.astimezone(self.LOCAL_TIMEZONE)
            
            # Format as string for display (similar to C# custom format: yyyy/MM/dd HH:mm:ss)
            formatted_datetime = local_datetime.strftime("%Y/%m/%d %H:%M:%S")
            
            return {
                "success": True,
                "datetime": formatted_datetime,
                "datetime_obj": local_datetime,
                "message": f"Converted SPS timestamp '{sps_minutes}' minutes to '{formatted_datetime}'"
            }
            
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": f"Invalid SPS timestamp: {str(e)}",
                "message": "SPS timestamp must be a valid numeric value"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Conversion error: {str(e)}",
                "message": "An unexpected error occurred during conversion"
            }

    def datetime_to_sps_timestamp(self, datetime_str: str) -> Dict[str, Any]:
        """Convert DateTime string to SPS Unix timestamp (in minutes)."""
        try:
            # Parse the datetime string (expected format: YYYY/MM/DD HH:MM:SS)
            try:
                dt = datetime.strptime(datetime_str, "%Y/%m/%d %H:%M:%S")
            except ValueError:
                # Try alternative formats
                try:
                    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    dt = datetime.strptime(datetime_str, "%Y/%m/%d")
            
            # Convert to UTC (assuming input is in fixed local time, no DST)
            local_tz = dt.replace(tzinfo=self.LOCAL_TIMEZONE)
            utc_dt = local_tz.astimezone(timezone.utc)
            
            # Calculate difference from SPS epoch in seconds
            time_diff = utc_dt - self.SPS_EPOCH
            total_seconds = time_diff.total_seconds()
            
            # Convert to minutes
            minutes = total_seconds / 60
            
            return {
                "success": True,
                "sps_timestamp": f"{minutes:.6f}",
                "sps_timestamp_float": minutes,
                "message": f"Converted datetime '{datetime_str}' to SPS timestamp '{minutes:.6f}' minutes"
            }
            
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid datetime format: {str(e)}",
                "message": "DateTime must be in format YYYY/MM/DD HH:MM:SS or YYYY/MM/DD"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Conversion error: {str(e)}",
                "message": "An unexpected error occurred during conversion"
            }

    def get_current_sps_timestamp(self) -> Dict[str, Any]:
        """Get current datetime as SPS timestamp (using fixed timezone, no DST)."""
        try:
            current_utc = datetime.now(timezone.utc)
            time_diff = current_utc - self.SPS_EPOCH
            minutes = time_diff.total_seconds() / 60
            
            # Convert current time to fixed local time for display
            current_local = current_utc.astimezone(self.LOCAL_TIMEZONE)
            
            return {
                "success": True,
                "sps_timestamp": f"{minutes:.6f}",
                "current_datetime": current_local.strftime("%Y/%m/%d %H:%M:%S"),
                "message": f"Current SPS timestamp: {minutes:.6f} minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting current timestamp: {str(e)}",
                "message": "Failed to get current timestamp"
            }

    def get_conversion_info(self) -> Dict[str, Any]:
        """Get information about the SPS time conversion system."""
        return {
            "success": True,
            "system_info": {
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
        }
