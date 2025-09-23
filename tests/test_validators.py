"""
Unit tests for validation components.
Tests input validators following Single Responsibility Principle.
"""

import unittest
from validation.input_validators import (
    FluidIdInputValidator,
    FluidNameInputValidator,
    NonEmptyStringValidator,
    CompositeValidator,
    create_fid_validator,
    create_fluid_name_validator
)


class TestFluidIdInputValidator(unittest.TestCase):
    """Test cases for FluidIdInputValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = FluidIdInputValidator()

    def test_valid_fid_input(self):
        """Test validation of valid FID inputs."""
        result = self.validator.validate("123")
        self.assertTrue(result.success)
        self.assertEqual(result.data, True)

    def test_zero_fid_input(self):
        """Test validation of zero FID input."""
        result = self.validator.validate("0")
        self.assertTrue(result.success)

    def test_fid_with_whitespace(self):
        """Test validation of FID with whitespace."""
        result = self.validator.validate("  123  ")
        self.assertTrue(result.success)

    def test_none_fid_input(self):
        """Test validation of None FID input."""
        result = self.validator.validate(None)
        self.assertFalse(result.success)
        self.assertIn("cannot be None", result.error)

    def test_empty_fid_input(self):
        """Test validation of empty FID input."""
        result = self.validator.validate("")
        self.assertFalse(result.success)
        self.assertIn("cannot be empty", result.error)

    def test_non_string_fid_input(self):
        """Test validation of non-string FID input."""
        result = self.validator.validate(123)
        self.assertFalse(result.success)
        self.assertIn("must be a string", result.error)

    def test_non_numeric_fid_input(self):
        """Test validation of non-numeric FID input."""
        result = self.validator.validate("abc")
        self.assertFalse(result.success)
        self.assertIn("must be numeric", result.error)

    def test_negative_fid_input(self):
        """Test validation of negative FID input."""
        result = self.validator.validate("-123")
        self.assertFalse(result.success)
        self.assertIn("must be non-negative", result.error)


class TestFluidNameInputValidator(unittest.TestCase):
    """Test cases for FluidNameInputValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = FluidNameInputValidator()

    def test_valid_fluid_name_input(self):
        """Test validation of valid fluid name inputs."""
        result = self.validator.validate("ABC")
        self.assertTrue(result.success)

    def test_fluid_name_with_numbers(self):
        """Test validation of fluid name with numbers."""
        result = self.validator.validate("A1B2")
        self.assertTrue(result.success)

    def test_fluid_name_with_spaces(self):
        """Test validation of fluid name with spaces."""
        result = self.validator.validate("A B C")
        self.assertTrue(result.success)

    def test_lowercase_fluid_name(self):
        """Test validation of lowercase fluid name."""
        result = self.validator.validate("abc")
        self.assertTrue(result.success)

    def test_none_fluid_name_input(self):
        """Test validation of None fluid name input."""
        result = self.validator.validate(None)
        self.assertFalse(result.success)
        self.assertIn("cannot be None", result.error)

    def test_empty_fluid_name_input(self):
        """Test validation of empty fluid name input."""
        result = self.validator.validate("")
        self.assertFalse(result.success)
        self.assertIn("cannot be empty", result.error)

    def test_non_string_fluid_name_input(self):
        """Test validation of non-string fluid name input."""
        result = self.validator.validate(123)
        self.assertFalse(result.success)
        self.assertIn("must be a string", result.error)

    def test_invalid_character_in_fluid_name(self):
        """Test validation of fluid name with invalid characters."""
        result = self.validator.validate("A@B")
        self.assertFalse(result.success)
        self.assertIn("Invalid character '@'", result.error)

    def test_fluid_name_with_special_characters(self):
        """Test validation of fluid name with various invalid special characters."""
        invalid_chars = ['!', '@', '#', '$', '%',
                         '^', '&', '*', '(', ')', '-', '+', '=']

        for char in invalid_chars:
            with self.subTest(char=char):
                result = self.validator.validate(f"A{char}B")
                self.assertFalse(result.success)
                self.assertIn(f"Invalid character '{char}'", result.error)


class TestNonEmptyStringValidator(unittest.TestCase):
    """Test cases for NonEmptyStringValidator."""

    def test_valid_string(self):
        """Test validation of valid non-empty string."""
        validator = NonEmptyStringValidator("TestField")
        result = validator.validate("test")
        self.assertTrue(result.success)

    def test_string_with_whitespace(self):
        """Test validation of string with only content after trim."""
        validator = NonEmptyStringValidator("TestField")
        result = validator.validate("  test  ")
        self.assertTrue(result.success)

    def test_none_value(self):
        """Test validation of None value."""
        validator = NonEmptyStringValidator("TestField")
        result = validator.validate(None)
        self.assertFalse(result.success)
        self.assertIn("TestField cannot be None", result.error)

    def test_empty_string(self):
        """Test validation of empty string."""
        validator = NonEmptyStringValidator("TestField")
        result = validator.validate("")
        self.assertFalse(result.success)
        self.assertIn("TestField cannot be empty", result.error)

    def test_whitespace_only_string(self):
        """Test validation of whitespace-only string."""
        validator = NonEmptyStringValidator("TestField")
        result = validator.validate("   ")
        self.assertFalse(result.success)
        self.assertIn("TestField cannot be empty", result.error)

    def test_non_string_value(self):
        """Test validation of non-string value."""
        validator = NonEmptyStringValidator("TestField")
        result = validator.validate(123)
        self.assertFalse(result.success)
        self.assertIn("TestField must be a string", result.error)

    def test_custom_field_name(self):
        """Test that custom field name appears in error messages."""
        validator = NonEmptyStringValidator("CustomField")
        result = validator.validate(None)
        self.assertIn("CustomField", result.error)
        self.assertIn("customfield", result.message.lower())


class TestCompositeValidator(unittest.TestCase):
    """Test cases for CompositeValidator."""

    def test_all_validators_pass(self):
        """Test when all validators pass."""
        validator1 = NonEmptyStringValidator("Field1")
        validator2 = FluidIdInputValidator()
        composite = CompositeValidator(validator1, validator2)

        result = composite.validate("123")
        self.assertTrue(result.success)

    def test_first_validator_fails(self):
        """Test when first validator fails."""
        validator1 = NonEmptyStringValidator("Field1")
        validator2 = FluidIdInputValidator()
        composite = CompositeValidator(validator1, validator2)

        result = composite.validate(None)
        self.assertFalse(result.success)
        self.assertIn("Field1 cannot be None", result.error)

    def test_second_validator_fails(self):
        """Test when second validator fails."""
        validator1 = NonEmptyStringValidator("Field1")
        validator2 = FluidIdInputValidator()
        composite = CompositeValidator(validator1, validator2)

        result = composite.validate("abc")  # Non-numeric
        self.assertFalse(result.success)
        self.assertIn("must be numeric", result.error)

    def test_empty_composite_validator(self):
        """Test composite validator with no validators."""
        composite = CompositeValidator()
        result = composite.validate("anything")
        self.assertTrue(result.success)


class TestValidatorFactories(unittest.TestCase):
    """Test cases for validator factory functions."""

    def test_create_fid_validator(self):
        """Test FID validator factory."""
        validator = create_fid_validator()
        self.assertIsInstance(validator, CompositeValidator)

        # Test valid input
        result = validator.validate("123")
        self.assertTrue(result.success)

        # Test invalid input
        result = validator.validate("abc")
        self.assertFalse(result.success)

    def test_create_fluid_name_validator(self):
        """Test fluid name validator factory."""
        validator = create_fluid_name_validator()
        self.assertIsInstance(validator, CompositeValidator)

        # Test valid input
        result = validator.validate("ABC")
        self.assertTrue(result.success)

        # Test invalid input
        result = validator.validate("A@B")
        self.assertFalse(result.success)


if __name__ == '__main__':
    unittest.main()
