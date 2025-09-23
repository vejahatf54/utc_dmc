"""
Unit tests for domain models.
Tests the FluidId and FluidName value objects.
"""

import unittest
from domain.fluid_models import FluidId, FluidName, ConversionConstants


class TestFluidId(unittest.TestCase):
    """Test cases for FluidId value object."""

    def test_valid_fid_creation(self):
        """Test creating valid FluidId objects."""
        fid = FluidId("123")
        self.assertEqual(fid.value, "123")
        self.assertEqual(fid.numeric_value, 123)

    def test_fid_with_whitespace(self):
        """Test FluidId with leading/trailing whitespace."""
        fid = FluidId("  123  ")
        self.assertEqual(fid.value, "123")
        self.assertEqual(fid.numeric_value, 123)

    def test_zero_fid(self):
        """Test FluidId with zero value."""
        fid = FluidId("0")
        self.assertEqual(fid.value, "0")
        self.assertEqual(fid.numeric_value, 0)

    def test_empty_fid_raises_error(self):
        """Test that empty FID raises ValueError."""
        with self.assertRaises(ValueError) as context:
            FluidId("")
        self.assertIn("cannot be empty", str(context.exception))

    def test_non_numeric_fid_raises_error(self):
        """Test that non-numeric FID raises ValueError."""
        with self.assertRaises(ValueError) as context:
            FluidId("abc")
        self.assertIn("valid numeric value", str(context.exception))

    def test_negative_fid_raises_error(self):
        """Test that negative FID raises ValueError."""
        with self.assertRaises(ValueError) as context:
            FluidId("-123")
        self.assertIn("non-negative", str(context.exception))

    def test_non_string_fid_raises_error(self):
        """Test that non-string FID raises ValueError."""
        with self.assertRaises(ValueError) as context:
            FluidId(123)
        self.assertIn("must be a string", str(context.exception))

    def test_fid_equality(self):
        """Test FluidId equality comparison."""
        fid1 = FluidId("123")
        fid2 = FluidId("123")
        fid3 = FluidId("456")

        self.assertEqual(fid1, fid2)
        self.assertNotEqual(fid1, fid3)

    def test_fid_hash(self):
        """Test FluidId hashing for use in sets/dicts."""
        fid1 = FluidId("123")
        fid2 = FluidId("123")

        self.assertEqual(hash(fid1), hash(fid2))

        # Test that equal objects have the same hash
        fid_set = {fid1, fid2}
        self.assertEqual(len(fid_set), 1)


class TestFluidName(unittest.TestCase):
    """Test cases for FluidName value object."""

    def test_valid_fluid_name_creation(self):
        """Test creating valid FluidName objects."""
        name = FluidName("ABC")
        self.assertEqual(name.value, "ABC")
        self.assertEqual(name.normalized_value, "ABC")

    def test_fluid_name_case_conversion(self):
        """Test that fluid names are converted to uppercase."""
        name = FluidName("abc")
        self.assertEqual(name.value, "ABC")

    def test_fluid_name_with_spaces(self):
        """Test fluid names with spaces."""
        name = FluidName("A B C")
        self.assertEqual(name.value, "A B C")
        self.assertEqual(name.normalized_value, "A B C")

    def test_single_character_padding(self):
        """Test that single character names are padded with spaces."""
        name = FluidName("A")
        self.assertEqual(name.value, "A")
        self.assertEqual(name.normalized_value, "A  ")  # Padded with 2 spaces

    def test_two_character_padding(self):
        """Test that two character names are padded with one space."""
        name = FluidName("AB")
        self.assertEqual(name.value, "AB")
        self.assertEqual(name.normalized_value, "AB ")  # Padded with 1 space

    def test_three_character_no_padding(self):
        """Test that three+ character names are not padded."""
        name = FluidName("ABC")
        self.assertEqual(name.value, "ABC")
        self.assertEqual(name.normalized_value, "ABC")  # No padding

    def test_empty_fluid_name_raises_error(self):
        """Test that empty fluid name raises ValueError."""
        with self.assertRaises(ValueError) as context:
            FluidName("")
        self.assertIn("cannot be empty", str(context.exception))

    def test_invalid_character_raises_error(self):
        """Test that invalid characters raise ValueError."""
        with self.assertRaises(ValueError) as context:
            FluidName("A@B")
        self.assertIn("Invalid character '@'", str(context.exception))

    def test_non_string_fluid_name_raises_error(self):
        """Test that non-string fluid name raises ValueError."""
        with self.assertRaises(ValueError) as context:
            FluidName(123)
        self.assertIn("must be a string", str(context.exception))

    def test_get_character_indices(self):
        """Test getting character indices for conversion."""
        name = FluidName("A")  # Will be normalized to "A  "
        indices = name.get_character_indices()

        # A = index 11, space = index 10
        expected = [11, 10, 10]
        self.assertEqual(indices, expected)

    def test_fluid_name_equality(self):
        """Test FluidName equality comparison."""
        name1 = FluidName("ABC")
        name2 = FluidName("abc")  # Should be converted to uppercase
        name3 = FluidName("DEF")

        self.assertEqual(name1, name2)
        self.assertNotEqual(name1, name3)

    def test_fluid_name_length(self):
        """Test fluid name length property."""
        name = FluidName("ABC")
        self.assertEqual(name.length, 3)


class TestConversionConstants(unittest.TestCase):
    """Test cases for ConversionConstants."""

    def test_basis_value(self):
        """Test that BASIS is 37."""
        self.assertEqual(ConversionConstants.BASIS, 37)

    def test_base_digits_length(self):
        """Test that BASE_DIGITS has 37 elements."""
        self.assertEqual(len(ConversionConstants.BASE_DIGITS), 37)

    def test_base_digits_order(self):
        """Test that BASE_DIGITS starts with expected characters."""
        expected_start = ['0', '1', '2', '3', '4',
                          '5', '6', '7', '8', '9', ' ', 'A']
        actual_start = ConversionConstants.BASE_DIGITS[:12]
        self.assertEqual(actual_start, expected_start)

    def test_get_system_info(self):
        """Test get_system_info returns proper dictionary."""
        info = ConversionConstants.get_system_info()

        self.assertIsInstance(info, dict)
        self.assertEqual(info["basis"], 37)
        self.assertIn("characters", info)
        self.assertIn("description", info)
        self.assertIn("examples", info)
        self.assertIn("rules", info)

        # Test examples structure
        self.assertIsInstance(info["examples"], list)
        self.assertTrue(len(info["examples"]) > 0)

        # Test rules structure
        self.assertIsInstance(info["rules"], list)
        self.assertTrue(len(info["rules"]) > 0)


if __name__ == '__main__':
    unittest.main()
