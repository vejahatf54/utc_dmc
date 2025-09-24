"""
Unit tests for Review controller.
Tests UI controller logic and coordination between UI and services.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from core.interfaces import Result
from controllers.review_to_csv_controller import ReviewToCsvPageController, ReviewToCsvUIResponseFormatter


class TestReviewToCsvPageController(unittest.TestCase):
    """Test ReviewToCsvPageController."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_converter_service = Mock()
        self.mock_file_reader = Mock()
        self.controller = ReviewToCsvPageController(
            self.mock_converter_service, self.mock_file_reader)

    def test_handle_input_change(self):
        """Test handling input change."""
        result = self.controller.handle_input_change("test_id", "test_value")

        self.assertTrue(result.success)
        self.assertEqual(result.data, {})

    def test_handle_directory_selection_empty_path(self):
        """Test handling empty directory selection."""
        result = self.controller.handle_directory_selection("")

        self.assertTrue(result.success)
        self.assertIn('status_message', result.data)
        self.assertEqual(
            result.data['status_message'], "No directory selected")
        self.assertTrue(result.data['process_disabled'])

    def test_handle_directory_selection_valid_directory(self):
        """Test handling valid directory selection."""
        # Mock converter service response
        directory_info = {
            'review_files_count': 3,
            'total_size_mb': 10.5,
            'files': [
                {'filename': 'test1.review', 'file_size_mb': 3.5},
                {'filename': 'test2.review', 'file_size_mb': 4.0},
                {'filename': 'test3.review', 'file_size_mb': 3.0}
            ]
        }
        self.mock_converter_service.get_directory_info.return_value = Result.ok(
            directory_info)

        # Mock the _create_directory_components method
        with patch.object(self.controller, '_create_directory_components') as mock_create:
            mock_create.return_value = ["component1", "component2"]

            result = self.controller.handle_directory_selection("c:/test")

            self.assertTrue(result.success)
            self.assertIn('directory_info', result.data)
            self.assertIn('status_message', result.data)
            self.assertFalse(result.data['process_disabled'])
            self.assertIn("Found 3 Review files",
                          result.data['status_message'])

    def test_handle_directory_selection_invalid_directory(self):
        """Test handling invalid directory selection."""
        # Mock converter service response
        self.mock_converter_service.get_directory_info.return_value = Result.fail(
            "Directory not found")

        result = self.controller.handle_directory_selection("invalid_path")

        # Controller handles the error gracefully
        self.assertTrue(result.success)
        self.assertIn('status_message', result.data)
        self.assertIn("Error:", result.data['status_message'])
        self.assertTrue(result.data['process_disabled'])

    def test_handle_processing_start_no_directory(self):
        """Test handling processing start with no directory."""
        result = self.controller.handle_processing_start("", {})

        self.assertFalse(result.success)
        self.assertIn("no directory selected", result.error.lower())

    def test_handle_processing_start_invalid_options(self):
        """Test handling processing start with invalid options."""
        processing_options = {}  # Missing required fields

        result = self.controller.handle_processing_start(
            "c:/test", processing_options)

        self.assertFalse(result.success)

    def test_handle_processing_start_valid_request(self):
        """Test handling valid processing start request."""
        processing_options = {
            'start_time': '2023-01-01 10:00:00',
            'end_time': '2023-01-01 12:00:00',
            'peek_file': {'tags': ['tag1', 'tag2']},
            'dump_all': False,
            'frequency_minutes': 5.0
        }

        with patch.object(self.controller, '_start_background_processing') as mock_start:
            mock_start.return_value = "task_123"

            result = self.controller.handle_processing_start(
                "c:/test", processing_options)

            self.assertTrue(result.success)
            self.assertIn('task_id', result.data)
            self.assertEqual(result.data['status'], 'started')

    def test_handle_processing_cancellation(self):
        """Test handling processing cancellation."""
        # Mock converter service response
        self.mock_converter_service.cancel_conversion.return_value = Result.ok(
            True)

        result = self.controller.handle_processing_cancellation()

        self.assertTrue(result.success)
        self.assertTrue(result.data['cancelled'])

    def test_handle_processing_cancellation_error(self):
        """Test handling processing cancellation error."""
        # Mock converter service response
        self.mock_converter_service.cancel_conversion.return_value = Result.fail(
            "Cancellation failed")

        result = self.controller.handle_processing_cancellation()

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Cancellation failed")

    def test_get_system_info(self):
        """Test getting system information."""
        # Mock converter service response
        system_info = {
            'component': 'Review to CSV Converter',
            'version': '2.0.0'
        }
        self.mock_converter_service.get_system_info.return_value = Result.ok(
            system_info)

        result = self.controller.get_system_info()

        self.assertTrue(result.success)
        self.assertEqual(result.data['component'], 'Review to CSV Converter')

    def test_validate_processing_options_missing_fields(self):
        """Test validating processing options with missing fields."""
        options = {'start_time': '2023-01-01 10:00:00'}  # Missing end_time

        result = self.controller._validate_processing_options(options)

        self.assertFalse(result.success)
        self.assertIn("Missing required field", result.error)

    def test_validate_processing_options_invalid_time_range(self):
        """Test validating processing options with invalid time range."""
        options = {
            'start_time': '2023-01-01 12:00:00',
            'end_time': '2023-01-01 10:00:00'  # End before start
        }

        result = self.controller._validate_processing_options(options)

        self.assertFalse(result.success)
        self.assertIn("start time must be before end time",
                      result.error.lower())

    def test_validate_processing_options_invalid_frequency(self):
        """Test validating processing options with invalid frequency."""
        options = {
            'start_time': '2023-01-01 10:00:00',
            'end_time': '2023-01-01 12:00:00',
            'dump_all': False,
            'frequency_minutes': -5.0  # Negative frequency
        }

        result = self.controller._validate_processing_options(options)

        self.assertFalse(result.success)
        self.assertIn("frequency", result.error.lower())

    def test_validate_processing_options_valid(self):
        """Test validating valid processing options."""
        options = {
            'start_time': '2023-01-01 10:00:00',
            'end_time': '2023-01-01 12:00:00',
            'dump_all': False,
            'frequency_minutes': 5.0
        }

        result = self.controller._validate_processing_options(options)

        self.assertTrue(result.success)
        self.assertTrue(result.data)


class TestReviewToCsvUIResponseFormatter(unittest.TestCase):
    """Test ReviewToCsvUIResponseFormatter."""

    def test_format_directory_selection_response_success(self):
        """Test formatting successful directory selection response."""
        result_data = {
            'directory_components': ['component1', 'component2'],
            'status_message': 'Found 3 files',
            'process_disabled': False
        }
        result = Result.ok(result_data)

        components, status, disabled = ReviewToCsvUIResponseFormatter.format_directory_selection_response(
            result)

        self.assertEqual(components, ['component1', 'component2'])
        self.assertEqual(status, 'Found 3 files')
        self.assertFalse(disabled)

    def test_format_directory_selection_response_error(self):
        """Test formatting error directory selection response."""
        result = Result.fail("Directory not found")

        components, status, disabled = ReviewToCsvUIResponseFormatter.format_directory_selection_response(
            result)

        self.assertEqual(components, [])
        self.assertIn("Error:", status)
        self.assertTrue(disabled)

    def test_format_processing_response_success(self):
        """Test formatting successful processing response."""
        result_data = {
            'message': 'Processing started',
            'task_id': 'task_123'
        }
        result = Result.ok(result_data)

        message, disabled = ReviewToCsvUIResponseFormatter.format_processing_response(
            result)

        self.assertEqual(message, 'Processing started')
        self.assertFalse(disabled)

    def test_format_processing_response_error(self):
        """Test formatting error processing response."""
        result = Result.fail("Processing failed")

        message, disabled = ReviewToCsvUIResponseFormatter.format_processing_response(
            result)

        self.assertIn("Error:", message)
        self.assertTrue(disabled)

    def test_format_status_response_running(self):
        """Test formatting running status response."""
        result_data = {
            'status': 'running',
            'progress': 'Processing files...'
        }
        result = Result.ok(result_data)

        progress, complete, status = ReviewToCsvUIResponseFormatter.format_status_response(
            result)

        self.assertEqual(progress, 'Processing files...')
        self.assertFalse(complete)
        self.assertEqual(status, 'Processing...')

    def test_format_status_response_completed_success(self):
        """Test formatting completed successful status response."""
        result_data = {
            'status': 'completed',
            'result': {'success': True}
        }
        result = Result.ok(result_data)

        progress, complete, status = ReviewToCsvUIResponseFormatter.format_status_response(
            result)

        self.assertEqual(progress, 'Processing completed successfully')
        self.assertTrue(complete)
        self.assertEqual(status, 'Complete')

    def test_format_status_response_completed_error(self):
        """Test formatting completed error status response."""
        result_data = {
            'status': 'completed',
            'result': {'success': False, 'error': 'Processing failed'}
        }
        result = Result.ok(result_data)

        progress, complete, status = ReviewToCsvUIResponseFormatter.format_status_response(
            result)

        self.assertIn('Processing failed', progress)
        self.assertTrue(complete)
        self.assertEqual(status, 'Error')

    def test_format_status_response_cancelled(self):
        """Test formatting cancelled status response."""
        result_data = {
            'status': 'cancelled'
        }
        result = Result.ok(result_data)

        progress, complete, status = ReviewToCsvUIResponseFormatter.format_status_response(
            result)

        self.assertEqual(progress, 'Processing cancelled')
        self.assertTrue(complete)
        self.assertEqual(status, 'Cancelled')

    def test_format_status_response_idle(self):
        """Test formatting idle status response."""
        result_data = {
            'status': 'idle'
        }
        result = Result.ok(result_data)

        progress, complete, status = ReviewToCsvUIResponseFormatter.format_status_response(
            result)

        self.assertEqual(progress, 'Ready')
        self.assertTrue(complete)
        self.assertEqual(status, 'Ready')

    def test_format_status_response_error(self):
        """Test formatting status response error."""
        result = Result.fail("Status check failed")

        progress, complete, status = ReviewToCsvUIResponseFormatter.format_status_response(
            result)

        self.assertIn('Status check error', progress)
        self.assertTrue(complete)
        self.assertEqual(status, 'Error')


if __name__ == '__main__':
    unittest.main()
