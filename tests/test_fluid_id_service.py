"""
Unit tests for the refactored Fluid ID Converter service.
Tests the service following SOLID principles and dependency injection.
"""

import unittest
from unittest.mock import Mock, patch
from services.fluid_id_service import FluidIdConverterService, LegacyFluidIdConverterService
from core.interfaces import IValidator, Result


class TestFluidIdConverterService(unittest.TestCase):
    """Test cases for FluidIdConverterService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = FluidIdConverterService()

    def test_fid_to_fluid_name_valid_input(self):
        """Test converting valid FID to fluid name."""
        result = self.service.fid_to_fluid_name("16292")
        self.assertTrue(result.success)
        self.assertEqual(result.data, "AWB")
        self.assertIn(
            "Converted FID '16292' to Fluid Name 'AWB'", result.message)

    def test_fid_to_fluid_name_zero(self):
        """Test converting zero FID to fluid name."""
        result = self.service.fid_to_fluid_name("0")
        self.assertTrue(result.success)
        self.assertEqual(result.data, "0")

    def test_fid_to_fluid_name_invalid_input(self):
        """Test converting invalid FID input."""
        result = self.service.fid_to_fluid_name("abc")
        self.assertFalse(result.success)
        self.assertIn("must be numeric", result.error)

    def test_fid_to_fluid_name_negative_input(self):
        """Test converting negative FID input."""
        result = self.service.fid_to_fluid_name("-123")
        self.assertFalse(result.success)
        self.assertIn("must be non-negative", result.error)

    def test_fid_to_fluid_name_empty_input(self):
        """Test converting empty FID input."""
        result = self.service.fid_to_fluid_name("")
        self.assertFalse(result.success)
        self.assertIn("cannot be empty", result.error)

    def test_fluid_name_to_fid_valid_input(self):
        """Test converting valid fluid name to FID."""
        result = self.service.fluid_name_to_fid("AWB")
        self.assertTrue(result.success)
        self.assertEqual(result.data, "16292")
        self.assertIn(
            "Converted Fluid Name 'AWB' to FID '16292'", result.message)

    def test_fluid_name_to_fid_single_character(self):
        """Test converting single character fluid name to FID."""
        result = self.service.fluid_name_to_fid("A")
        self.assertTrue(result.success)
        # Single 'A' gets padded to 'A  ' which should convert to a specific FID
        self.assertIsInstance(result.data, str)
        self.assertTrue(result.data.isdigit())

    def test_fluid_name_to_fid_with_spaces(self):
        """Test converting fluid name with spaces to FID."""
        result = self.service.fluid_name_to_fid("A B")
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, str)
        self.assertTrue(result.data.isdigit())

    def test_fluid_name_to_fid_invalid_character(self):
        """Test converting fluid name with invalid character."""
        result = self.service.fluid_name_to_fid("A@B")
        self.assertFalse(result.success)
        self.assertIn("Invalid character '@'", result.error)

    def test_fluid_name_to_fid_empty_input(self):
        """Test converting empty fluid name input."""
        result = self.service.fluid_name_to_fid("")
        self.assertFalse(result.success)
        self.assertIn("cannot be empty", result.error)

    def test_get_system_info(self):
        """Test getting system information."""
        result = self.service.get_system_info()
        self.assertTrue(result.success)

        info = result.data
        self.assertIsInstance(info, dict)
        self.assertEqual(info["basis"], 37)
        self.assertIn("characters", info)
        self.assertIn("description", info)
        self.assertIn("examples", info)
        self.assertIn("rules", info)

    def test_generic_convert_with_numeric_input(self):
        """Test generic convert method with numeric input."""
        result = self.service.convert("16292")
        self.assertTrue(result.success)
        self.assertEqual(result.data, "AWB")

    def test_generic_convert_with_alphabetic_input(self):
        """Test generic convert method with alphabetic input."""
        result = self.service.convert("AWB")
        self.assertTrue(result.success)
        self.assertEqual(result.data, "16292")

    def test_generic_convert_with_invalid_input(self):
        """Test generic convert method with invalid input."""
        result = self.service.convert(123)  # Non-string
        self.assertFalse(result.success)
        self.assertIn("Input must be a string", result.error)

    def test_bidirectional_conversion(self):
        """Test that conversion is truly bidirectional."""
        # Test FID -> Name -> FID
        fid_to_name = self.service.fid_to_fluid_name("16292")
        self.assertTrue(fid_to_name.success)

        name_to_fid = self.service.fluid_name_to_fid(fid_to_name.data)
        self.assertTrue(name_to_fid.success)
        self.assertEqual(name_to_fid.data, "16292")

        # Test Name -> FID -> Name
        name_to_fid2 = self.service.fluid_name_to_fid("ABC")
        self.assertTrue(name_to_fid2.success)

        fid_to_name2 = self.service.fid_to_fluid_name(name_to_fid2.data)
        self.assertTrue(fid_to_name2.success)
        self.assertEqual(fid_to_name2.data, "ABC")


class TestFluidIdConverterServiceWithMockValidators(unittest.TestCase):
    """Test cases for FluidIdConverterService with mocked validators."""

    def test_with_custom_validators(self):
        """Test service with custom injected validators."""
        # Create mock validators
        mock_fid_validator = Mock()
        mock_fid_validator.validate.return_value = Result.ok(True, "Valid FID")

        mock_name_validator = Mock()
        mock_name_validator.validate.return_value = Result.ok(
            True, "Valid name")

        # Create service with mocked validators
        service = FluidIdConverterService(
            mock_fid_validator, mock_name_validator)

        # Test FID conversion
        result = service.fid_to_fluid_name("123")
        self.assertTrue(result.success)
        mock_fid_validator.validate.assert_called_once_with("123")

        # Test fluid name conversion
        result = service.fluid_name_to_fid("ABC")
        self.assertTrue(result.success)
        mock_name_validator.validate.assert_called_once_with("ABC")

    def test_with_failing_validator(self):
        """Test service with failing validator."""
        # Create mock validator that fails
        mock_fid_validator = Mock()
        mock_fid_validator.validate.return_value = Result.fail(
            "Validation failed", "Invalid input")

        mock_name_validator = Mock()
        mock_name_validator.validate.return_value = Result.ok(
            True, "Valid name")

        # Create service with mocked validators
        service = FluidIdConverterService(
            mock_fid_validator, mock_name_validator)

        # Test that validation failure is properly handled
        result = service.fid_to_fluid_name("123")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Validation failed")
        self.assertEqual(result.message, "Invalid input")


class TestLegacyFluidIdConverterService(unittest.TestCase):
    """Test cases for LegacyFluidIdConverterService wrapper."""

    def setUp(self):
        """Set up test fixtures."""
        self.legacy_service = LegacyFluidIdConverterService()

    def test_convert_fid_to_fluid_name_success(self):
        """Test legacy FID to fluid name conversion success."""
        result = self.legacy_service.convert_fid_to_fluid_name("16292")

        self.assertIsInstance(result, dict)
        self.assertTrue(result["success"])
        self.assertEqual(result["fluid_name"], "AWB")
        self.assertIn("message", result)

    def test_convert_fid_to_fluid_name_failure(self):
        """Test legacy FID to fluid name conversion failure."""
        result = self.legacy_service.convert_fid_to_fluid_name("abc")

        self.assertIsInstance(result, dict)
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIn("message", result)

    def test_convert_fluid_name_to_fid_success(self):
        """Test legacy fluid name to FID conversion success."""
        result = self.legacy_service.convert_fluid_name_to_fid("AWB")

        self.assertIsInstance(result, dict)
        self.assertTrue(result["success"])
        self.assertEqual(result["fid"], "16292")
        self.assertIn("message", result)

    def test_convert_fluid_name_to_fid_failure(self):
        """Test legacy fluid name to FID conversion failure."""
        result = self.legacy_service.convert_fluid_name_to_fid("A@B")

        self.assertIsInstance(result, dict)
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIn("message", result)

    def test_get_conversion_info(self):
        """Test legacy get conversion info."""
        result = self.legacy_service.get_conversion_info()

        self.assertIsInstance(result, dict)
        self.assertTrue(result["success"])
        self.assertIn("system_info", result)
        self.assertIn("message", result)

        system_info = result["system_info"]
        self.assertEqual(system_info["basis"], 37)


if __name__ == '__main__':
    unittest.main()
