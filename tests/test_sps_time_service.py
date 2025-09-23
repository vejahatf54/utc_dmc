"""
Unit tests for SPS Time Converter service.
Tests business logic, validation, and service interactions.
"""

import unittest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone, timedelta
from core.interfaces import IValidator, Result
from services.sps_time_converter_service import SpsTimeConverterService, LegacySpsTimeConverterService
from domain.time_models import TimeConversionConstants


class TestSpsTimeConverterService(unittest.TestCase):
    """Test cases for SpsTimeConverterService."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock validators
        self.mock_timestamp_validator = Mock(spec=IValidator)
        self.mock_datetime_validator = Mock(spec=IValidator)

        # Create service with mock validators
        self.service = SpsTimeConverterService(
            timestamp_validator=self.mock_timestamp_validator,
            datetime_validator=self.mock_datetime_validator
        )

        # Also create service without validators for some tests
        self.service_no_validators = SpsTimeConverterService()

    def test_sps_timestamp_to_datetime_success(self):
        """Test successful SPS timestamp to datetime conversion."""
        # Setup mock validator to succeed
        self.mock_timestamp_validator.validate.return_value = Result.ok(
            True, "Valid")

        # Test conversion
        result = self.service.sps_timestamp_to_datetime("30000000")

        # Verify result
        self.assertTrue(result.success)
        self.assertIn("sps_timestamp", result.data)
        self.assertIn("datetime", result.data)
        self.assertIn("datetime_obj", result.data)
        self.assertIn("message", result.data)

        # Verify validator was called
        self.mock_timestamp_validator.validate.assert_called_once_with(
            "30000000")

    def test_sps_timestamp_to_datetime_validation_failure(self):
        """Test SPS timestamp to datetime conversion with validation failure."""
        # Setup mock validator to fail
        self.mock_timestamp_validator.validate.return_value = Result.fail(
            "Invalid timestamp", "Timestamp must be numeric"
        )

        # Test conversion
        result = self.service.sps_timestamp_to_datetime("invalid")

        # Verify result
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid timestamp")
        self.assertEqual(result.message, "Timestamp must be numeric")

    def test_sps_timestamp_to_datetime_no_validator(self):
        """Test SPS timestamp to datetime conversion without validator."""
        result = self.service_no_validators.sps_timestamp_to_datetime(
            "30000000")

        # Should succeed without validation
        self.assertTrue(result.success)
        self.assertIn("datetime", result.data)

    def test_sps_timestamp_to_datetime_invalid_value(self):
        """Test SPS timestamp to datetime conversion with invalid value."""
        # Setup mock validator to succeed (let domain model handle validation)
        self.mock_timestamp_validator.validate.return_value = Result.ok(
            True, "Valid")

        # Test with invalid timestamp that will fail in domain model
        result = self.service.sps_timestamp_to_datetime("not_a_number")

        # Should fail at domain model level
        self.assertFalse(result.success)
        self.assertIn("Invalid SPS timestamp", result.message)

    def test_datetime_to_sps_timestamp_success(self):
        """Test successful datetime to SPS timestamp conversion."""
        # Setup mock validator to succeed
        self.mock_datetime_validator.validate.return_value = Result.ok(
            True, "Valid")

        # Test conversion
        result = self.service.datetime_to_sps_timestamp("2024/04/15 14:30:45")

        # Verify result
        self.assertTrue(result.success)
        self.assertIn("sps_timestamp", result.data)
        self.assertIn("sps_timestamp_float", result.data)
        self.assertIn("datetime", result.data)
        self.assertIn("message", result.data)

        # Verify validator was called
        self.mock_datetime_validator.validate.assert_called_once_with(
            "2024/04/15 14:30:45")

    def test_datetime_to_sps_timestamp_validation_failure(self):
        """Test datetime to SPS timestamp conversion with validation failure."""
        # Setup mock validator to fail
        self.mock_datetime_validator.validate.return_value = Result.fail(
            "Invalid datetime", "DateTime format is invalid"
        )

        # Test conversion
        result = self.service.datetime_to_sps_timestamp("invalid_date")

        # Verify result
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid datetime")
        self.assertEqual(result.message, "DateTime format is invalid")

    def test_datetime_to_sps_timestamp_no_validator(self):
        """Test datetime to SPS timestamp conversion without validator."""
        result = self.service_no_validators.datetime_to_sps_timestamp(
            "2024/04/15 14:30:45")

        # Should succeed without validation
        self.assertTrue(result.success)
        self.assertIn("sps_timestamp", result.data)

    def test_get_current_sps_timestamp(self):
        """Test getting current SPS timestamp."""
        result = self.service.get_current_sps_timestamp()

        # Verify result
        self.assertTrue(result.success)
        self.assertIn("sps_timestamp", result.data)
        self.assertIn("current_datetime", result.data)
        self.assertIn("message", result.data)

        # Verify current timestamp is reasonable (within last few seconds)
        import time
        current_utc = datetime.now(timezone.utc)
        sps_epoch = TimeConversionConstants.SPS_EPOCH
        expected_minutes = (current_utc - sps_epoch).total_seconds() / 60
        actual_minutes = float(result.data["sps_timestamp"])

        # Should be within 1 minute of expected (allowing for test execution time)
        self.assertAlmostEqual(actual_minutes, expected_minutes, delta=1.0)

    def test_get_system_info(self):
        """Test getting system information."""
        result = self.service.get_system_info()

        # Verify result
        self.assertTrue(result.success)
        self.assertIn("system_info", result.data)

        system_info = result.data["system_info"]
        required_keys = ["sps_epoch", "description", "examples", "rules"]
        for key in required_keys:
            self.assertIn(key, system_info)

    def test_convert_generic_method_sps_to_datetime(self):
        """Test generic convert method with SPS timestamp."""
        input_data = {"sps_timestamp": "30000000"}
        result = self.service_no_validators.convert(input_data)

        self.assertTrue(result.success)
        self.assertIn("datetime", result.data)

    def test_convert_generic_method_datetime_to_sps(self):
        """Test generic convert method with datetime."""
        input_data = {"datetime": "2024/04/15 14:30:45"}
        result = self.service_no_validators.convert(input_data)

        self.assertTrue(result.success)
        self.assertIn("sps_timestamp", result.data)

    def test_convert_generic_method_invalid_input(self):
        """Test generic convert method with invalid input."""
        input_data = {"invalid_key": "value"}
        result = self.service.convert(input_data)

        self.assertFalse(result.success)
        self.assertIn("Invalid input format", result.error)

    def test_bidirectional_conversion_consistency(self):
        """Test that bidirectional conversion is consistent."""
        # Start with a known SPS timestamp
        original_sps = "30000000"

        # Convert to datetime
        result1 = self.service_no_validators.sps_timestamp_to_datetime(
            original_sps)
        self.assertTrue(result1.success)

        # Convert back to SPS timestamp
        datetime_str = result1.data["datetime"]
        result2 = self.service_no_validators.datetime_to_sps_timestamp(
            datetime_str)
        self.assertTrue(result2.success)

        # Should be very close to original (allowing for floating point precision)
        converted_sps = float(result2.data["sps_timestamp"])
        original_sps_float = float(original_sps)
        self.assertAlmostEqual(converted_sps, original_sps_float, places=6)

    def test_error_handling_in_conversion(self):
        """Test error handling in conversion methods."""
        # Test with None input (should be handled by validator or domain model)
        result = self.service_no_validators.sps_timestamp_to_datetime(None)
        self.assertFalse(result.success)


class TestLegacySpsTimeConverterService(unittest.TestCase):
    """Test cases for LegacySpsTimeConverterService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_modern_service = Mock(spec=SpsTimeConverterService)
        self.legacy_service = LegacySpsTimeConverterService(
            self.mock_modern_service)

    def test_sps_timestamp_to_datetime_success(self):
        """Test legacy wrapper with successful conversion."""
        # Setup mock to return successful result
        mock_result = Result.ok({
            "sps_timestamp": "30000000.000000",
            "datetime": "2024/04/15 14:30:45",
            "datetime_obj": datetime(2024, 4, 15, 14, 30, 45),
            "message": "Conversion successful"
        })
        self.mock_modern_service.sps_timestamp_to_datetime.return_value = mock_result

        # Test legacy method
        result = self.legacy_service.sps_timestamp_to_datetime("30000000")

        # Verify legacy format
        self.assertTrue(result["success"])
        self.assertIn("sps_timestamp", result)
        self.assertIn("datetime", result)
        self.assertIn("datetime_obj", result)
        self.assertIn("message", result)

    def test_sps_timestamp_to_datetime_failure(self):
        """Test legacy wrapper with failed conversion."""
        # Setup mock to return failed result
        mock_result = Result.fail("Invalid timestamp", "Error message")
        self.mock_modern_service.sps_timestamp_to_datetime.return_value = mock_result

        # Test legacy method
        result = self.legacy_service.sps_timestamp_to_datetime("invalid")

        # Verify legacy error format
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Invalid timestamp")
        self.assertEqual(result["message"], "Error message")

    def test_datetime_to_sps_timestamp_success(self):
        """Test legacy wrapper for datetime conversion."""
        # Setup mock to return successful result
        mock_result = Result.ok({
            "sps_timestamp": "30000000.000000",
            "sps_timestamp_float": 30000000.0,
            "datetime": "2024/04/15 14:30:45",
            "message": "Conversion successful"
        })
        self.mock_modern_service.datetime_to_sps_timestamp.return_value = mock_result

        # Test legacy method
        result = self.legacy_service.datetime_to_sps_timestamp(
            "2024/04/15 14:30:45")

        # Verify result
        self.assertTrue(result["success"])
        self.assertIn("sps_timestamp", result)
        self.assertIn("sps_timestamp_float", result)

    def test_get_current_sps_timestamp(self):
        """Test legacy wrapper for getting current timestamp."""
        # Setup mock
        mock_result = Result.ok({
            "sps_timestamp": "30000000.000000",
            "current_datetime": "2024/04/15 14:30:45",
            "message": "Current timestamp retrieved"
        })
        self.mock_modern_service.get_current_sps_timestamp.return_value = mock_result

        # Test legacy method
        result = self.legacy_service.get_current_sps_timestamp()

        # Verify result
        self.assertTrue(result["success"])
        self.assertIn("sps_timestamp", result)
        self.assertIn("current_datetime", result)

    def test_get_conversion_info(self):
        """Test legacy wrapper for getting conversion info."""
        # Setup mock
        mock_result = Result.ok({
            "system_info": {
                "sps_epoch": "1967-12-31 00:00:00 UTC",
                "description": "SPS time converter"
            }
        })
        self.mock_modern_service.get_system_info.return_value = mock_result

        # Test legacy method
        result = self.legacy_service.get_conversion_info()

        # Verify result
        self.assertTrue(result["success"])
        self.assertIn("system_info", result)


if __name__ == '__main__':
    unittest.main()
