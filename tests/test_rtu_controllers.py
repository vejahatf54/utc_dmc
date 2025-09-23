"""
Unit tests for RTU controllers.
Tests the refactored SOLID-compliant RTU controllers.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import os
from datetime import datetime
import dash_mantine_components as dmc

from core.interfaces import Result
from controllers.rtu_to_csv_controller import RtuToCsvPageController
from controllers.rtu_resizer_controller import RtuResizerPageController


class TestRtuToCsvPageController(unittest.TestCase):
    """Test RtuToCsvPageController."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_converter_service = Mock()
        self.mock_file_reader = Mock()
        self.controller = RtuToCsvPageController(
            self.mock_converter_service, self.mock_file_reader)

    def test_handle_input_change(self):
        """Test input change handling."""
        result = self.controller.handle_input_change(
            "test-input", "test-value")
        self.assertTrue(result.success)
        self.assertEqual(result.data, {})

    def test_handle_file_selection_success(self):
        """Test successful file selection."""
        # Arrange
        test_files = ["test1.dt", "test2.dt"]

        # Mock file info for each file
        file_info_1 = {
            'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
            'last_timestamp': datetime(2023, 1, 1, 12, 0, 0),
            'total_points': 1000,
            'tags_count': 50
        }
        file_info_2 = {
            'first_timestamp': datetime(2023, 1, 1, 12, 0, 0),
            'last_timestamp': datetime(2023, 1, 1, 14, 0, 0),
            'total_points': 800,
            'tags_count': 45
        }

        self.mock_file_reader.get_file_info.side_effect = [
            Result.ok(file_info_1),
            Result.ok(file_info_2)
        ]

        # Create temporary files to mock file existence
        temp1 = tempfile.NamedTemporaryFile(suffix='.dt', delete=False)
        temp2 = tempfile.NamedTemporaryFile(suffix='.dt', delete=False)
        temp1.write(b'test data')
        temp2.write(b'test data')
        temp1.close()
        temp2.close()

        test_files = [temp1.name, temp2.name]

        try:
            # Act
            result = self.controller.handle_file_selection(test_files)

            # Assert
            self.assertTrue(result.success)
            self.assertIn('files', result.data)
            self.assertIn('file_components', result.data)
            self.assertEqual(len(result.data['files']), 2)
            self.assertFalse(result.data['process_disabled'])

        finally:
            try:
                os.unlink(temp1.name)
            except (PermissionError, FileNotFoundError):
                pass
            try:
                os.unlink(temp2.name)
            except (PermissionError, FileNotFoundError):
                pass

    def test_handle_file_selection_no_files(self):
        """Test file selection with no files."""
        result = self.controller.handle_file_selection([])

        self.assertTrue(result.success)
        self.assertEqual(len(result.data['files']), 0)
        self.assertTrue(result.data['process_disabled'])

    def test_handle_file_selection_invalid_files(self):
        """Test file selection with invalid files."""
        test_files = ["nonexistent.dt"]

        result = self.controller.handle_file_selection(test_files)

        self.assertTrue(result.success)
        self.assertEqual(len(result.data['files']), 0)
        self.assertTrue(result.data['process_disabled'])

    def test_handle_conversion_start_success(self):
        """Test successful conversion start."""
        # Arrange
        files = [{'path': 'test.dt', 'name': 'test.dt'}]
        output_directory = tempfile.mkdtemp()
        processing_options = {
            'enable_sampling': False,
            'sample_interval': 60,
            'sample_mode': 'actual'
        }

        self.mock_converter_service.convert_file.return_value = Result.ok({
            'output_file': 'test.csv',
            'records_processed': 1000
        })

        try:
            # Act
            result = self.controller.handle_conversion_start(
                files, output_directory, processing_options)

            # Assert
            self.assertTrue(result.success)
            self.assertIn('status', result.data)
            self.assertEqual(result.data['status'], 'completed')
            self.assertIn('files_processed', result.data)

        finally:
            import shutil
            shutil.rmtree(output_directory)

    def test_handle_conversion_start_no_files(self):
        """Test conversion start with no files."""
        result = self.controller.handle_conversion_start([], "/tmp", {})

        self.assertFalse(result.success)
        self.assertIn("No files to process", result.error)

    def test_handle_conversion_start_invalid_directory(self):
        """Test conversion start with invalid output directory."""
        files = [{'path': 'test.dt', 'name': 'test.dt'}]

        result = self.controller.handle_conversion_start(
            files, "/nonexistent/directory", {})

        self.assertFalse(result.success)
        self.assertIn("Invalid output directory", result.error)

    def test_handle_background_conversion(self):
        """Test background conversion start."""
        files = [{'path': 'test.dt', 'name': 'test.dt'}]
        output_directory = tempfile.mkdtemp()
        processing_options = {}

        try:
            # Act
            task_id = self.controller.handle_background_conversion(
                files, output_directory, processing_options)

            # Assert
            self.assertIsInstance(task_id, str)
            self.assertIn("rtu_csv_task_", task_id)

        finally:
            import shutil
            shutil.rmtree(output_directory)

    def test_get_file_info_success(self):
        """Test successful file info retrieval."""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.dt', delete=False)
        temp_file.write(b'test data')
        temp_file.close()

        try:
            file_info = {
                'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
                'last_timestamp': datetime(2023, 1, 1, 12, 0, 0),
                'total_points': 1000,
                'tags_count': 50
            }
            self.mock_file_reader.get_file_info.return_value = Result.ok(
                file_info)

            # Act
            result = self.controller.get_file_info(temp_file.name)

            # Assert
            self.assertTrue(result.success)
            self.mock_file_reader.get_file_info.assert_called_once_with(
                temp_file.name)

        finally:
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass

    def test_get_file_info_invalid_file(self):
        """Test file info with invalid file."""
        result = self.controller.get_file_info("invalid.txt")

        self.assertFalse(result.success)
        self.assertIn("Invalid RTU file extension", result.error)

    def test_get_system_info(self):
        """Test system info retrieval."""
        expected_info = {'conversion_type': 'RTU to CSV'}
        self.mock_converter_service.get_system_info.return_value = Result.ok(
            expected_info)

        result = self.controller.get_system_info()

        self.assertTrue(result.success)
        self.mock_converter_service.get_system_info.assert_called_once()

    def test_create_file_components(self):
        """Test file components creation."""
        files = [
            {
                'name': 'test.dt',
                'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
                'last_timestamp': datetime(2023, 1, 1, 12, 0, 0),
                'total_points': 1000,
                'tags_count': 50
            }
        ]

        components = self.controller._create_file_components(files)

        self.assertEqual(len(components), 1)
        self.assertIsInstance(components[0], dmc.Paper)

    def test_create_file_components_empty(self):
        """Test file components creation with empty list."""
        components = self.controller._create_file_components([])

        self.assertEqual(len(components), 0)


class TestRtuResizerPageController(unittest.TestCase):
    """Test RtuResizerPageController."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_resizer_service = Mock()
        self.mock_file_reader = Mock()
        self.controller = RtuResizerPageController(
            self.mock_resizer_service, self.mock_file_reader)

    def test_handle_input_change(self):
        """Test input change handling."""
        result = self.controller.handle_input_change(
            "test-input", "test-value")
        self.assertTrue(result.success)
        self.assertEqual(result.data, {})

    def test_handle_file_selection_success(self):
        """Test successful file selection."""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.dt', delete=False)
        temp_file.write(b'test data')
        temp_file.close()

        try:
            file_info = {
                'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
                'last_timestamp': datetime(2023, 1, 1, 12, 0, 0),
                'total_points': 1000,
                'tags_count': 50,
                'duration_seconds': 7200
            }
            self.mock_file_reader.get_file_info.return_value = Result.ok(
                file_info)

            # Act
            result = self.controller.handle_file_selection(temp_file.name)

            # Assert
            self.assertTrue(result.success)
            self.assertTrue(result.data['file_loaded'])
            self.assertIn('file_info', result.data)
            self.assertFalse(result.data['resize_disabled'])

        finally:
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass

    def test_handle_file_selection_no_file(self):
        """Test file selection with no file."""
        result = self.controller.handle_file_selection("")

        self.assertTrue(result.success)
        self.assertFalse(result.data['file_loaded'])
        self.assertTrue(result.data['resize_disabled'])

    def test_handle_file_selection_nonexistent_file(self):
        """Test file selection with nonexistent file."""
        result = self.controller.handle_file_selection("nonexistent.dt")

        self.assertFalse(result.success)
        self.assertIn("File not found", result.error)

    def test_handle_resize_request_success(self):
        """Test successful resize request."""
        # Mock validation and resize
        self.mock_resizer_service.validate_resize_request.return_value = Result.ok(
            True)

        resize_result = {
            'input_points': 1000,
            'output_points': 500,
            'processing_time': 2.5
        }
        self.mock_resizer_service.resize_file.return_value = Result.ok(
            resize_result)

        # Act
        result = self.controller.handle_resize_request(
            "input.dt", "output.dt", "01/01/23 10:00:00", "01/01/23 11:00:00"
        )

        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.data['status'], 'completed')
        self.assertIn('output_file', result.data)

    def test_handle_resize_request_validation_failure(self):
        """Test resize request with validation failure."""
        self.mock_resizer_service.validate_resize_request.return_value = Result.fail(
            "Invalid request", "Validation failed")

        result = self.controller.handle_resize_request("input.dt", "output.dt")

        self.assertFalse(result.success)
        self.assertIn("Invalid", result.error)

    def test_handle_background_resize(self):
        """Test background resize start."""
        task_id = self.controller.handle_background_resize(
            "input.dt", "output.dt")

        self.assertIsInstance(task_id, str)
        self.assertIn("rtu_resize_task_", task_id)

    def test_validate_time_range_success(self):
        """Test successful time range validation."""
        # Set up current file info
        self.controller._current_file_info = {
            'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
            'last_timestamp': datetime(2023, 1, 1, 12, 0, 0)
        }

        result = self.controller.validate_time_range(
            "01/01/23 10:30:00", "01/01/23 11:30:00")

        self.assertTrue(result.success)
        self.assertTrue(result.data['valid'])

    def test_validate_time_range_no_file_loaded(self):
        """Test time range validation with no file loaded."""
        result = self.controller.validate_time_range(
            "01/01/23 10:30:00", "01/01/23 11:30:00")

        self.assertFalse(result.success)
        self.assertIn("No file loaded", result.error)

    def test_validate_time_range_invalid_format(self):
        """Test time range validation with invalid format."""
        self.controller._current_file_info = {
            'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
            'last_timestamp': datetime(2023, 1, 1, 12, 0, 0)
        }

        result = self.controller.validate_time_range(
            "invalid-format", "01/01/23 11:30:00")

        self.assertFalse(result.success)
        self.assertIn("Invalid start time format", result.error)

    def test_get_file_time_bounds_success(self):
        """Test successful file time bounds retrieval."""
        self.controller._current_file_info = {
            'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
            'last_timestamp': datetime(2023, 1, 1, 12, 0, 0)
        }

        result = self.controller.get_file_time_bounds()

        self.assertTrue(result.success)
        self.assertIn('first_timestamp', result.data)
        self.assertIn('last_timestamp', result.data)
        self.assertIn('duration_seconds', result.data)

    def test_get_file_time_bounds_no_file(self):
        """Test file time bounds with no file loaded."""
        result = self.controller.get_file_time_bounds()

        self.assertFalse(result.success)
        self.assertIn("No file loaded", result.error)

    def test_generate_output_filename_with_time_range(self):
        """Test output filename generation with time range."""
        result = self.controller.generate_output_filename(
            "test.dt", "01/01/23 10:00:00", "01/01/23 11:00:00"
        )

        self.assertTrue(result.success)
        self.assertIn("_from_", result.data)
        self.assertIn("_to_", result.data)
        self.assertTrue(result.data.endswith('.dt'))

    def test_generate_output_filename_no_time_range(self):
        """Test output filename generation without time range."""
        result = self.controller.generate_output_filename("test.dt")

        self.assertTrue(result.success)
        self.assertIn("_resized", result.data)
        self.assertTrue(result.data.endswith('.dt'))

    def test_get_system_info(self):
        """Test system info retrieval."""
        expected_info = {'operation_type': 'RTU Resize'}
        self.mock_resizer_service.get_system_info.return_value = Result.ok(
            expected_info)

        result = self.controller.get_system_info()

        self.assertTrue(result.success)
        self.mock_resizer_service.get_system_info.assert_called_once()

    def test_clear_current_file(self):
        """Test clearing current file."""
        self.controller._current_file_info = {'test': 'data'}

        self.controller.clear_current_file()

        self.assertIsNone(self.controller._current_file_info)


if __name__ == '__main__':
    unittest.main()
