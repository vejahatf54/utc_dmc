"""
Unit tests for text replacement controller.
Tests UI controller handling interactions and formatting responses.
"""

import unittest
import base64
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from controllers.text_replacement_controller import (
    TextReplacementPageController, TextReplacementUIResponseFormatter,
    create_text_replacement_controller
)
from services.text_replacement_service_v2 import ITextReplacementService
from validation.text_replacement_validators import (
    CsvContentValidator, DirectoryPathValidator, FileExtensionsValidator
)
from core.interfaces import Result


class TestTextReplacementPageController(unittest.TestCase):
    """Test cases for TextReplacementPageController."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock(spec=ITextReplacementService)
        self.mock_csv_validator = Mock(spec=CsvContentValidator)
        self.mock_dir_validator = Mock(spec=DirectoryPathValidator)
        self.mock_ext_validator = Mock(spec=FileExtensionsValidator)

        self.controller = TextReplacementPageController(
            self.mock_service,
            self.mock_csv_validator,
            self.mock_dir_validator,
            self.mock_ext_validator
        )

        # Create valid CSV content
        csv_content = "old1,new1\nold2,new2\n"
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')
        self.valid_contents = f"data:text/csv;base64,{encoded_content}"

    def test_handle_csv_upload_success(self):
        """Test successful CSV upload handling."""
        # Mock CSV validation success
        self.mock_csv_validator.validate.return_value = Result.ok(
            True, "Valid CSV")

        # Mock substitution validation (mocked internally)
        with patch('controllers.text_replacement_controller.SubstitutionDataValidator') as mock_sub_validator_class:
            mock_sub_validator = Mock()
            mock_sub_validator.validate.return_value = Result.ok(
                [("old1", "new1"), ("old2", "new2")])
            mock_sub_validator_class.return_value = mock_sub_validator

            result = self.controller.handle_csv_upload(
                self.valid_contents, "test.csv")

        self.assertTrue(result.success)
        self.assertEqual(result.data['filename'], "test.csv")
        self.assertEqual(result.data['substitution_count'], 2)
        self.assertEqual(result.data['status'], 'valid')

    def test_handle_csv_upload_validation_failure(self):
        """Test CSV upload with validation failure."""
        self.mock_csv_validator.validate.return_value = Result.fail(
            "Invalid CSV format")

        result = self.controller.handle_csv_upload(
            self.valid_contents, "test.csv")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid CSV format")

    def test_handle_csv_upload_substitution_parsing_failure(self):
        """Test CSV upload with substitution parsing failure."""
        self.mock_csv_validator.validate.return_value = Result.ok(
            True, "Valid CSV")

        with patch('controllers.text_replacement_controller.SubstitutionDataValidator') as mock_sub_validator_class:
            mock_sub_validator = Mock()
            mock_sub_validator.validate.return_value = Result.fail(
                "Parse error")
            mock_sub_validator_class.return_value = mock_sub_validator

            result = self.controller.handle_csv_upload(
                self.valid_contents, "test.csv")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Parse error")

    def test_handle_csv_upload_exception(self):
        """Test CSV upload with unexpected exception."""
        self.mock_csv_validator.validate.side_effect = Exception(
            "Unexpected error")

        result = self.controller.handle_csv_upload(
            self.valid_contents, "test.csv")

        self.assertFalse(result.success)
        self.assertIn("Error processing CSV file", result.error)

    def test_handle_text_replacement_success(self):
        """Test successful text replacement handling."""
        # Mock all validations as successful
        self.mock_dir_validator.validate.return_value = Result.ok(
            True, "Valid directory")
        self.mock_ext_validator.validate.return_value = Result.ok(
            True, "Valid extensions")

        # Mock service success
        service_result = {
            'processed_files': 5,
            'total_files': 5,
            'errors': [],
            'substitution_count': 2
        }
        self.mock_service.replace_text_in_files.return_value = Result.ok(
            service_result, "Success")

        csv_data = {'content': 'encoded_content'}

        result = self.controller.handle_text_replacement(
            "/test/dir", csv_data, "txt,py", True
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data, service_result)

        # Verify service was called with correct parameters
        self.mock_service.replace_text_in_files.assert_called_once_with(
            directory="/test/dir",
            substitution_source="encoded_content",
            extensions=["txt", "py"],
            match_case=True
        )

    def test_handle_text_replacement_missing_directory(self):
        """Test text replacement with missing directory."""
        csv_data = {'content': 'encoded_content'}

        result = self.controller.handle_text_replacement(
            "", csv_data, "txt,py", True
        )

        self.assertFalse(result.success)
        self.assertIn("Target directory is required", result.error)

    def test_handle_text_replacement_missing_csv(self):
        """Test text replacement with missing CSV data."""
        self.mock_dir_validator.validate.return_value = Result.ok(
            True, "Valid directory")

        result = self.controller.handle_text_replacement(
            "/test/dir", {}, "txt,py", True
        )

        self.assertFalse(result.success)
        self.assertIn("CSV file is required", result.error)

    def test_handle_text_replacement_missing_extensions(self):
        """Test text replacement with missing extensions."""
        self.mock_dir_validator.validate.return_value = Result.ok(
            True, "Valid directory")
        csv_data = {'content': 'encoded_content'}

        result = self.controller.handle_text_replacement(
            "/test/dir", csv_data, "", True
        )

        self.assertFalse(result.success)
        self.assertIn("File extensions are required", result.error)

    def test_handle_text_replacement_validation_failures(self):
        """Test text replacement with multiple validation failures."""
        self.mock_dir_validator.validate.return_value = Result.fail(
            "Invalid directory")
        self.mock_ext_validator.validate.return_value = Result.fail(
            "Invalid extensions")

        csv_data = {'content': 'encoded_content'}

        result = self.controller.handle_text_replacement(
            "/invalid/dir", csv_data, "invalid_ext", True
        )

        self.assertFalse(result.success)
        self.assertIn("Invalid directory", result.error)
        self.assertIn("Invalid extensions", result.error)

    def test_handle_text_replacement_service_failure(self):
        """Test text replacement with service failure."""
        self.mock_dir_validator.validate.return_value = Result.ok(
            True, "Valid directory")
        self.mock_ext_validator.validate.return_value = Result.ok(
            True, "Valid extensions")

        self.mock_service.replace_text_in_files.return_value = Result.fail(
            "Service error")

        csv_data = {'content': 'encoded_content'}

        result = self.controller.handle_text_replacement(
            "/test/dir", csv_data, "txt,py", True
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Service error")

    def test_handle_text_replacement_extension_parsing(self):
        """Test text replacement with extension parsing."""
        self.mock_dir_validator.validate.return_value = Result.ok(
            True, "Valid directory")
        self.mock_ext_validator.validate.return_value = Result.ok(
            True, "Valid extensions")
        self.mock_service.replace_text_in_files.return_value = Result.ok(
            {}, "Success")

        csv_data = {'content': 'encoded_content'}

        # Test with dots and asterisks in extensions
        result = self.controller.handle_text_replacement(
            "/test/dir", csv_data, ".txt,*.py, js ", True
        )

        self.assertTrue(result.success)

        # Verify extensions were cleaned
        call_args = self.mock_service.replace_text_in_files.call_args
        self.assertEqual(call_args[1]['extensions'], ["txt", "py", "js"])

    def test_handle_text_replacement_no_valid_extensions(self):
        """Test text replacement with no valid extensions after parsing."""
        self.mock_dir_validator.validate.return_value = Result.ok(
            True, "Valid directory")
        self.mock_ext_validator.validate.return_value = Result.ok(
            True, "Valid extensions")

        csv_data = {'content': 'encoded_content'}

        result = self.controller.handle_text_replacement(
            "/test/dir", csv_data, "  ,  ,  ", True
        )

        self.assertFalse(result.success)
        self.assertIn("No valid extensions specified", result.error)

    def test_handle_text_replacement_exception(self):
        """Test text replacement with unexpected exception."""
        self.mock_dir_validator.validate.side_effect = Exception(
            "Unexpected error")

        csv_data = {'content': 'encoded_content'}

        result = self.controller.handle_text_replacement(
            "/test/dir", csv_data, "txt", True
        )

        self.assertFalse(result.success)
        self.assertIn("Processing error", result.error)

    def test_controller_with_default_validators(self):
        """Test controller with default validators."""
        controller = TextReplacementPageController(self.mock_service)

        self.assertIsNotNone(controller._csv_validator)
        self.assertIsNotNone(controller._directory_validator)
        self.assertIsNotNone(controller._extensions_validator)


class TestTextReplacementUIResponseFormatter(unittest.TestCase):
    """Test cases for TextReplacementUIResponseFormatter."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = TextReplacementUIResponseFormatter()

    def test_format_csv_upload_response_success(self):
        """Test formatting successful CSV upload response."""
        csv_data = {
            'filename': 'test.csv',
            'content': 'encoded_content',
            'substitution_count': 5,
            'status': 'valid',
            'message': 'Success message'
        }
        result = Result.ok(csv_data, "Success message")

        data, status = self.formatter.format_csv_upload_response(result)

        self.assertEqual(data, csv_data)
        self.assertEqual(status['type'], 'success')
        self.assertEqual(status['title'], 'CSV File Loaded Successfully')
        self.assertEqual(status['filename'], 'test.csv')
        self.assertEqual(status['substitution_count'], 5)

    def test_format_csv_upload_response_failure(self):
        """Test formatting failed CSV upload response."""
        result = Result.fail("Upload error")

        data, status = self.formatter.format_csv_upload_response(result)

        self.assertEqual(data, {})
        self.assertEqual(status['type'], 'error')
        self.assertEqual(status['title'], 'File Processing Error')
        self.assertEqual(status['message'], 'Upload error')

    def test_format_replacement_response_success(self):
        """Test formatting successful replacement response."""
        data = {
            'processed_files': 10,
            'total_files': 10,
            'errors': []
        }
        result = Result.ok(data, "All files processed successfully")

        response = self.formatter.format_replacement_response(result)

        self.assertEqual(response['type'], 'success')
        self.assertEqual(response['title'], 'Completed Successfully')
        self.assertEqual(response['message'],
                         "All files processed successfully")
        self.assertEqual(response['details']['processed_files'], 10)
        self.assertEqual(response['details']['total_files'], 10)

    def test_format_replacement_response_partial_success(self):
        """Test formatting partial success replacement response."""
        data = {
            'processed_files': 8,
            'total_files': 10,
            'errors': ['Error 1', 'Error 2']
        }
        result = Result.ok(data, "Partially completed")

        response = self.formatter.format_replacement_response(result)

        self.assertEqual(response['type'], 'warning')
        self.assertEqual(response['title'], 'Partially Completed')
        self.assertEqual(response['message'], "Partially completed")
        self.assertEqual(response['details']['processed_files'], 8)
        self.assertEqual(response['details']['total_files'], 10)
        self.assertEqual(response['details']['error_count'], 2)

    def test_format_replacement_response_failure(self):
        """Test formatting failed replacement response."""
        result = Result.fail("Processing failed")

        response = self.formatter.format_replacement_response(result)

        self.assertEqual(response['type'], 'error')
        self.assertEqual(response['title'], 'Processing Error')
        self.assertEqual(response['message'], 'Processing failed')

    def test_format_replacement_response_success_no_errors(self):
        """Test formatting success response with explicitly empty errors."""
        data = {
            'processed_files': 5,
            'total_files': 5,
            'errors': []  # Explicitly empty
        }
        result = Result.ok(data, "Success")

        response = self.formatter.format_replacement_response(result)

        self.assertEqual(response['type'], 'success')


class TestControllerFactory(unittest.TestCase):
    """Test cases for controller factory function."""

    def test_create_text_replacement_controller(self):
        """Test text replacement controller factory."""
        mock_service = Mock(spec=ITextReplacementService)

        controller = create_text_replacement_controller(mock_service)

        self.assertIsInstance(controller, TextReplacementPageController)
        self.assertEqual(controller._service, mock_service)


if __name__ == '__main__':
    unittest.main()
