"""
SPS Time Converter page controller following MVC pattern.
Handles UI logic and coordinates between UI components and business services.
"""

from typing import Dict, Any, Union
from datetime import datetime
import dash_mantine_components as dmc
from core.interfaces import IPageController, ISpsTimeConverter, Result
from components.bootstrap_icon import BootstrapIcon


class SpsTimeConverterPageController(IPageController):
    """Controller for SPS Time Converter page."""

    def __init__(self, converter_service: ISpsTimeConverter):
        """Initialize controller with converter service."""
        self._converter_service = converter_service

    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle input changes and return UI updates."""
        if not value or (isinstance(value, str) and value.strip() == ""):
            return Result.ok({
                "sps_timestamp_value": "",
                "datetime_value": None,
                "message": ""
            }, "Input cleared")

        try:
            if input_id == 'sps-timestamp-input':
                return self._handle_sps_timestamp_input(value.strip())
            elif input_id == 'sps-datetime-input':
                return self._handle_datetime_input(value)
            else:
                return Result.fail(f"Unknown input ID: {input_id}", "Invalid input source")

        except Exception as e:
            return Result.fail(f"Controller error: {str(e)}", "An unexpected error occurred")

    def handle_current_time_request(self) -> Result[Dict[str, Any]]:
        """Handle get current time button click."""
        try:
            result = self._converter_service.get_current_sps_timestamp()

            if result.success:
                return Result.ok({
                    "sps_timestamp_value": result.data.get("sps_timestamp", ""),
                    "datetime_value": None,
                    "message": self._create_success_alert(
                        f"Current SPS timestamp: {result.data.get('sps_timestamp', '')} minutes")
                }, "Current time retrieved successfully")
            else:
                return Result.ok({
                    "sps_timestamp_value": "",
                    "datetime_value": None,
                    "message": self._create_error_alert(result.error)
                }, "Failed to get current time")

        except Exception as e:
            return Result.fail(f"Error getting current time: {str(e)}", "Failed to retrieve current time")

    def _handle_sps_timestamp_input(self, timestamp_value: str) -> Result[Dict[str, Any]]:
        """Handle SPS timestamp input and convert to datetime."""
        result = self._converter_service.sps_timestamp_to_datetime(
            timestamp_value)

        if result.success:
            # Convert the timezone-aware datetime to a naive datetime for the DateTimePicker
            dt_obj = result.data.get("datetime_obj")
            naive_dt = dt_obj.replace(tzinfo=None) if dt_obj else None

            message = self._create_success_alert(
                f"Converted: {timestamp_value} minutes → {result.data.get('datetime', '')}")

            return Result.ok({
                "sps_timestamp_value": timestamp_value,
                "datetime_value": naive_dt,
                "message": message
            }, "SPS timestamp conversion successful")
        else:
            message = self._create_error_alert(result.error)
            return Result.ok({
                "sps_timestamp_value": timestamp_value,
                "datetime_value": None,
                "message": message
            }, "SPS timestamp conversion failed")

    def _handle_datetime_input(self, datetime_value: Union[datetime, str]) -> Result[Dict[str, Any]]:
        """Handle datetime input and convert to SPS timestamp."""
        try:
            # Convert datetime object to string format expected by service
            if isinstance(datetime_value, datetime):
                datetime_str = datetime_value.strftime("%Y/%m/%d %H:%M:%S")
            else:
                datetime_str = str(datetime_value).replace("-", "/")

            result = self._converter_service.datetime_to_sps_timestamp(
                datetime_str)

            if result.success:
                message = self._create_success_alert(
                    f"Converted: {datetime_str} → {result.data.get('sps_timestamp', '')} minutes")

                return Result.ok({
                    "sps_timestamp_value": result.data.get("sps_timestamp", ""),
                    "datetime_value": datetime_value,
                    "message": message
                }, "DateTime conversion successful")
            else:
                message = self._create_error_alert(result.error)
                return Result.ok({
                    "sps_timestamp_value": "",
                    "datetime_value": datetime_value,
                    "message": message
                }, "DateTime conversion failed")

        except Exception as e:
            message = self._create_error_alert(
                f"Error processing datetime: {str(e)}")
            return Result.ok({
                "sps_timestamp_value": "",
                "datetime_value": datetime_value,
                "message": message
            }, "DateTime processing error")

    def _create_success_alert(self, message: str) -> dmc.Alert:
        """Create a success alert component."""
        return dmc.Alert(
            title="Conversion Successful",
            children=message,
            color="green",
            icon=BootstrapIcon(icon="check")
        )

    def _create_error_alert(self, error: str) -> dmc.Alert:
        """Create an error alert component."""
        return dmc.Alert(
            title="Conversion Error",
            children=error,
            color="red",
            icon=BootstrapIcon(icon="exclamation-circle")
        )

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for the help modal."""
        return self._converter_service.get_system_info()


class SpsTimeUIResponseFormatter:
    """Formats SPS Time Converter responses for Dash callbacks."""

    @staticmethod
    def format_conversion_response(controller_result: Result[Dict[str, Any]]) -> tuple:
        """Format controller result for SPS time conversion callback."""
        if controller_result.success:
            data = controller_result.data
            return (
                data.get("datetime_value"),
                data.get("sps_timestamp_value", ""),
                data.get("message", "")
            )
        else:
            error_alert = dmc.Alert(
                title="Controller Error",
                children=controller_result.error,
                color="red",
                icon=BootstrapIcon(icon="exclamation-circle")
            )
            return (None, "", error_alert)

    @staticmethod
    def format_current_time_response(controller_result: Result[Dict[str, Any]]) -> str:
        """Format controller result for current time callback."""
        if controller_result.success:
            return controller_result.data.get("sps_timestamp_value", "")
        else:
            return ""
