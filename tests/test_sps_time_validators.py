"""
Unit tests for SPS Time input validators.
Tests validation logic for SPS timestamps and datetime inputs.
"""

import unittest
from validation.input_validators import (
    SpsTimestampInputValidator, DateTimeInputValidator,
    create_sps_timestamp_validator, create_datetime_validator
)


class TestSpsTimestampInputValidator(unittest.TestCase):
    """Test cases for SpsTimestampInputValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = SpsTimestampInputValidator()

    def test_validate_valid_integer_string(self):
        """Test validation with valid integer string."""
        result = self.validator.validate("30000000")

        self.assertTrue(result.success)
        self.assertEqual(result.message, "SPS timestamp input is valid")

    def test_validate_valid_float_string(self):
        """Test validation with valid float string."""
        result = self.validator.validate("30000000.123456")

        self.assertTrue(result.success)

    def test_validate_valid_negative_number(self):
        """Test validation with valid negative number."""
        result = self.validator.validate("-1000000")

        self.assertTrue(result.success)

    def test_validate_zero(self):
        """Test validation with zero."""
        result = self.validator.validate("0")

        self.assertTrue(result.success)

    def test_validate_none_value(self):
        """Test validation with None value."""
        result = self.validator.validate(None)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "SPS timestamp cannot be None")
        self.assertEqual(
            result.message, "Please provide a valid timestamp value")

    def test_validate_non_string_value(self):
        """Test validation with non-string value."""
        result = self.validator.validate(123456)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "SPS timestamp must be a string")

    def test_validate_empty_string(self):
        """Test validation with empty string."""
        result = self.validator.validate("")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "SPS timestamp cannot be empty")

    def test_validate_whitespace_only(self):
        """Test validation with whitespace-only string."""
        result = self.validator.validate("   ")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "SPS timestamp cannot be empty")

    def test_validate_non_numeric_string(self):
        """Test validation with non-numeric string."""
        result = self.validator.validate("not_a_number")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "SPS timestamp must be numeric")
        self.assertEqual(result.message, "Timestamp must be a valid number")

    def test_validate_mixed_alphanumeric(self):
        """Test validation with mixed alphanumeric string."""
        result = self.validator.validate("123abc456")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "SPS timestamp must be numeric")

    def test_validate_out_of_range_large(self):
        """Test validation with value too large."""
        result = self.validator.validate("200000000")  # Too large

        self.assertFalse(result.success)
        self.assertIn("reasonable range", result.error)

    def test_validate_out_of_range_small(self):
        """Test validation with value too small."""
        result = self.validator.validate("-200000000")  # Too small

        self.assertFalse(result.success)
        self.assertIn("reasonable range", result.error)

    def test_validate_scientific_notation(self):
        """Test validation with scientific notation."""
        result = self.validator.validate("3e7")  # 30,000,000

        self.assertTrue(result.success)

    def test_validate_with_spaces(self):
        """Test validation with leading/trailing spaces."""
        result = self.validator.validate("  30000000  ")

        self.assertTrue(result.success)


class TestDateTimeInputValidator(unittest.TestCase):
    """Test cases for DateTimeInputValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = DateTimeInputValidator()

    def test_validate_full_format_slash(self):
        """Test validation with full format using slashes."""
        result = self.validator.validate("2024/04/15 14:30:45")

        self.assertTrue(result.success)
        self.assertEqual(result.message, "DateTime input is valid")

    def test_validate_full_format_dash(self):
        """Test validation with full format using dashes."""
        result = self.validator.validate("2024-04-15 14:30:45")

        self.assertTrue(result.success)

    def test_validate_date_only_slash(self):
        """Test validation with date-only format using slashes."""
        result = self.validator.validate("2024/04/15")

        self.assertTrue(result.success)

    def test_validate_date_only_dash(self):
        """Test validation with date-only format using dashes."""
        result = self.validator.validate("2024-04-15")

        self.assertTrue(result.success)

    def test_validate_none_value(self):
        """Test validation with None value."""
        result = self.validator.validate(None)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "DateTime cannot be None")

    def test_validate_non_string_value(self):
        """Test validation with non-string value."""
        result = self.validator.validate(20240415)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "DateTime must be a string")

    def test_validate_empty_string(self):
        """Test validation with empty string."""
        result = self.validator.validate("")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "DateTime cannot be empty")

    def test_validate_invalid_format(self):
        """Test validation with invalid format."""
        result = self.validator.validate("invalid_datetime")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid datetime format")
        self.assertIn("Expected formats", result.message)

    def test_validate_invalid_date_values(self):
        """Test validation with invalid date values."""
        result = self.validator.validate(
            "2024/13/32 25:70:80")  # Invalid month, day, hour, minute, second

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid datetime format")

    def test_validate_year_too_early(self):
        """Test validation with year too early."""
        result = self.validator.validate("1800/01/01")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "DateTime year out of reasonable range")

    def test_validate_year_too_late(self):
        """Test validation with year too late."""
        result = self.validator.validate("2300/01/01")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "DateTime year out of reasonable range")

    def test_validate_leap_year(self):
        """Test validation with leap year date."""
        result = self.validator.validate("2024/02/29")  # 2024 is a leap year

        self.assertTrue(result.success)

    def test_validate_non_leap_year(self):
        """Test validation with invalid leap year date."""
        result = self.validator.validate(
            "2023/02/29")  # 2023 is not a leap year

        self.assertFalse(result.success)

    def test_validate_midnight(self):
        """Test validation with midnight time."""
        result = self.validator.validate("2024/04/15 00:00:00")

        self.assertTrue(result.success)

    def test_validate_end_of_day(self):
        """Test validation with end of day time."""
        result = self.validator.validate("2024/04/15 23:59:59")

        self.assertTrue(result.success)

    def test_validate_with_spaces(self):
        """Test validation with leading/trailing spaces."""
        result = self.validator.validate("  2024/04/15 14:30:45  ")

        self.assertTrue(result.success)


class TestValidatorFactories(unittest.TestCase):
    """Test cases for validator factory functions."""

    def test_create_sps_timestamp_validator(self):
        """Test creating SPS timestamp validator."""
        validator = create_sps_timestamp_validator()

        # Test with valid input
        result = validator.validate("30000000")
        self.assertTrue(result.success)

        # Test with invalid input
        result = validator.validate("")
        self.assertFalse(result.success)

    def test_create_datetime_validator(self):
        """Test creating datetime validator."""
        validator = create_datetime_validator()

        # Test with valid input
        result = validator.validate("2024/04/15 14:30:45")
        self.assertTrue(result.success)

        # Test with invalid input
        result = validator.validate("")
        self.assertFalse(result.success)

    def test_composite_validator_behavior(self):
        """Test that factory returns composite validator."""
        timestamp_validator = create_sps_timestamp_validator()
        datetime_validator = create_datetime_validator()

        # Both should fail on empty string (from NonEmptyStringValidator)
        result1 = timestamp_validator.validate("")
        result2 = datetime_validator.validate("")

        self.assertFalse(result1.success)
        self.assertFalse(result2.success)

        # Both should fail on None (from specific validators)
        result3 = timestamp_validator.validate(None)
        result4 = datetime_validator.validate(None)

        self.assertFalse(result3.success)
        self.assertFalse(result4.success)


if __name__ == '__main__':
    unittest.main()
