"""
Unit tests for CSV to RTU service implementations.
Tests business logic with mocked dependencies.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from services.csv_to_rtu_service import (
    CsvToRtuConverterService, SpsRtuDataWriter, MockRtuDataWriter,
    CsvToRtuConverterServiceFromUpload, LegacyCsvToRtuService
)
from core.interfaces import Result
from domain.csv_rtu_models import (
    CsvFileMetadata, RtuTimestamp, RtuDataPoint, ConversionRequest,
    ConversionResult, ConversionConstants
)


class TestSpsRtuDataWriter(unittest.TestCase):
    """Test SpsRtuDataWriter."""

    def setUp(self):
        """Set up test fixtures."""
        self.writer = SpsRtuDataWriter()

    def test_is_available_when_sps_api_missing(self):
        """Test availability when sps_api is not available."""
        with patch.object(self.writer, '_sps_api_available', False):
            self.assertFalse(self.writer.is_available())

    def test_write_rtu_data_sps_api_not_available(self):
        """Test writing RTU data when sps_api is not available."""
        with patch.object(self.writer, '_sps_api_available', False):
            data_points = [
                RtuDataPoint(RtuTimestamp.now(), "TAG001", 123.45, 1)
            ]

            result = self.writer.write_rtu_data(data_points, "/output/test.dt")

            self.assertFalse(result.success)
            self.assertIn("sps_api is not available", result.error)

    @patch('services.csv_to_rtu_service.SpsRtuDataWriter._init_sps_api')
    def test_write_rtu_data_success(self, mock_init):
        """Test successful RTU data writing."""
        # Mock sps_api availability and classes
        mock_api_class = Mock()
        mock_model_class = Mock()
        mock_api_instance = Mock()

        mock_api_class.return_value = mock_api_instance
        mock_api_instance.open_rtu_file.return_value = 1  # Success

        self.writer._sps_api_available = True
        self.writer._api_class = mock_api_class
        self.writer._model_class = mock_model_class

        data_points = [
            RtuDataPoint(RtuTimestamp.now(), "TAG001", 123.45, 1),
            RtuDataPoint(RtuTimestamp.now(), "TAG002", 678.90, 1)
        ]

        with patch('os.path.exists', return_value=False):
            result = self.writer.write_rtu_data(data_points, "/output/test.dt")

        self.assertTrue(result.success)
        self.assertEqual(result.data['tags_written'], 2)
        self.assertEqual(result.data['output_path'], "/output/test.dt")

        # Verify API calls
        mock_api_instance.open_rtu_file.assert_called_once_with(
            "/output/test.dt", 2)
        self.assertEqual(mock_api_instance.write_to_rtu_file.call_count, 2)

    @patch('services.csv_to_rtu_service.SpsRtuDataWriter._init_sps_api')
    def test_write_rtu_data_open_failure(self, mock_init):
        """Test RTU data writing when file open fails."""
        mock_api_class = Mock()
        mock_api_instance = Mock()

        mock_api_class.return_value = mock_api_instance
        mock_api_instance.open_rtu_file.return_value = 0  # Failure

        self.writer._sps_api_available = True
        self.writer._api_class = mock_api_class

        data_points = [RtuDataPoint(RtuTimestamp.now(), "TAG001", 123.45, 1)]

        result = self.writer.write_rtu_data(data_points, "/output/test.dt")

        self.assertFalse(result.success)
        self.assertIn("Failed to open RTU file", result.error)


class TestMockRtuDataWriter(unittest.TestCase):
    """Test MockRtuDataWriter."""

    def setUp(self):
        """Set up test fixtures."""
        self.writer = MockRtuDataWriter()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_is_available(self):
        """Test availability of mock writer."""
        self.assertTrue(self.writer.is_available())

    def test_write_rtu_data_success(self):
        """Test successful mock RTU data writing."""
        output_path = os.path.join(self.temp_dir, "test.dt")
        data_points = [
            RtuDataPoint(RtuTimestamp.now(), "TAG001", 123.45, 1),
            RtuDataPoint(RtuTimestamp.now(), "TAG002", 678.90, 1)
        ]

        result = self.writer.write_rtu_data(data_points, output_path)

        self.assertTrue(result.success)
        self.assertEqual(result.data['tags_written'], 2)
        self.assertEqual(result.data['output_path'], output_path)
        self.assertTrue(os.path.exists(output_path))

        # Check file content
        with open(output_path, 'r') as f:
            content = f.read()
            self.assertIn("Mock RTU file", content)
            self.assertIn("2 data points", content)

    def test_write_rtu_data_directory_creation_error(self):
        """Test mock RTU data writing when directory creation fails."""
        # Use invalid path that can't be created
        invalid_path = "/invalid/nonexistent/path/test.dt"
        data_points = [RtuDataPoint(RtuTimestamp.now(), "TAG001", 123.45, 1)]

        result = self.writer.write_rtu_data(data_points, invalid_path)

        self.assertFalse(result.success)
        self.assertIn("Mock RTU write error", result.error)


class TestCsvToRtuConverterService(unittest.TestCase):
    """Test CsvToRtuConverterService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_validator = Mock()
        self.mock_writer = Mock()
        self.service = CsvToRtuConverterService(
            self.mock_validator, self.mock_writer)

        self.temp_dir = tempfile.mkdtemp()
        self.csv_file = os.path.join(self.temp_dir, "test.csv")

        # Create test CSV file
        with open(self.csv_file, 'w') as f:
            f.write(
                "timestamp,tag1,tag2\n2023-01-01 12:00:00,1.0,2.0\n2023-01-01 12:01:00,3.0,4.0\n")

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_convert_file_success(self):
        """Test successful file conversion."""
        # Mock validator response
        metadata = CsvFileMetadata("test.csv", 1024, 2, 3, "timestamp")
        self.mock_validator.validate_file_structure.return_value = Result.ok({
            'metadata': metadata,
            'valid': True
        })

        # Mock writer availability and response
        self.mock_writer.is_available.return_value = True
        self.mock_writer.write_rtu_data.return_value = Result.ok({
            'tags_written': 4,
            'output_path': os.path.join(self.temp_dir, "test.dt"),
            'output_file': "test.dt"
        })

        result = self.service.convert_file(self.csv_file, self.temp_dir)

        self.assertTrue(result.success)
        self.assertIn('result', result.data)
        self.assertEqual(result.data['records_processed'], 2)
        self.assertEqual(result.data['tags_written'], 4)

    def test_convert_file_validation_failure(self):
        """Test file conversion with validation failure."""
        self.mock_validator.validate_file_structure.return_value = Result.fail(
            "Invalid CSV format", "File validation failed"
        )
        self.mock_writer.is_available.return_value = True

        result = self.service.convert_file(self.csv_file, self.temp_dir)

        self.assertFalse(result.success)
        self.assertIn("Invalid CSV format", result.error)

    def test_convert_file_writer_failure(self):
        """Test file conversion with writer failure."""
        metadata = CsvFileMetadata("test.csv", 1024, 2, 3, "timestamp")
        self.mock_validator.validate_file_structure.return_value = Result.ok({
            'metadata': metadata,
            'valid': True
        })

        self.mock_writer.is_available.return_value = True
        self.mock_writer.write_rtu_data.return_value = Result.fail(
            "Write error", "Failed to write RTU data"
        )

        result = self.service.convert_file(self.csv_file, self.temp_dir)

        self.assertFalse(result.success)
        self.assertIn("Write error", result.error)

    def test_convert_multiple_files_success(self):
        """Test successful multiple file conversion."""
        # Create second test file
        csv_file2 = os.path.join(self.temp_dir, "test2.csv")
        with open(csv_file2, 'w') as f:
            f.write("timestamp,tag1\n2023-01-01 12:00:00,5.0\n")

        # Mock successful conversion for both files
        with patch.object(self.service, 'convert_file') as mock_convert:
            mock_convert.side_effect = [
                Result.ok({
                    'success': True,
                    'records_processed': 2,
                    'tags_written': 4,
                    'rtu_file': 'test.dt'
                }),
                Result.ok({
                    'success': True,
                    'records_processed': 1,
                    'tags_written': 1,
                    'rtu_file': 'test2.dt'
                })
            ]

            result = self.service.convert_multiple_files(
                [self.csv_file, csv_file2], self.temp_dir)

        self.assertTrue(result.success)
        self.assertEqual(result.data['successful_conversions'], 2)
        self.assertEqual(result.data['total_files'], 2)

    def test_convert_multiple_files_partial_failure(self):
        """Test multiple file conversion with partial failures."""
        csv_file2 = os.path.join(self.temp_dir, "test2.csv")
        with open(csv_file2, 'w') as f:
            f.write("timestamp,tag1\n2023-01-01 12:00:00,5.0\n")

        # Mock one success, one failure
        with patch.object(self.service, 'convert_file') as mock_convert:
            mock_convert.side_effect = [
                Result.ok({
                    'success': True,
                    'records_processed': 2,
                    'tags_written': 4,
                    'rtu_file': 'test.dt'
                }),
                Result.fail("Conversion failed", "File 2 failed")
            ]

            result = self.service.convert_multiple_files(
                [self.csv_file, csv_file2], self.temp_dir)

        # Still success if at least one file converted
        self.assertTrue(result.success)
        self.assertEqual(result.data['successful_conversions'], 1)
        self.assertEqual(result.data['total_files'], 2)

    def test_convert_multiple_files_all_failures(self):
        """Test multiple file conversion with all failures."""
        with patch.object(self.service, 'convert_file') as mock_convert:
            mock_convert.return_value = Result.fail(
                "Conversion failed", "All files failed")

            result = self.service.convert_multiple_files(
                [self.csv_file], self.temp_dir)

        self.assertFalse(result.success)
        self.assertIn("No files were successfully converted", result.error)

    def test_validate_conversion_request_writer_not_available(self):
        """Test conversion request validation when writer not available."""
        self.mock_writer.is_available.return_value = False

        result = self.service.validate_conversion_request(
            self.csv_file, self.temp_dir)

        self.assertFalse(result.success)
        self.assertIn("sps_api is not available", result.error)

    def test_get_system_info(self):
        """Test getting system information."""
        self.mock_writer.is_available.return_value = True

        result = self.service.get_system_info()

        self.assertTrue(result.success)
        self.assertIn('service_name', result.data)
        self.assertIn('version', result.data)
        self.assertIn('rtu_writer_available', result.data)
        self.assertTrue(result.data['rtu_writer_available'])


class TestLegacyCsvToRtuService(unittest.TestCase):
    """Test LegacyCsvToRtuService wrapper."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_converter = Mock()
        self.legacy_service = LegacyCsvToRtuService(self.mock_converter)

    def test_convert_to_rtu_success(self):
        """Test legacy convert_to_rtu method."""
        self.mock_converter.convert_multiple_files.return_value = Result.ok({
            'success': True,
            'successful_conversions': 2,
            'total_files': 2
        })

        result = self.legacy_service.convert_to_rtu(
            ["/file1.csv", "/file2.csv"], "/output")

        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])

    def test_convert_single_csv_to_rtu_success(self):
        """Test legacy convert_single_csv_to_rtu method."""
        self.mock_converter.convert_file.return_value = Result.ok({
            'success': True,
            'records_processed': 100,
            'tags_written': 400
        })

        result = self.legacy_service.convert_single_csv_to_rtu(
            "/file.csv", "/output")

        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])

    def test_convert_single_csv_to_rtu_failure(self):
        """Test legacy convert_single_csv_to_rtu method with failure."""
        self.mock_converter.convert_file.return_value = Result.fail(
            "Conversion failed", "Error occurred"
        )

        result = self.legacy_service.convert_single_csv_to_rtu(
            "/file.csv", "/output")

        self.assertIsInstance(result, dict)
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_validate_csv_file(self):
        """Test legacy validate_csv_file method."""
        with patch('validation.csv_validators.create_csv_file_validator') as mock_create:
            mock_validator = Mock()
            mock_validator.validate_file_structure.return_value = Result.ok({
                'valid': True,
                'metadata': Mock()
            })
            mock_create.return_value = mock_validator

            result = self.legacy_service.validate_csv_file("/file.csv")

            self.assertIsInstance(result, dict)
            self.assertTrue(result['valid'])


if __name__ == '__main__':
    unittest.main()
