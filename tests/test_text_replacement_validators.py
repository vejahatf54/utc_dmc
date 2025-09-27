"""
Unit tests for text replacement validators.
Tests input validation following Single Responsibility Principle.
"""

import unittest
import base64
import io
import pandas as pd
import tempfile
import os
from pathlib import Path
from validation.text_replacement_validators import (
    CsvContentValidator, DirectoryPathValidator, FileExtensionsValidator,
    TextReplacementInputValidator, SubstitutionDataValidator,
    create_csv_validator, create_directory_validator, create_extensions_validator,
    create_input_validator, create_substitution_validator
)


class TestCsvContentValidator(unittest.TestCase):
    """Test cases for CsvContentValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = CsvContentValidator()

        # Create sample CSV content
        csv_content = "old1,new1\nold2,new2\n"
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')
        self.valid_contents = f"data:text/csv;base64,{encoded_content}"

    def test_valid_csv_upload(self):
        """Test validation of valid CSV upload."""
        upload_data = {
            'contents': self.valid_contents,
            'filename': 'test.csv'
        }

        result = self.validator.validate(upload_data)

        self.assertTrue(result.success)
        self.assertIn("2 valid substitution pairs", result.message)

    def test_no_data(self):
        """Test validation with no data."""
        result = self.validator.validate(None)
        self.assertFalse(result.success)
        self.assertIn("No CSV data provided", result.error)

    def test_no_contents(self):
        """Test validation with no contents."""
        upload_data = {'filename': 'test.csv'}

        result = self.validator.validate(upload_data)

        self.assertFalse(result.success)
        self.assertIn("No file contents provided", result.error)

    def test_no_filename(self):
        """Test validation with no filename."""
        upload_data = {'contents': self.valid_contents}

        result = self.validator.validate(upload_data)

        self.assertFalse(result.success)
        self.assertIn("No filename provided", result.error)

    def test_wrong_file_extension(self):
        """Test validation with wrong file extension."""
        upload_data = {
            'contents': self.valid_contents,
            'filename': 'test.txt'
        }

        result = self.validator.validate(upload_data)

        self.assertFalse(result.success)
        self.assertIn("CSV file (.csv extension)", result.error)

    def test_invalid_csv_format(self):
        """Test validation with invalid CSV format."""
        csv_content = "single_column\n"
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')
        invalid_contents = f"data:text/csv;base64,{encoded_content}"

        upload_data = {
            'contents': invalid_contents,
            'filename': 'test.csv'
        }

        result = self.validator.validate(upload_data)

        self.assertFalse(result.success)
        self.assertIn("at least 2 columns", result.error)

    def test_empty_csv(self):
        """Test validation with empty CSV."""
        csv_content = ""
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')
        empty_contents = f"data:text/csv;base64,{encoded_content}"

        upload_data = {
            'contents': empty_contents,
            'filename': 'test.csv'
        }

        result = self.validator.validate(upload_data)

        self.assertFalse(result.success)
        self.assertIn("Error reading CSV file", result.error)

    def test_no_valid_substitutions(self):
        """Test validation with no valid substitution pairs."""
        csv_content = ",new1\n,new2\n"  # Empty old text
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')
        invalid_contents = f"data:text/csv;base64,{encoded_content}"

        upload_data = {
            'contents': invalid_contents,
            'filename': 'test.csv'
        }

        result = self.validator.validate(upload_data)

        self.assertFalse(result.success)
        self.assertIn("at least one valid substitution pair", result.error)


class TestDirectoryPathValidator(unittest.TestCase):
    """Test cases for DirectoryPathValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = DirectoryPathValidator()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test.txt"
        self.temp_file.write_text("content")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_directory(self):
        """Test validation of valid directory."""
        result = self.validator.validate(self.temp_dir)

        self.assertTrue(result.success)
        self.assertIn("Valid directory", result.message)

    def test_empty_path(self):
        """Test validation with empty path."""
        result = self.validator.validate("")

        self.assertFalse(result.success)
        self.assertIn("Directory path is required", result.error)

    def test_none_path(self):
        """Test validation with None path."""
        result = self.validator.validate(None)

        self.assertFalse(result.success)
        self.assertIn("Directory path is required", result.error)

    def test_non_string_path(self):
        """Test validation with non-string path."""
        result = self.validator.validate(123)

        self.assertFalse(result.success)
        self.assertIn("must be a string", result.error)

    def test_nonexistent_directory(self):
        """Test validation with nonexistent directory."""
        result = self.validator.validate("/nonexistent/path")

        self.assertFalse(result.success)
        self.assertIn("does not exist", result.error)

    def test_file_instead_of_directory(self):
        """Test validation with file instead of directory."""
        result = self.validator.validate(str(self.temp_file))

        self.assertFalse(result.success)
        self.assertIn("not a directory", result.error)


class TestFileExtensionsValidator(unittest.TestCase):
    """Test cases for FileExtensionsValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = FileExtensionsValidator()

    def test_valid_extensions(self):
        """Test validation of valid extensions."""
        result = self.validator.validate("txt,py,js")

        self.assertTrue(result.success)
        self.assertIn("Valid extensions: txt, py, js", result.message)

    def test_extensions_with_dots_and_asterisks(self):
        """Test validation cleans dots and asterisks."""
        result = self.validator.validate(".txt,*.py,js")

        self.assertTrue(result.success)
        self.assertIn("txt, py, js", result.message)

    def test_extensions_with_whitespace(self):
        """Test validation handles whitespace."""
        result = self.validator.validate("  txt  ,  py  ,  js  ")

        self.assertTrue(result.success)
        self.assertIn("txt, py, js", result.message)

    def test_empty_extensions(self):
        """Test validation with empty extensions."""
        result = self.validator.validate("")

        self.assertFalse(result.success)
        self.assertIn("File extensions are required", result.error)

    def test_none_extensions(self):
        """Test validation with None extensions."""
        result = self.validator.validate(None)

        self.assertFalse(result.success)
        self.assertIn("File extensions are required", result.error)

    def test_non_string_extensions(self):
        """Test validation with non-string extensions."""
        result = self.validator.validate(123)

        self.assertFalse(result.success)
        self.assertIn("must be a string", result.error)

    def test_no_valid_extensions_after_cleaning(self):
        """Test validation when no valid extensions remain after cleaning."""
        result = self.validator.validate(",,  ,  ")

        self.assertFalse(result.success)
        self.assertIn(
            "At least one valid file extension is required", result.error)

    def test_invalid_extension_characters(self):
        """Test validation with invalid extension characters."""
        result = self.validator.validate("txt,py@#$,js")

        self.assertFalse(result.success)
        self.assertIn("Invalid file extensions", result.error)


class TestSubstitutionDataValidator(unittest.TestCase):
    """Test cases for SubstitutionDataValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = SubstitutionDataValidator()

    def test_valid_csv_content(self):
        """Test validation of valid CSV content."""
        csv_content = "old1,new1\nold2,new2\n"
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')

        result = self.validator.validate(encoded_content)

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)
        self.assertEqual(result.data[0], ("old1", "new1"))
        self.assertEqual(result.data[1], ("old2", "new2"))

    def test_empty_content(self):
        """Test validation with empty content."""
        result = self.validator.validate("")

        self.assertFalse(result.success)
        self.assertIn("No CSV content provided", result.error)

    def test_none_content(self):
        """Test validation with None content."""
        result = self.validator.validate(None)

        self.assertFalse(result.success)
        self.assertIn("No CSV content provided", result.error)

    def test_invalid_base64(self):
        """Test validation with invalid base64 content."""
        result = self.validator.validate("invalid_base64!")

        self.assertFalse(result.success)
        self.assertIn("Error parsing CSV content", result.error)

    def test_csv_with_empty_old_text(self):
        """Test validation filters out rows with empty old text."""
        csv_content = "old1,new1\n,new2\nold3,new3\n"
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')

        result = self.validator.validate(encoded_content)

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)  # One row filtered out
        self.assertIn("1 invalid rows skipped", result.message)

    def test_csv_with_no_valid_pairs(self):
        """Test validation with no valid substitution pairs."""
        csv_content = ",new1\n,new2\n"
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')

        result = self.validator.validate(encoded_content)

        self.assertFalse(result.success)
        self.assertIn("No valid substitution pairs", result.error)


class TestTextReplacementInputValidator(unittest.TestCase):
    """Test cases for TextReplacementInputValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = TextReplacementInputValidator()
        self.temp_dir = tempfile.mkdtemp()

        csv_content = "old1,new1\nold2,new2\n"
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')
        valid_contents = f"data:text/csv;base64,{encoded_content}"

        self.valid_input = {
            'csv_data': {
                'contents': valid_contents,
                'filename': 'test.csv'
            },
            'directory': self.temp_dir,
            'extensions': 'txt,py,js'
        }

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_input(self):
        """Test validation of all valid inputs."""
        result = self.validator.validate(self.valid_input)

        self.assertTrue(result.success)
        self.assertIn("All inputs are valid", result.message)

    def test_no_input_data(self):
        """Test validation with no input data."""
        result = self.validator.validate(None)

        self.assertFalse(result.success)
        self.assertIn("No input data provided", result.error)

    def test_missing_csv_data(self):
        """Test validation with missing CSV data."""
        input_data = self.valid_input.copy()
        del input_data['csv_data']

        result = self.validator.validate(input_data)

        self.assertFalse(result.success)
        self.assertIn("CSV file is required", result.error)

    def test_missing_directory(self):
        """Test validation with missing directory."""
        input_data = self.valid_input.copy()
        del input_data['directory']

        result = self.validator.validate(input_data)

        self.assertFalse(result.success)
        self.assertIn("Target directory is required", result.error)

    def test_missing_extensions(self):
        """Test validation with missing extensions."""
        input_data = self.valid_input.copy()
        del input_data['extensions']

        result = self.validator.validate(input_data)

        self.assertFalse(result.success)
        self.assertIn("File extensions are required", result.error)

    def test_multiple_validation_errors(self):
        """Test validation with multiple errors."""
        input_data = {
            'csv_data': {'contents': 'invalid'},
            'directory': '/nonexistent',
            'extensions': ''
        }

        result = self.validator.validate(input_data)

        self.assertFalse(result.success)
        self.assertIn("CSV validation failed", result.error)
        self.assertIn("Directory validation failed", result.error)
        # Extensions validation should fail, but since it's empty, we expect a different message
        self.assertIn("File extensions are required", result.error)


class TestValidatorFactories(unittest.TestCase):
    """Test cases for validator factory functions."""

    def test_create_csv_validator(self):
        """Test CSV validator factory."""
        validator = create_csv_validator()
        self.assertIsInstance(validator, CsvContentValidator)

    def test_create_directory_validator(self):
        """Test directory validator factory."""
        validator = create_directory_validator()
        self.assertIsInstance(validator, DirectoryPathValidator)

    def test_create_extensions_validator(self):
        """Test extensions validator factory."""
        validator = create_extensions_validator()
        self.assertIsInstance(validator, FileExtensionsValidator)

    def test_create_input_validator(self):
        """Test input validator factory."""
        validator = create_input_validator()
        self.assertIsInstance(validator, TextReplacementInputValidator)

    def test_create_substitution_validator(self):
        """Test substitution validator factory."""
        validator = create_substitution_validator()
        self.assertIsInstance(validator, SubstitutionDataValidator)


if __name__ == '__main__':
    unittest.main()
