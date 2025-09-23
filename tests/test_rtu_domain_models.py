"""
Unit tests for RTU domain models.
Tests all value objects and their validation logic.
"""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

from domain.rtu_models import (
    RtuFilePath, RtuTimeRange, RtuFileInfo, RtuProcessingOptions, RtuConversionConstants
)


class TestRtuFilePath(unittest.TestCase):
    """Test RtuFilePath value object."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary RTU file for testing
        self.temp_file = tempfile.NamedTemporaryFile(
            suffix='.dt', delete=False)
        self.temp_file.write(b'test data')
        self.temp_file.close()
        self.temp_file_path = self.temp_file.name

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_file_path)
        except:
            pass

    def test_valid_rtu_file_path(self):
        """Test creation of valid RTU file path."""
        rtu_path = RtuFilePath(self.temp_file_path)
        self.assertEqual(str(rtu_path), str(
            Path(self.temp_file_path).resolve()))
        self.assertTrue(rtu_path.filename.endswith('.dt'))
        self.assertEqual(rtu_path.extension, '.dt')
        self.assertTrue(rtu_path.exists())

    def test_valid_rtu_extension(self):
        """Test RTU file with .rtu extension."""
        rtu_file = tempfile.NamedTemporaryFile(suffix='.rtu', delete=False)
        rtu_file.close()
        try:
            rtu_path = RtuFilePath(rtu_file.name)
            self.assertEqual(rtu_path.extension, '.rtu')
        finally:
            os.unlink(rtu_file.name)

    def test_invalid_extension(self):
        """Test invalid file extension raises ValueError."""
        with self.assertRaises(ValueError) as context:
            RtuFilePath("test.txt")
        self.assertIn("Invalid RTU file extension", str(context.exception))

    def test_empty_path(self):
        """Test empty path raises ValueError."""
        with self.assertRaises(ValueError) as context:
            RtuFilePath("")
        self.assertIn("RTU file path cannot be empty", str(context.exception))

    def test_non_string_path(self):
        """Test non-string path raises ValueError."""
        with self.assertRaises(ValueError):
            RtuFilePath(123)

    def test_value_object_equality(self):
        """Test value object equality."""
        path1 = RtuFilePath(self.temp_file_path)
        path2 = RtuFilePath(self.temp_file_path)
        self.assertEqual(path1, path2)

    def test_value_object_hashing(self):
        """Test value object can be hashed."""
        path1 = RtuFilePath(self.temp_file_path)
        path2 = RtuFilePath(self.temp_file_path)
        self.assertEqual(hash(path1), hash(path2))


class TestRtuTimeRange(unittest.TestCase):
    """Test RtuTimeRange value object."""

    def setUp(self):
        """Set up test fixtures."""
        self.start_time = datetime(2023, 1, 1, 10, 0, 0)
        self.end_time = datetime(2023, 1, 1, 12, 0, 0)

    def test_valid_time_range(self):
        """Test creation of valid time range."""
        time_range = RtuTimeRange(self.start_time, self.end_time)
        self.assertEqual(time_range.start_time, self.start_time)
        self.assertEqual(time_range.end_time, self.end_time)
        self.assertTrue(time_range.has_start_time)
        self.assertTrue(time_range.has_end_time)
        self.assertTrue(time_range.is_complete_range)
        self.assertEqual(time_range.duration_seconds, 7200.0)  # 2 hours

    def test_start_time_only(self):
        """Test time range with only start time."""
        time_range = RtuTimeRange(self.start_time, None)
        self.assertEqual(time_range.start_time, self.start_time)
        self.assertIsNone(time_range.end_time)
        self.assertTrue(time_range.has_start_time)
        self.assertFalse(time_range.has_end_time)
        self.assertFalse(time_range.is_complete_range)
        self.assertIsNone(time_range.duration_seconds)

    def test_end_time_only(self):
        """Test time range with only end time."""
        time_range = RtuTimeRange(None, self.end_time)
        self.assertIsNone(time_range.start_time)
        self.assertEqual(time_range.end_time, self.end_time)
        self.assertFalse(time_range.has_start_time)
        self.assertTrue(time_range.has_end_time)
        self.assertFalse(time_range.is_complete_range)

    def test_no_times(self):
        """Test time range with no times specified."""
        time_range = RtuTimeRange()
        self.assertIsNone(time_range.start_time)
        self.assertIsNone(time_range.end_time)
        self.assertFalse(time_range.has_start_time)
        self.assertFalse(time_range.has_end_time)
        self.assertFalse(time_range.is_complete_range)

    def test_invalid_time_range(self):
        """Test invalid time range raises ValueError."""
        with self.assertRaises(ValueError) as context:
            RtuTimeRange(self.end_time, self.start_time)  # start after end
        self.assertIn("Start time must be before end time",
                      str(context.exception))

    def test_equal_times(self):
        """Test equal start and end times raises ValueError."""
        with self.assertRaises(ValueError):
            RtuTimeRange(self.start_time, self.start_time)

    def test_format_methods(self):
        """Test time formatting methods."""
        time_range = RtuTimeRange(self.start_time, self.end_time)
        self.assertEqual(time_range.format_start_time(), "01/01/23 10:00:00")
        self.assertEqual(time_range.format_end_time(), "01/01/23 12:00:00")

    def test_string_representation(self):
        """Test string representation."""
        time_range = RtuTimeRange(self.start_time, self.end_time)
        expected = "01/01/23 10:00:00 to 01/01/23 12:00:00"
        self.assertEqual(str(time_range), expected)


class TestRtuFileInfo(unittest.TestCase):
    """Test RtuFileInfo value object."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(
            suffix='.dt', delete=False)
        self.temp_file.close()
        self.file_path = self.temp_file.name
        self.first_timestamp = datetime(2023, 1, 1, 10, 0, 0)
        self.last_timestamp = datetime(2023, 1, 1, 12, 0, 0)

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.file_path)
        except:
            pass

    def test_valid_file_info(self):
        """Test creation of valid file info."""
        file_info = RtuFileInfo(
            self.file_path, self.first_timestamp, self.last_timestamp, 1000, 50)

        self.assertIsInstance(file_info.file_path, RtuFilePath)
        self.assertEqual(file_info.first_timestamp, self.first_timestamp)
        self.assertEqual(file_info.last_timestamp, self.last_timestamp)
        self.assertEqual(file_info.total_points, 1000)
        self.assertEqual(file_info.tags_count, 50)
        self.assertEqual(file_info.duration_seconds, 7200.0)

    def test_time_range_property(self):
        """Test time range property."""
        file_info = RtuFileInfo(
            self.file_path, self.first_timestamp, self.last_timestamp, 1000, 50)

        time_range = file_info.time_range
        self.assertIsInstance(time_range, RtuTimeRange)
        self.assertEqual(time_range.start_time, self.first_timestamp)
        self.assertEqual(time_range.end_time, self.last_timestamp)

    def test_to_dict_method(self):
        """Test conversion to dictionary."""
        file_info = RtuFileInfo(
            self.file_path, self.first_timestamp, self.last_timestamp, 1000, 50)

        result_dict = file_info.to_dict()
        self.assertIn('file_path', result_dict)
        self.assertIn('filename', result_dict)
        self.assertIn('first_timestamp', result_dict)
        self.assertIn('last_timestamp', result_dict)
        self.assertIn('total_points', result_dict)
        self.assertIn('tags_count', result_dict)
        self.assertIn('duration_seconds', result_dict)

    def test_invalid_timestamps(self):
        """Test invalid timestamps raise ValueError."""
        with self.assertRaises(ValueError):
            RtuFileInfo(self.file_path, self.last_timestamp,
                        self.first_timestamp, 1000, 50)

    def test_invalid_counts(self):
        """Test invalid counts raise ValueError."""
        with self.assertRaises(ValueError):
            RtuFileInfo(self.file_path, self.first_timestamp,
                        self.last_timestamp, -1, 50)

        with self.assertRaises(ValueError):
            RtuFileInfo(self.file_path, self.first_timestamp,
                        self.last_timestamp, 1000, -1)


class TestRtuProcessingOptions(unittest.TestCase):
    """Test RtuProcessingOptions dataclass."""

    def test_default_options(self):
        """Test default processing options."""
        options = RtuProcessingOptions()
        self.assertFalse(options.enable_peek_file_filtering)
        self.assertEqual(options.peek_file_pattern, "*.dt")
        self.assertIsNone(options.time_range)
        self.assertEqual(options.sample_interval, 60)
        self.assertEqual(options.sample_mode, "actual")
        self.assertEqual(options.output_format, "csv")
        self.assertTrue(options.enable_parallel_processing)

    def test_custom_options(self):
        """Test custom processing options."""
        time_range = RtuTimeRange(
            datetime.now(), datetime.now() + timedelta(hours=1))
        options = RtuProcessingOptions(
            enable_peek_file_filtering=True,
            time_range=time_range,
            sample_interval=120,
            sample_mode="interpolated",
            enable_parallel_processing=False
        )

        self.assertTrue(options.enable_peek_file_filtering)
        self.assertEqual(options.time_range, time_range)
        self.assertEqual(options.sample_interval, 120)
        self.assertEqual(options.sample_mode, "interpolated")
        self.assertFalse(options.enable_parallel_processing)

    def test_invalid_sample_interval(self):
        """Test invalid sample interval raises ValueError."""
        with self.assertRaises(ValueError):
            RtuProcessingOptions(sample_interval=-1)

        with self.assertRaises(ValueError):
            RtuProcessingOptions(sample_interval=0)

    def test_invalid_sample_mode(self):
        """Test invalid sample mode raises ValueError."""
        with self.assertRaises(ValueError):
            RtuProcessingOptions(sample_mode="invalid")

    def test_invalid_output_format(self):
        """Test invalid output format raises ValueError."""
        with self.assertRaises(ValueError):
            RtuProcessingOptions(output_format="invalid")

    def test_invalid_max_workers(self):
        """Test invalid max workers raises ValueError."""
        with self.assertRaises(ValueError):
            RtuProcessingOptions(max_workers=-1)

        with self.assertRaises(ValueError):
            RtuProcessingOptions(max_workers=0)

    def test_immutability(self):
        """Test that options are immutable (frozen dataclass)."""
        options = RtuProcessingOptions()
        with self.assertRaises(AttributeError):
            options.sample_interval = 120


class TestRtuConversionConstants(unittest.TestCase):
    """Test RtuConversionConstants."""

    def test_supported_extensions(self):
        """Test supported file extensions."""
        self.assertIn('.dt', RtuConversionConstants.SUPPORTED_INPUT_EXTENSIONS)
        self.assertIn(
            '.rtu', RtuConversionConstants.SUPPORTED_INPUT_EXTENSIONS)
        self.assertIn(
            '.csv', RtuConversionConstants.SUPPORTED_OUTPUT_EXTENSIONS)

    def test_time_formats(self):
        """Test time format constants."""
        self.assertEqual(
            RtuConversionConstants.TIME_FORMAT_DMY, "%d/%m/%y %H:%M:%S")
        self.assertEqual(
            RtuConversionConstants.TIME_FORMAT_YMD, "%Y-%m-%d %H:%M:%S")
        self.assertEqual(
            RtuConversionConstants.TIME_FORMAT_ISO, "%Y-%m-%dT%H:%M:%S")

    def test_get_system_info(self):
        """Test system info method."""
        info = RtuConversionConstants.get_system_info()
        self.assertIn('supported_input_extensions', info)
        self.assertIn('supported_output_extensions', info)
        self.assertIn('default_sample_interval', info)
        self.assertIn('max_file_size_mb', info)
        self.assertIn('time_formats', info)

    def test_default_values(self):
        """Test default constant values."""
        self.assertEqual(RtuConversionConstants.DEFAULT_SAMPLE_INTERVAL, 60)
        self.assertEqual(RtuConversionConstants.DEFAULT_MAX_WORKERS, 4)
        self.assertEqual(RtuConversionConstants.DEFAULT_OUTPUT_FORMAT, "csv")
        self.assertGreater(RtuConversionConstants.MAX_FILE_SIZE_BYTES, 0)


if __name__ == '__main__':
    unittest.main()
