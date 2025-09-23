"""
Unit tests for SPS Time Converter controller.
Tests UI logic, input handling, and service coordination.
"""

import unittest
from unittest.mock import Mock, MagicMock
from datetime import datetime
import dash_mantine_components as dmc
from core.interfaces import ISpsTimeConverter, Result
from controllers.sps_time_controller import SpsTimeConverterPageController, SpsTimeUIResponseFormatter
from components.bootstrap_icon import BootstrapIcon


class TestSpsTimeConverterPageController(unittest.TestCase):
    """Test cases for SpsTimeConverterPageController."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock(spec=ISpsTimeConverter)
        self.controller = SpsTimeConverterPageController(self.mock_service)

    def test_init(self):
        """Test controller initialization."""
        self.assertEqual(self.controller._converter_service, self.mock_service)

    def test_handle_input_change_empty_value(self):
        """Test handling empty input value."""
        result = self.controller.handle_input_change("sps-timestamp-input", "")

        self.assertTrue(result.success)
        data = result.data
        self.assertEqual(data["sps_timestamp_value"], "")
        self.assertIsNone(data["datetime_value"])
        self.assertEqual(data["message"], "")

    def test_handle_input_change_sps_timestamp_success(self):
        """Test handling SPS timestamp input with successful conversion."""
        # Setup mock service
        mock_result = Result.ok({
            "sps_timestamp": "30000000.000000",
            "datetime": "2024/04/15 14:30:45",
            "datetime_obj": datetime(2024, 4, 15, 14, 30, 45),
            "message": "Conversion successful"
        })
        self.mock_service.sps_timestamp_to_datetime.return_value = mock_result

        # Test controller
        result = self.controller.handle_input_change(
            "sps-timestamp-input", "30000000")

        # Verify result
        self.assertTrue(result.success)
        data = result.data
        self.assertEqual(data["sps_timestamp_value"], "30000000")
        self.assertIsInstance(data["datetime_value"], datetime)
        self.assertIsInstance(data["message"], dmc.Alert)

        # Verify service was called
        self.mock_service.sps_timestamp_to_datetime.assert_called_once_with(
            "30000000")

    def test_handle_input_change_sps_timestamp_failure(self):
        """Test handling SPS timestamp input with failed conversion."""
        # Setup mock service
        mock_result = Result.fail("Invalid timestamp", "Error message")
        self.mock_service.sps_timestamp_to_datetime.return_value = mock_result

        # Test controller
        result = self.controller.handle_input_change(
            "sps-timestamp-input", "invalid")

        # Verify result
        # Controller should handle service errors gracefully
        self.assertTrue(result.success)
        data = result.data
        self.assertEqual(data["sps_timestamp_value"], "invalid")
        self.assertIsNone(data["datetime_value"])
        self.assertIsInstance(data["message"], dmc.Alert)

    def test_handle_input_change_datetime_success(self):
        """Test handling datetime input with successful conversion."""
        # Setup mock service
        mock_result = Result.ok({
            "sps_timestamp": "30000000.000000",
            "sps_timestamp_float": 30000000.0,
            "datetime": "2024/04/15 14:30:45",
            "message": "Conversion successful"
        })
        self.mock_service.datetime_to_sps_timestamp.return_value = mock_result

        # Test with datetime object
        dt_obj = datetime(2024, 4, 15, 14, 30, 45)
        result = self.controller.handle_input_change(
            "sps-datetime-input", dt_obj)

        # Verify result
        self.assertTrue(result.success)
        data = result.data
        self.assertEqual(data["sps_timestamp_value"], "30000000.000000")
        self.assertEqual(data["datetime_value"], dt_obj)
        self.assertIsInstance(data["message"], dmc.Alert)

    def test_handle_input_change_datetime_string(self):
        """Test handling datetime input as string."""
        # Setup mock service
        mock_result = Result.ok({
            "sps_timestamp": "30000000.000000",
            "message": "Conversion successful"
        })
        self.mock_service.datetime_to_sps_timestamp.return_value = mock_result

        # Test with string input
        result = self.controller.handle_input_change(
            "sps-datetime-input", "2024/04/15 14:30:45")

        # Verify result
        self.assertTrue(result.success)
        self.mock_service.datetime_to_sps_timestamp.assert_called_once()

    def test_handle_input_change_unknown_input_id(self):
        """Test handling unknown input ID."""
        result = self.controller.handle_input_change("unknown-input", "value")

        self.assertFalse(result.success)
        self.assertIn("Unknown input ID", result.error)

    def test_handle_current_time_request_success(self):
        """Test handling current time request with success."""
        # Setup mock service
        mock_result = Result.ok({
            "sps_timestamp": "30000000.000000",
            "current_datetime": "2024/04/15 14:30:45",
            "message": "Current time retrieved"
        })
        self.mock_service.get_current_sps_timestamp.return_value = mock_result

        # Test controller
        result = self.controller.handle_current_time_request()

        # Verify result
        self.assertTrue(result.success)
        data = result.data
        self.assertEqual(data["sps_timestamp_value"], "30000000.000000")
        self.assertIsNone(data["datetime_value"])
        self.assertIsInstance(data["message"], dmc.Alert)

    def test_handle_current_time_request_failure(self):
        """Test handling current time request with failure."""
        # Setup mock service
        mock_result = Result.fail("Time error", "Failed to get time")
        self.mock_service.get_current_sps_timestamp.return_value = mock_result

        # Test controller
        result = self.controller.handle_current_time_request()

        # Verify result
        self.assertTrue(result.success)  # Controller handles errors gracefully
        data = result.data
        self.assertEqual(data["sps_timestamp_value"], "")
        self.assertIsInstance(data["message"], dmc.Alert)

    def test_get_system_info(self):
        """Test getting system information."""
        # Setup mock service
        mock_result = Result.ok({"system_info": {"description": "Test info"}})
        self.mock_service.get_system_info.return_value = mock_result

        # Test controller
        result = self.controller.get_system_info()

        # Verify result
        self.assertEqual(result, mock_result)
        self.mock_service.get_system_info.assert_called_once()

    def test_create_success_alert(self):
        """Test creating success alert."""
        alert = self.controller._create_success_alert("Test message")

        self.assertIsInstance(alert, dmc.Alert)
        self.assertEqual(alert.title, "Conversion Successful")
        self.assertEqual(alert.children, "Test message")
        self.assertEqual(alert.color, "green")

    def test_create_error_alert(self):
        """Test creating error alert."""
        alert = self.controller._create_error_alert("Error message")

        self.assertIsInstance(alert, dmc.Alert)
        self.assertEqual(alert.title, "Conversion Error")
        self.assertEqual(alert.children, "Error message")
        self.assertEqual(alert.color, "red")

    def test_error_handling_in_input_handling(self):
        """Test error handling when service raises exception."""
        # Setup mock service to raise exception
        self.mock_service.sps_timestamp_to_datetime.side_effect = Exception(
            "Service error")

        # Test controller
        result = self.controller.handle_input_change(
            "sps-timestamp-input", "30000000")

        # Verify error is handled gracefully
        self.assertFalse(result.success)
        self.assertIn("Controller error", result.error)


class TestSpsTimeUIResponseFormatter(unittest.TestCase):
    """Test cases for SpsTimeUIResponseFormatter."""

    def test_format_conversion_response_success(self):
        """Test formatting successful conversion response."""
        # Create controller result
        controller_result = Result.ok({
            "datetime_value": datetime(2024, 4, 15, 14, 30, 45),
            "sps_timestamp_value": "30000000.000000",
            "message": dmc.Alert(title="Success", children="Converted successfully", color="green")
        })

        # Format response
        datetime_value, timestamp_value, message = SpsTimeUIResponseFormatter.format_conversion_response(
            controller_result)

        # Verify formatted response
        self.assertIsInstance(datetime_value, datetime)
        self.assertEqual(timestamp_value, "30000000.000000")
        self.assertIsInstance(message, dmc.Alert)

    def test_format_conversion_response_failure(self):
        """Test formatting failed conversion response."""
        # Create controller result
        controller_result = Result.fail("Controller error", "Error occurred")

        # Format response
        datetime_value, timestamp_value, message = SpsTimeUIResponseFormatter.format_conversion_response(
            controller_result)

        # Verify formatted response
        self.assertIsNone(datetime_value)
        self.assertEqual(timestamp_value, "")
        self.assertIsInstance(message, dmc.Alert)
        self.assertEqual(message.title, "Controller Error")

    def test_format_current_time_response_success(self):
        """Test formatting successful current time response."""
        # Create controller result
        controller_result = Result.ok({
            "sps_timestamp_value": "30000000.000000"
        })

        # Format response
        timestamp_value = SpsTimeUIResponseFormatter.format_current_time_response(
            controller_result)

        # Verify formatted response
        self.assertEqual(timestamp_value, "30000000.000000")

    def test_format_current_time_response_failure(self):
        """Test formatting failed current time response."""
        # Create controller result
        controller_result = Result.fail("Time error", "Failed to get time")

        # Format response
        timestamp_value = SpsTimeUIResponseFormatter.format_current_time_response(
            controller_result)

        # Verify formatted response
        self.assertEqual(timestamp_value, "")

    def test_format_conversion_response_missing_data(self):
        """Test formatting response with missing data."""
        # Create controller result with partial data
        controller_result = Result.ok({
            "datetime_value": None,
            "sps_timestamp_value": "",
            "message": ""
        })

        # Format response
        datetime_value, timestamp_value, message = SpsTimeUIResponseFormatter.format_conversion_response(
            controller_result)

        # Verify formatted response
        self.assertIsNone(datetime_value)
        self.assertEqual(timestamp_value, "")
        self.assertEqual(message, "")


if __name__ == '__main__':
    unittest.main()
