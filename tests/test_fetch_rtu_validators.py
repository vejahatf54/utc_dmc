"""
Unit tests for RTU fetch data validators.
Tests validation logic following clean architecture principles.
"""

import unittest
import tempfile
from datetime import date
from pathlib import Path
import os

from validation.rtu_validators import (
    RtuDateInputValidator, RtuLineSelectionValidator, 
    RtuOutputDirectoryValidator, CompositeRtuValidator,
    create_rtu_date_validator, create_rtu_line_validator, 
    create_rtu_directory_validator, create_composite_rtu_validator
)
from core.interfaces import Result


class TestRtuDateInputValidator(unittest.TestCase):
    """Test RTU date input validator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = RtuDateInputValidator()

    def test_valid_date_string(self):
        """Test valid date string validation."""
        result = self.validator.validate("2024-01-15")
        self.assertTrue(result.success)
        self.assertEqual(result.data.value, date(2024, 1, 15))

    def test_valid_date_object(self):
        """Test valid date object validation."""
        test_date = date(2024, 1, 15)
        result = self.validator.validate(test_date)
        self.assertTrue(result.success)
        self.assertEqual(result.data.value, test_date)

    def test_invalid_date_format(self):
        """Test invalid date format."""
        result = self.validator.validate("2024/01/15")
        self.assertFalse(result.success)
        self.assertIn("Invalid date format", result.error)

    def test_future_date_validation(self):
        """Test future date validation."""
        from datetime import datetime, timedelta
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        result = self.validator.validate(future_date)
        self.assertFalse(result.success)

    def test_too_old_date_validation(self):
        """Test too old date validation."""
        result = self.validator.validate("1999-01-01")
        self.assertFalse(result.success)

    def test_none_value(self):
        """Test None value validation."""
        result = self.validator.validate(None)
        self.assertFalse(result.success)
        self.assertIn("Date value cannot be None", result.error)

    def test_empty_string(self):
        """Test empty string validation."""
        result = self.validator.validate("")
        self.assertFalse(result.success)
        self.assertIn("Invalid date format", result.error)

    def test_invalid_type(self):
        """Test invalid type validation."""
        result = self.validator.validate(123)
        self.assertFalse(result.success)
        self.assertIn("Invalid date type", result.error)


class TestRtuLineSelectionValidator(unittest.TestCase):
    """Test RTU line selection validator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = RtuLineSelectionValidator()

    def test_valid_line_list(self):
        """Test valid line list validation."""
        lines = ["l01", "l02", "l03"]
        result = self.validator.validate(lines)
        self.assertTrue(result.success)
        self.assertEqual(result.data.line_ids, lines)

    def test_single_line(self):
        """Test single line validation."""
        result = self.validator.validate(["l01"])
        self.assertTrue(result.success)
        self.assertEqual(result.data.count, 1)

    def test_empty_list(self):
        """Test empty list validation."""
        result = self.validator.validate([])
        self.assertFalse(result.success)
        self.assertIn("At least one pipeline line must be selected", result.error)

    def test_none_value(self):
        """Test None value validation."""
        result = self.validator.validate(None)
        self.assertFalse(result.success)

    def test_non_list_type(self):
        """Test non-list type validation."""
        result = self.validator.validate("l01")
        self.assertFalse(result.success)

    def test_empty_line_string(self):
        """Test empty line string in list."""
        result = self.validator.validate(["l01", "", "l02"])
        self.assertFalse(result.success)

    def test_invalid_line_types(self):
        """Test invalid line types in list."""
        result = self.validator.validate(["l01", 1, "l02"])
        self.assertFalse(result.success)
        self.assertIn("Line ID must be a string", result.error)


class TestRtuOutputDirectoryValidator(unittest.TestCase):
    """Test RTU output directory validator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = RtuOutputDirectoryValidator()

    def test_valid_existing_directory(self):
        """Test valid existing directory validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.validator.validate(temp_dir)
            self.assertTrue(result.success)
            self.assertTrue(result.data.exists)

    def test_valid_new_directory(self):
        """Test valid new directory validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "new_folder")
            result = self.validator.validate(new_dir)
            self.assertTrue(result.success)

    def test_path_object_input(self):
        """Test Path object input validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path_obj = Path(temp_dir)
            result = self.validator.validate(path_obj)
            self.assertTrue(result.success)

    def test_none_value(self):
        """Test None value validation."""
        result = self.validator.validate(None)
        self.assertFalse(result.success)

    def test_empty_string(self):
        """Test empty string validation."""
        result = self.validator.validate("")
        self.assertFalse(result.success)
        self.assertIn("Output directory cannot be empty", result.error)

    def test_invalid_type(self):
        """Test invalid type validation."""
        result = self.validator.validate(123)
        self.assertFalse(result.success)


class TestCompositeRtuValidator(unittest.TestCase):
    """Test composite RTU validator."""

    def setUp(self):
        """Set up test fixtures."""
        self.date_validator = RtuDateInputValidator()
        self.line_validator = RtuLineSelectionValidator()
        self.output_validator = RtuOutputDirectoryValidator()
        
        self.composite = CompositeRtuValidator(
            self.date_validator,
            None,  # date_range_validator
            self.line_validator,
            self.output_validator
        )

    def test_valid_all_inputs(self):
        """Test validation when all inputs are valid."""
        with tempfile.TemporaryDirectory() as temp_dir:
            inputs = {
                'mode': 'range',
                'start_date': "2024-01-01",
                'end_date': "2024-01-31",
                'selected_lines': ["l01", "l02"],
                'output_directory': temp_dir
            }
            
            result = self.composite.validate_all(inputs)
            self.assertTrue(result.success)
            
            validated = result.data
            self.assertIn('date_range', validated)
            self.assertIn('line_selection', validated)
            self.assertIn('output_directory', validated)

    def test_partial_validation_failure(self):
        """Test validation when some inputs fail."""
        inputs = {
            'mode': 'range',
            'start_date': "invalid-date",
            'end_date': "2024-01-31",
            'selected_lines': ["l01", "l02"],
            'output_directory': None
        }
        
        result = self.composite.validate_all(inputs)
        self.assertFalse(result.success)
        self.assertIn("date format", result.error)

    def test_date_range_validation(self):
        """Test date range validation with invalid order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            inputs = {
                'mode': 'range',
                'start_date': "2024-01-31",
                'end_date': "2024-01-01",
                'selected_lines': ["l01", "l02"],
                'output_directory': temp_dir
            }
            
            result = self.composite.validate_all(inputs)
            self.assertFalse(result.success)
            self.assertIn("Start date cannot be after end date", result.error)

    def test_single_date_validation(self):
        """Test validation with only start date (single date mode)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            inputs = {
                'mode': 'single',
                'single_date': "2024-01-15",
                'selected_lines': ["l01", "l02"],
                'output_directory': temp_dir
            }
            
            result = self.composite.validate_all(inputs)
            self.assertTrue(result.success)
            
            validated = result.data
            self.assertTrue(validated['date_range'].is_single_date)

    def test_validate_individual_components(self):
        """Test individual component validation methods."""
        # Test date validation
        date_result = self.composite.validate_dates("2024-01-01", "2024-01-31")
        self.assertTrue(date_result.success)
        
        # Test line validation
        line_result = self.composite.validate_lines(["l01", "l02"])
        self.assertTrue(line_result.success)
        
        # Test directory validation
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_result = self.composite.validate_directory(temp_dir)
            self.assertTrue(dir_result.success)


class TestValidatorFactories(unittest.TestCase):
    """Test validator factory functions."""

    def test_create_date_validator(self):
        """Test date validator factory."""
        validator = create_rtu_date_validator()
        self.assertIsInstance(validator, RtuDateInputValidator)

    def test_create_line_validator(self):
        """Test line validator factory."""
        validator = create_rtu_line_validator()
        self.assertIsInstance(validator, RtuLineSelectionValidator)

    def test_create_output_validator(self):
        """Test output validator factory."""
        validator = create_rtu_directory_validator()
        self.assertIsInstance(validator, RtuOutputDirectoryValidator)

    def test_create_composite_validator(self):
        """Test composite validator factory."""
        validator = create_composite_rtu_validator()
        self.assertIsInstance(validator, CompositeRtuValidator)
        
        # Test that it works
        with tempfile.TemporaryDirectory() as temp_dir:
            inputs = {
                'mode': 'single',
                'single_date': "2024-01-15",
                'selected_lines': ["l01"],
                'output_directory': temp_dir
            }
            result = validator.validate_all(inputs)
            self.assertTrue(result.success)


if __name__ == '__main__':
    unittest.main()