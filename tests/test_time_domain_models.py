"""
Unit tests for SPS Time domain models.
Tests value objects, validation, and business logic.
"""

import unittest
from datetime import datetime, timezone, timedelta
from domain.time_models import (
    SpsTimestamp, StandardDateTime, SpsTimeConversionResult, TimeConversionConstants
)


class TestSpsTimestamp(unittest.TestCase):
    """Test cases for SpsTimestamp value object."""

    def test_create_from_string(self):
        """Test creating SPS timestamp from string."""
        sps = SpsTimestamp("30000000")
        self.assertEqual(sps.minutes, 30000000.0)
        self.assertEqual(sps.formatted_value, "30000000.000000")

    def test_create_from_float(self):
        """Test creating SPS timestamp from float."""
        sps = SpsTimestamp(30000000.5)
        self.assertEqual(sps.minutes, 30000000.5)
        self.assertEqual(sps.seconds, 1800000030.0)

    def test_create_from_int(self):
        """Test creating SPS timestamp from integer."""
        sps = SpsTimestamp(123456)
        self.assertEqual(sps.minutes, 123456.0)

    def test_validation_empty_string(self):
        """Test validation with empty string."""
        with self.assertRaises(ValueError) as context:
            SpsTimestamp("")
        self.assertIn("empty", str(context.exception))

    def test_validation_invalid_string(self):
        """Test validation with invalid string."""
        with self.assertRaises(ValueError) as context:
            SpsTimestamp("not_a_number")
        self.assertIn("numeric", str(context.exception))

    def test_validation_out_of_range(self):
        """Test validation with out of range values."""
        with self.assertRaises(ValueError) as context:
            SpsTimestamp(200_000_000)  # Too large
        self.assertIn("reasonable range", str(context.exception))

    def test_negative_values_allowed(self):
        """Test that reasonable negative values are allowed."""
        sps = SpsTimestamp(-1000000)
        self.assertEqual(sps.minutes, -1000000.0)

    def test_string_representation(self):
        """Test string representation."""
        sps = SpsTimestamp(123.456789)
        self.assertEqual(str(sps), "123.456789")
        self.assertEqual(repr(sps), "SpsTimestamp(123.456789)")

    def test_value_object_equality(self):
        """Test value object equality."""
        sps1 = SpsTimestamp("12345")
        sps2 = SpsTimestamp("12345")
        sps3 = SpsTimestamp("54321")

        self.assertEqual(sps1, sps2)
        self.assertNotEqual(sps1, sps3)
        self.assertEqual(hash(sps1), hash(sps2))


class TestStandardDateTime(unittest.TestCase):
    """Test cases for StandardDateTime value object."""

    def test_create_from_string_full_format(self):
        """Test creating datetime from full format string."""
        dt = StandardDateTime("2024/04/15 14:30:45")
        expected = datetime(2024, 4, 15, 14, 30, 45)
        self.assertEqual(dt.datetime_obj, expected)
        self.assertEqual(dt.formatted_value, "2024/04/15 14:30:45")

    def test_create_from_string_date_only(self):
        """Test creating datetime from date-only string."""
        dt = StandardDateTime("2024/04/15")
        expected = datetime(2024, 4, 15, 0, 0, 0)
        self.assertEqual(dt.datetime_obj, expected)

    def test_create_from_string_alternative_format(self):
        """Test creating datetime from alternative format."""
        dt = StandardDateTime("2024-04-15 14:30:45")
        expected = datetime(2024, 4, 15, 14, 30, 45)
        self.assertEqual(dt.datetime_obj, expected)

    def test_create_from_datetime_object(self):
        """Test creating from datetime object."""
        dt_obj = datetime(2024, 4, 15, 14, 30, 45)
        dt = StandardDateTime(dt_obj)
        self.assertEqual(dt.datetime_obj, dt_obj)

    def test_validation_empty_string(self):
        """Test validation with empty string."""
        with self.assertRaises(ValueError) as context:
            StandardDateTime("")
        self.assertIn("empty", str(context.exception))

    def test_validation_invalid_format(self):
        """Test validation with invalid format."""
        with self.assertRaises(ValueError) as context:
            StandardDateTime("invalid_date")
        self.assertIn("Invalid datetime format", str(context.exception))

    def test_validation_year_out_of_range(self):
        """Test validation with year out of range."""
        with self.assertRaises(ValueError) as context:
            StandardDateTime("1800/01/01")
        self.assertIn("reasonable range", str(context.exception))

    def test_iso_format(self):
        """Test ISO format output."""
        dt = StandardDateTime("2024/04/15 14:30:45")
        expected_iso = "2024-04-15T14:30:45"
        self.assertEqual(dt.iso_format, expected_iso)

    def test_to_timezone(self):
        """Test timezone conversion."""
        dt = StandardDateTime("2024/04/15 14:30:45")
        utc_tz = timezone.utc
        dt_with_tz = dt.to_timezone(utc_tz)

        self.assertEqual(dt_with_tz.datetime_obj.tzinfo, utc_tz)

    def test_string_representation(self):
        """Test string representation."""
        dt = StandardDateTime("2024/04/15 14:30:45")
        self.assertEqual(str(dt), "2024/04/15 14:30:45")
        self.assertEqual(repr(dt), "StandardDateTime('2024/04/15 14:30:45')")

    def test_value_object_equality(self):
        """Test value object equality."""
        dt1 = StandardDateTime("2024/04/15 14:30:45")
        dt2 = StandardDateTime("2024/04/15 14:30:45")
        dt3 = StandardDateTime("2024/04/15 14:30:46")

        self.assertEqual(dt1, dt2)
        self.assertNotEqual(dt1, dt3)
        self.assertEqual(hash(dt1), hash(dt2))


class TestSpsTimeConversionResult(unittest.TestCase):
    """Test cases for SpsTimeConversionResult value object."""

    def setUp(self):
        """Set up test fixtures."""
        self.sps_timestamp = SpsTimestamp("30000000")
        self.standard_datetime = StandardDateTime("2024/04/15 14:30:45")

    def test_create_conversion_result(self):
        """Test creating conversion result."""
        result = SpsTimeConversionResult(
            self.sps_timestamp,
            self.standard_datetime,
            "Test conversion"
        )

        self.assertEqual(result.sps_timestamp, self.sps_timestamp)
        self.assertEqual(result.standard_datetime, self.standard_datetime)
        self.assertEqual(result.conversion_message, "Test conversion")

    def test_create_conversion_result_default_message(self):
        """Test creating conversion result with default message."""
        result = SpsTimeConversionResult(
            self.sps_timestamp, self.standard_datetime)
        self.assertEqual(result.conversion_message,
                         "Conversion completed successfully")

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = SpsTimeConversionResult(
            self.sps_timestamp,
            self.standard_datetime,
            "Test conversion"
        )

        dict_result = result.to_dict()
        expected_keys = ["sps_timestamp", "sps_minutes",
                         "datetime", "datetime_obj", "message"]

        for key in expected_keys:
            self.assertIn(key, dict_result)

        self.assertEqual(dict_result["sps_timestamp"],
                         self.sps_timestamp.formatted_value)
        self.assertEqual(dict_result["sps_minutes"],
                         self.sps_timestamp.minutes)
        self.assertEqual(dict_result["datetime"],
                         self.standard_datetime.formatted_value)
        self.assertEqual(dict_result["datetime_obj"],
                         self.standard_datetime.datetime_obj)
        self.assertEqual(dict_result["message"], "Test conversion")

    def test_string_representation(self):
        """Test string representation."""
        result = SpsTimeConversionResult(
            self.sps_timestamp, self.standard_datetime)
        expected_str = f"SPS: {self.sps_timestamp} ↔ DateTime: {self.standard_datetime}"
        self.assertEqual(str(result), expected_str)

    def test_value_object_equality(self):
        """Test value object equality."""
        result1 = SpsTimeConversionResult(
            self.sps_timestamp, self.standard_datetime, "msg1")
        result2 = SpsTimeConversionResult(
            self.sps_timestamp, self.standard_datetime, "msg1")
        result3 = SpsTimeConversionResult(
            self.sps_timestamp, self.standard_datetime, "msg2")

        self.assertEqual(result1, result2)
        self.assertNotEqual(result1, result3)
        self.assertEqual(hash(result1), hash(result2))


class TestTimeConversionConstants(unittest.TestCase):
    """Test cases for TimeConversionConstants."""

    def test_sps_epoch(self):
        """Test SPS epoch constant."""
        expected_epoch = datetime(1967, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(TimeConversionConstants.SPS_EPOCH, expected_epoch)

    def test_get_standard_timezone(self):
        """Test getting standard timezone."""
        tz = TimeConversionConstants.get_standard_timezone()
        self.assertIsInstance(tz, timezone)

        # Test that it returns a timezone with fixed offset (not DST)
        # This will depend on the system timezone, but should be consistent
        offset = tz.utcoffset(None)
        self.assertIsInstance(offset, timedelta)

    def test_get_system_info(self):
        """Test getting system information."""
        info = TimeConversionConstants.get_system_info()

        required_keys = ["sps_epoch", "description", "examples", "rules"]
        for key in required_keys:
            self.assertIn(key, info)

        self.assertEqual(info["sps_epoch"], "1967-12-31 00:00:00 UTC")
        self.assertIsInstance(info["examples"], list)
        self.assertIsInstance(info["rules"], list)
        self.assertTrue(len(info["examples"]) > 0)
        self.assertTrue(len(info["rules"]) > 0)


if __name__ == '__main__':
    unittest.main()
