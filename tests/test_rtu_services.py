"""
Unit tests for RTU service implementations.
Tests the refactored SOLID-compliant RTU services.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from datetime import datetime

from core.interfaces import Result
from services.rtu_file_reader_service import RtuFileReaderService
from services.rtu_to_csv_converter_service import RtuToCsvConverterService
from services.rtu_resizer_service import RtuResizerService


class TestRtuFileReaderService(unittest.TestCase):
    """Test RtuFileReaderService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = RtuFileReaderService()
        # Create a temporary RTU file for testing
        self.temp_file = tempfile.NamedTemporaryFile(
            suffix='.dt', delete=False)
        self.temp_file.write(b'test RTU data')
        self.temp_file.close()
        self.temp_file_path = self.temp_file.name

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_file_path)
        except:
            pass

    def test_get_file_info_success(self):
        """Test successful file info retrieval."""
        # Arrange
        with patch.object(self.service, '_rtu_service') as mock_rtu_service:
            expected_file_info = {
                'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
                'last_timestamp': datetime(2023, 1, 1, 12, 0, 0),
                'total_points': 1000,
                'tags_count': 50
            }
            mock_rtu_service.get_file_info.return_value = expected_file_info

            # Act
            result = self.service.get_file_info(self.temp_file_path)

            # Assert
            self.assertTrue(result.success)
            self.assertIn('file_path', result.data)
            self.assertIn('filename', result.data)
            self.assertIn('first_timestamp', result.data)
            self.assertIn('last_timestamp', result.data)
            self.assertIn('total_points', result.data)
            self.assertIn('tags_count', result.data)
            self.assertIn('duration_seconds', result.data)
            mock_rtu_service.get_file_info.assert_called_once_with(
                self.temp_file_path)

    def test_get_file_info_invalid_path(self):
        """Test file info with invalid path."""
        result = self.service.get_file_info("invalid_file.txt")
        self.assertFalse(result.success)
        self.assertIn("Invalid RTU file extension", result.error)

    def test_get_file_info_nonexistent_file(self):
        """Test file info with nonexistent file."""
        result = self.service.get_file_info("nonexistent.dt")
        self.assertFalse(result.success)
        self.assertIn("File not found", result.error)

    def test_get_file_info_no_timestamps(self):
        """Test file info with missing timestamps."""
        # Arrange
        with patch.object(self.service, '_rtu_service') as mock_rtu_service:
            mock_rtu_service.get_file_info.return_value = {'total_points': 100}

            # Act
            result = self.service.get_file_info(self.temp_file_path)

            # Assert
            self.assertFalse(result.success)
            self.assertIn("Invalid file timestamps", result.error)

    def test_validate_file_success(self):
        """Test successful file validation."""
        # Arrange
        with patch.object(self.service, '_rtu_service') as mock_rtu_service:
            mock_rtu_service.get_file_info.return_value = {
                'first_timestamp': datetime.now()}

            # Act
            result = self.service.validate_file(self.temp_file_path)

            # Assert
            self.assertTrue(result.success)
            self.assertTrue(result.data)

    def test_validate_file_invalid_extension(self):
        """Test file validation with invalid extension."""
        result = self.service.validate_file("test.txt")
        self.assertFalse(result.success)
        self.assertIn("Invalid RTU file extension", result.error)

    def test_validate_file_empty_file(self):
        """Test file validation with empty file."""
        # Create empty RTU file
        empty_file = tempfile.NamedTemporaryFile(suffix='.dt', delete=False)
        empty_file.close()

        try:
            result = self.service.validate_file(empty_file.name)
            self.assertFalse(result.success)
            self.assertIn("Empty file", result.error)
        finally:
            os.unlink(empty_file.name)


class TestRtuToCsvConverterService(unittest.TestCase):
    """Test RtuToCsvConverterService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_file_reader = Mock()
        self.service = RtuToCsvConverterService(self.mock_file_reader)

        # Create temporary files for testing
        self.temp_input_file = tempfile.NamedTemporaryFile(
            suffix='.dt', delete=False)
        self.temp_input_file.close()

        self.temp_output_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_input_file.name)
            import shutil
            shutil.rmtree(self.temp_output_dir)
        except:
            pass

    def test_convert_file_success(self):
        """Test successful file conversion."""
        # Arrange
        with patch.object(self.service, '_rtu_service') as mock_rtu_service:
            self.mock_file_reader.validate_file.return_value = Result.ok(True)

            mock_conversion_result = {
                'success': True,
                'records_processed': 1000,
                'processing_time': 5.5
            }
            mock_rtu_service.export_csv_flat.return_value = mock_conversion_result

            # Create expected output file
            expected_output = os.path.join(self.temp_output_dir,
                                           os.path.splitext(os.path.basename(self.temp_input_file.name))[0] + '.csv')
            with open(expected_output, 'w') as f:
                f.write('test,data\n1,2\n')

            # Act
            result = self.service.convert_file(
                self.temp_input_file.name, self.temp_output_dir)

            # Assert
            self.assertTrue(result.success)
            self.assertIn('output_file', result.data)
            self.assertIn('records_processed', result.data)
            self.assertIn('processing_time', result.data)
            mock_rtu_service.export_csv_flat.assert_called_once()

    def test_convert_file_invalid_input(self):
        """Test conversion with invalid input file."""
        self.mock_file_reader.validate_file.return_value = Result.fail(
            "Invalid file", "File validation failed")

        result = self.service.convert_file("invalid.dt", self.temp_output_dir)
        self.assertFalse(result.success)
        self.assertIn("Invalid file", result.error)

    def test_convert_file_invalid_output_dir(self):
        """Test conversion with invalid output directory."""
        self.mock_file_reader.validate_file.return_value = Result.ok(True)

        result = self.service.convert_file(
            self.temp_input_file.name, "nonexistent/directory")
        self.assertFalse(result.success)
        self.assertIn("Output directory not found", result.error)

    def test_convert_multiple_files_success(self):
        """Test successful multiple file conversion."""
        # Arrange
        file_paths = [self.temp_input_file.name]

        with patch.object(self.service, 'convert_file') as mock_convert:
            mock_convert.return_value = Result.ok({
                'output_file': 'test.csv',
                'records_processed': 100,
                'processing_time': 1.0
            })

            # Act
            result = self.service.convert_multiple_files(
                file_paths, self.temp_output_dir)

            # Assert
            self.assertTrue(result.success)
            self.assertEqual(result.data['total_files_processed'], 1)
            self.assertEqual(result.data['total_files_failed'], 0)

    def test_convert_multiple_files_empty_list(self):
        """Test multiple file conversion with empty list."""
        result = self.service.convert_multiple_files([], self.temp_output_dir)
        self.assertFalse(result.success)
        self.assertIn("No files provided", result.error)

    def test_get_system_info(self):
        """Test system info retrieval."""
        result = self.service.get_system_info()
        self.assertTrue(result.success)
        self.assertIn('conversion_type', result.data)
        self.assertIn('supported_sampling_modes', result.data)


class TestRtuResizerService(unittest.TestCase):
    """Test RtuResizerService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_file_reader = Mock()
        self.service = RtuResizerService(self.mock_file_reader)

        # Create temporary files for testing
        self.temp_input_file = tempfile.NamedTemporaryFile(
            suffix='.dt', delete=False)
        self.temp_input_file.close()

        self.temp_output_file = tempfile.NamedTemporaryFile(
            suffix='.dt', delete=False)
        self.temp_output_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_input_file.name)
            os.unlink(self.temp_output_file.name)
        except:
            pass

    def test_resize_file_success(self):
        """Test successful file resize."""
        # Arrange
        with patch.object(self.service, '_rtu_service') as mock_rtu_service:
            # Mock validation
            with patch.object(self.service, 'validate_resize_request') as mock_validate:
                mock_validate.return_value = Result.ok(True)

                # Mock file info calls
                original_info = {
                    'total_points': 1000,
                    'tags_count': 50,
                    'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
                    'last_timestamp': datetime(2023, 1, 1, 12, 0, 0)
                }
                resized_info = {
                    'total_points': 500,
                    'tags_count': 50,
                    'first_timestamp': datetime(2023, 1, 1, 10, 30, 0),
                    'last_timestamp': datetime(2023, 1, 1, 11, 30, 0)
                }

                self.mock_file_reader.get_file_info.side_effect = [
                    Result.ok(original_info),  # Original file info
                    Result.ok(resized_info)    # Resized file info
                ]

                # Mock RTU service resize
                # RTU service returns integer (points written) on success
                mock_rtu_service.resize_rtu.return_value = 500

                # Act
                result = self.service.resize_file(
                    self.temp_input_file.name,
                    self.temp_output_file.name,
                    "01/01/23 10:30:00",
                    "01/01/23 11:30:00"
                )

                # Assert
                self.assertTrue(result.success)
                self.assertIn('input_file', result.data)
                self.assertIn('output_file', result.data)
                self.assertIn('input_points', result.data)
                self.assertIn('output_points', result.data)
                self.assertIn('processing_time', result.data)

    def test_resize_file_validation_failure(self):
        """Test resize with validation failure."""
        with patch.object(self.service, 'validate_resize_request') as mock_validate:
            mock_validate.return_value = Result.fail(
                "Invalid request", "Validation failed")

            result = self.service.resize_file(
                self.temp_input_file.name,
                self.temp_output_file.name
            )

            self.assertFalse(result.success)
            self.assertIn("Invalid request", result.error)

    def test_validate_resize_request_success(self):
        """Test successful resize request validation."""
        self.mock_file_reader.validate_file.return_value = Result.ok(True)

        result = self.service.validate_resize_request(
            self.temp_input_file.name,
            self.temp_output_file.name
        )

        self.assertTrue(result.success)

    def test_validate_resize_request_invalid_input(self):
        """Test resize validation with invalid input file."""
        self.mock_file_reader.validate_file.return_value = Result.fail(
            "Invalid file", "File not found")

        result = self.service.validate_resize_request(
            "nonexistent.dt",
            self.temp_output_file.name
        )

        self.assertFalse(result.success)
        self.assertIn("Invalid file", result.error)

    def test_validate_resize_request_invalid_output_path(self):
        """Test resize validation with invalid output path."""
        self.mock_file_reader.validate_file.return_value = Result.ok(True)

        # Invalid output directory
        result = self.service.validate_resize_request(
            self.temp_input_file.name,
            "/nonexistent/directory/output.dt"
        )

        self.assertFalse(result.success)
        self.assertIn("Output directory does not exist", result.error)

    def test_validate_resize_request_invalid_extension(self):
        """Test resize validation with invalid output extension."""
        self.mock_file_reader.validate_file.return_value = Result.ok(True)

        result = self.service.validate_resize_request(
            self.temp_input_file.name,
            "output.txt"  # Invalid extension
        )

        self.assertFalse(result.success)
        self.assertIn("Invalid output file extension", result.error)

    def test_validate_time_range_success(self):
        """Test successful time range validation."""
        file_info = {
            'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
            'last_timestamp': datetime(2023, 1, 1, 12, 0, 0)
        }
        self.mock_file_reader.get_file_info.return_value = Result.ok(file_info)

        result = self.service._validate_time_range(
            self.temp_input_file.name,
            "01/01/23 10:30:00",
            "01/01/23 11:30:00"
        )

        self.assertTrue(result.success)

    def test_validate_time_range_invalid_format(self):
        """Test time range validation with invalid format."""
        file_info = {
            'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
            'last_timestamp': datetime(2023, 1, 1, 12, 0, 0)
        }
        self.mock_file_reader.get_file_info.return_value = Result.ok(file_info)

        result = self.service._validate_time_range(
            self.temp_input_file.name,
            "invalid-date-format",
            "01/01/23 11:30:00"
        )

        self.assertFalse(result.success)
        self.assertIn("Invalid start time format", result.error)

    def test_validate_time_range_start_after_end(self):
        """Test time range validation with start after end."""
        file_info = {
            'first_timestamp': datetime(2023, 1, 1, 10, 0, 0),
            'last_timestamp': datetime(2023, 1, 1, 12, 0, 0)
        }
        self.mock_file_reader.get_file_info.return_value = Result.ok(file_info)

        result = self.service._validate_time_range(
            self.temp_input_file.name,
            "01/01/23 11:30:00",  # After end time
            "01/01/23 10:30:00"   # Before start time
        )

        self.assertFalse(result.success)
        self.assertIn("Start time must be before end time", result.error)

    def test_get_system_info(self):
        """Test system info retrieval."""
        result = self.service.get_system_info()
        self.assertTrue(result.success)
        self.assertIn('operation_type', result.data)
        self.assertIn('supports_time_range', result.data)
        self.assertIn('supports_tag_mapping', result.data)


if __name__ == '__main__':
    unittest.main()
