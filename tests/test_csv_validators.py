"""
Unit tests for CSV to RTU validators.
Tests input validation following Single Responsibility Principle.
"""

import unittest
import tempfile
import os
import pandas as pd
from unittest.mock import patch, MagicMock

from validation.csv_validators import (
    CsvFilePathValidator, CsvFileSizeValidator, CsvStructureValidator,
    CsvTimestampValidator, OutputDirectoryValidator, CsvContentValidator,
    CompositeValidator, CsvToRtuValidator,
    create_csv_file_validator, create_output_directory_validator,
    create_file_upload_validator
)
from domain.csv_rtu_models import ConversionConstants


class TestCsvFilePathValidator(unittest.TestCase):
    """Test CsvFilePathValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = CsvFilePathValidator()

        # Create a temporary CSV file for testing
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False)
        self.temp_file.write(
            "timestamp,tag1,tag2\n2023-01-01 12:00:00,1.0,2.0\n")
        self.temp_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_valid_file_path(self):
        """Test validation with valid file path."""
        result = self.validator.validate(self.temp_file.name)

        self.assertTrue(result.success)
        self.assertIn("File path is valid", result.message)

    def test_none_value(self):
        """Test validation with None value."""
        result = self.validator.validate(None)

        self.assertFalse(result.success)
        self.assertIn("File path cannot be None", result.error)

    def test_non_string_value(self):
        """Test validation with non-string value."""
        result = self.validator.validate(123)

        self.assertFalse(result.success)
        self.assertIn("File path must be a string", result.error)

    def test_empty_string(self):
        """Test validation with empty string."""
        result = self.validator.validate("")

        self.assertFalse(result.success)
        self.assertIn("File path cannot be empty", result.error)

    def test_non_existent_file(self):
        """Test validation with non-existent file."""
        result = self.validator.validate("/path/that/does/not/exist.csv")

        self.assertFalse(result.success)
        self.assertIn("File does not exist", result.error)

    def test_unsupported_extension(self):
        """Test validation with unsupported file extension."""
        # Create temp file with wrong extension
        temp_txt = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False)
        temp_txt.write("some content")
        temp_txt.close()

        try:
            result = self.validator.validate(temp_txt.name)

            self.assertFalse(result.success)
            self.assertIn("Unsupported file extension", result.error)
        finally:
            os.unlink(temp_txt.name)


class TestCsvFileSizeValidator(unittest.TestCase):
    """Test CsvFileSizeValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = CsvFileSizeValidator(
            max_size_bytes=1024)  # 1KB limit for testing

    def test_valid_file_size_from_path(self):
        """Test validation with valid file size from path."""
        # Create small temp file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False)
        temp_file.write("small content")
        temp_file.close()

        try:
            result = self.validator.validate(temp_file.name)

            self.assertTrue(result.success)
            self.assertIn("File size is valid", result.message)
        finally:
            os.unlink(temp_file.name)

    def test_valid_file_size_from_value(self):
        """Test validation with valid file size value."""
        result = self.validator.validate(512)  # 512 bytes

        self.assertTrue(result.success)
        self.assertIn("File size is valid", result.message)

    def test_file_too_large(self):
        """Test validation with file too large."""
        result = self.validator.validate(2048)  # 2KB > 1KB limit

        self.assertFalse(result.success)
        self.assertIn("File too large", result.error)

    def test_empty_file(self):
        """Test validation with empty file."""
        result = self.validator.validate(0)

        self.assertFalse(result.success)
        self.assertIn("Empty file", result.error)

    def test_negative_size(self):
        """Test validation with negative size."""
        result = self.validator.validate(-1)

        self.assertFalse(result.success)
        self.assertIn("Invalid file size", result.error)

    def test_non_existent_file_path(self):
        """Test validation with non-existent file path."""
        result = self.validator.validate("/path/that/does/not/exist.csv")

        self.assertFalse(result.success)
        self.assertIn("File does not exist", result.error)

    def test_invalid_input_type(self):
        """Test validation with invalid input type."""
        result = self.validator.validate(
            [1, 2, 3])  # List is not a valid input type

        self.assertFalse(result.success)
        self.assertIn("Invalid input type", result.error)


class TestCsvStructureValidator(unittest.TestCase):
    """Test CsvStructureValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = CsvStructureValidator()

    def test_valid_structure_from_dataframe(self):
        """Test validation with valid DataFrame structure."""
        df = pd.DataFrame({
            'timestamp': ['2023-01-01 12:00:00', '2023-01-01 12:01:00'],
            'tag1': [1.0, 2.0],
            'tag2': [3.0, 4.0]
        })

        result = self.validator.validate(df)

        self.assertTrue(result.success)
        self.assertIn("CSV structure is valid", result.message)

    def test_valid_structure_from_file(self):
        """Test validation with valid CSV file structure."""
        # Create temp CSV file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False)
        temp_file.write("timestamp,tag1,tag2\n2023-01-01 12:00:00,1.0,2.0\n")
        temp_file.close()

        try:
            result = self.validator.validate(temp_file.name)

            self.assertTrue(result.success)
            self.assertIn("CSV structure is valid", result.message)
        finally:
            os.unlink(temp_file.name)

    def test_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        df = pd.DataFrame()

        result = self.validator.validate(df)

        self.assertFalse(result.success)
        self.assertIn("Empty CSV file", result.error)

    def test_insufficient_columns(self):
        """Test validation with insufficient columns."""
        df = pd.DataFrame({'timestamp': ['2023-01-01 12:00:00']})

        result = self.validator.validate(df)

        self.assertFalse(result.success)
        self.assertIn("Insufficient columns", result.error)

    def test_too_many_columns(self):
        """Test validation with too many columns."""
        # Create DataFrame with more than MAX_COLUMNS
        columns = ['timestamp'] + \
            [f'tag{i}' for i in range(ConversionConstants.MAX_COLUMNS)]
        data = {col: [1.0] for col in columns}
        df = pd.DataFrame(data)

        result = self.validator.validate(df)

        self.assertFalse(result.success)
        self.assertIn("Too many columns", result.error)

    def test_empty_column_names(self):
        """Test validation with empty column names."""
        df = pd.DataFrame({
            'timestamp': ['2023-01-01 12:00:00'],
            '': [1.0],  # Empty column name
            'tag2': [2.0]
        })

        result = self.validator.validate(df)

        self.assertFalse(result.success)
        self.assertIn("Empty column names", result.error)

    def test_invalid_csv_file(self):
        """Test validation with invalid CSV file."""
        # Create temp file with invalid CSV content that pandas cannot parse
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False)
        # Write malformed CSV with unescaped quotes and special characters
        temp_file.write(
            'invalid"quotes"in,middle,of"field\n"unclosed,quote,field\nvalid,data,here')
        temp_file.close()

        try:
            result = self.validator.validate(temp_file.name)

            # Should handle parsing errors gracefully
            self.assertFalse(result.success)
            self.assertIn("Cannot read CSV file", result.error)
        finally:
            os.unlink(temp_file.name)


class TestCsvTimestampValidator(unittest.TestCase):
    """Test CsvTimestampValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = CsvTimestampValidator()

    def test_valid_timestamps(self):
        """Test validation with valid timestamps."""
        df = pd.DataFrame({
            'timestamp': ['2023-01-01 12:00:00', '2023-01-01T12:01:00', '2023-01-01 12:02:00'],
            'tag1': [1.0, 2.0, 3.0]
        })

        result = self.validator.validate(df)

        self.assertTrue(result.success)
        self.assertIn("Timestamp validation passed", result.message)

    def test_no_valid_timestamps(self):
        """Test validation with no valid timestamps."""
        df = pd.DataFrame({
            'timestamp': ['invalid', 'not a timestamp', 'also invalid'],
            'tag1': [1.0, 2.0, 3.0]
        })

        result = self.validator.validate(df)

        self.assertFalse(result.success)
        self.assertIn("No valid timestamps found", result.error)

    def test_insufficient_valid_timestamps(self):
        """Test validation with insufficient valid timestamps."""
        df = pd.DataFrame({
            'timestamp': ['2023-01-01 12:00:00', 'invalid', 'also invalid', 'still invalid', 'nope'],
            'tag1': [1.0, 2.0, 3.0, 4.0, 5.0]
        })

        result = self.validator.validate(df)

        self.assertFalse(result.success)
        self.assertIn("Too many invalid timestamps", result.error)

    def test_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        df = pd.DataFrame()

        result = self.validator.validate(df)

        self.assertFalse(result.success)
        self.assertIn("Empty CSV file", result.error)


class TestOutputDirectoryValidator(unittest.TestCase):
    """Test OutputDirectoryValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = OutputDirectoryValidator()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_directory(self):
        """Test validation with valid existing directory."""
        result = self.validator.validate(self.temp_dir)

        self.assertTrue(result.success)
        self.assertIn("Output directory is valid", result.message)

    def test_valid_new_directory(self):
        """Test validation with valid new directory path."""
        new_dir = os.path.join(self.temp_dir, "new_directory")

        result = self.validator.validate(new_dir)

        self.assertTrue(result.success)
        self.assertTrue(os.path.exists(new_dir))  # Should be created

    def test_none_value(self):
        """Test validation with None value."""
        result = self.validator.validate(None)

        self.assertFalse(result.success)
        self.assertIn("Output directory cannot be None", result.error)

    def test_non_string_value(self):
        """Test validation with non-string value."""
        result = self.validator.validate(123)

        self.assertFalse(result.success)
        self.assertIn("Output directory must be a string", result.error)

    def test_empty_string(self):
        """Test validation with empty string."""
        result = self.validator.validate("")

        self.assertFalse(result.success)
        self.assertIn("Output directory cannot be empty", result.error)

    @patch('os.makedirs')
    def test_cannot_create_directory(self, mock_makedirs):
        """Test validation when directory cannot be created."""
        mock_makedirs.side_effect = PermissionError("Permission denied")

        result = self.validator.validate("/invalid/path")

        self.assertFalse(result.success)
        self.assertIn("Cannot create directory", result.error)

    @patch('os.access')
    def test_directory_not_writable(self, mock_access):
        """Test validation when directory is not writable."""
        mock_access.return_value = False

        result = self.validator.validate(self.temp_dir)

        self.assertFalse(result.success)
        self.assertIn("Directory is not writable", result.error)


class TestCompositeValidator(unittest.TestCase):
    """Test CompositeValidator."""

    def test_all_validators_pass(self):
        """Test when all validators pass."""
        validator1 = MagicMock()
        validator1.validate.return_value = MagicMock(
            success=True, message="Pass 1")

        validator2 = MagicMock()
        validator2.validate.return_value = MagicMock(
            success=True, message="Pass 2")

        composite = CompositeValidator(validator1, validator2)
        result = composite.validate("test_value")

        self.assertTrue(result.success)
        self.assertIn("All validations passed", result.message)

    def test_first_validator_fails(self):
        """Test when first validator fails."""
        validator1 = MagicMock()
        validator1.validate.return_value = MagicMock(
            success=False, error="Fail 1", message="Error 1")

        validator2 = MagicMock()
        validator2.validate.return_value = MagicMock(
            success=True, message="Pass 2")

        composite = CompositeValidator(validator1, validator2)
        result = composite.validate("test_value")

        self.assertFalse(result.success)
        self.assertIn("Fail 1", result.error)

    def test_second_validator_fails(self):
        """Test when second validator fails."""
        validator1 = MagicMock()
        validator1.validate.return_value = MagicMock(
            success=True, message="Pass 1")

        validator2 = MagicMock()
        validator2.validate.return_value = MagicMock(
            success=False, error="Fail 2", message="Error 2")

        composite = CompositeValidator(validator1, validator2)
        result = composite.validate("test_value")

        self.assertFalse(result.success)
        self.assertIn("Fail 2", result.error)


class TestCsvToRtuValidator(unittest.TestCase):
    """Test CsvToRtuValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = CsvToRtuValidator()

        # Create a valid temp CSV file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False)
        self.temp_file.write(
            "timestamp,tag1,tag2\n2023-01-01 12:00:00,1.0,2.0\n2023-01-01 12:01:00,3.0,4.0\n")
        self.temp_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_validate_file_structure_success(self):
        """Test successful file structure validation."""
        result = self.validator.validate_file_structure(self.temp_file.name)

        self.assertTrue(result.success)
        self.assertIn('metadata', result.data)
        self.assertIn('valid', result.data)
        self.assertTrue(result.data['valid'])

    def test_validate_file_content_success(self):
        """Test successful file content validation."""
        # Read file content and encode it
        with open(self.temp_file.name, 'rb') as f:
            content = f.read()

        import base64
        encoded_content = "data:text/csv;base64," + \
            base64.b64encode(content).decode('utf-8')

        result = self.validator.validate_file_content(
            encoded_content, "test.csv")

        self.assertTrue(result.success)
        self.assertIn('metadata', result.data)
        self.assertIn('valid', result.data)
        self.assertTrue(result.data['valid'])


class TestFactoryFunctions(unittest.TestCase):
    """Test factory functions for creating validators."""

    def test_create_csv_file_validator(self):
        """Test creating CSV file validator."""
        validator = create_csv_file_validator()

        self.assertIsInstance(validator, CsvToRtuValidator)

    def test_create_output_directory_validator(self):
        """Test creating output directory validator."""
        validator = create_output_directory_validator()

        self.assertIsInstance(validator, OutputDirectoryValidator)

    def test_create_file_upload_validator(self):
        """Test creating file upload validator."""
        validator = create_file_upload_validator()

        self.assertIsInstance(validator, CompositeValidator)


if __name__ == '__main__':
    unittest.main()
