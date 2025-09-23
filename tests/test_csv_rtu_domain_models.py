"""
Unit tests for CSV to RTU domain models.
Tests value objects and business entities.
"""

import unittest
from datetime import datetime
from domain.csv_rtu_models import (
    CsvFileMetadata, RtuTimestamp, RtuDataPoint, ConversionRequest,
    ConversionResult, ConversionConstants
)


class TestCsvFileMetadata(unittest.TestCase):
    """Test CsvFileMetadata value object."""

    def test_valid_creation(self):
        """Test creating valid CsvFileMetadata."""
        metadata = CsvFileMetadata("test.csv", 1024, 100, 5, "timestamp")

        self.assertEqual(metadata.filename, "test.csv")
        self.assertEqual(metadata.size, 1024)
        self.assertEqual(metadata.rows, 100)
        self.assertEqual(metadata.columns, 5)
        self.assertEqual(metadata.first_column, "timestamp")
        self.assertEqual(metadata.tag_count, 4)  # columns - 1
        self.assertEqual(metadata.total_points, 400)  # tags * rows
        self.assertEqual(metadata.size_kb, 1.0)

    def test_invalid_filename(self):
        """Test creating CsvFileMetadata with invalid filename."""
        with self.assertRaises(ValueError) as context:
            CsvFileMetadata("", 1024, 100, 5, "timestamp")
        self.assertIn("Filename cannot be empty", str(context.exception))

        with self.assertRaises(ValueError):
            CsvFileMetadata("   ", 1024, 100, 5, "timestamp")

    def test_invalid_size(self):
        """Test creating CsvFileMetadata with invalid size."""
        with self.assertRaises(ValueError) as context:
            CsvFileMetadata("test.csv", -1, 100, 5, "timestamp")
        self.assertIn("File size cannot be negative", str(context.exception))

    def test_invalid_rows(self):
        """Test creating CsvFileMetadata with invalid rows."""
        with self.assertRaises(ValueError) as context:
            CsvFileMetadata("test.csv", 1024, -1, 5, "timestamp")
        self.assertIn("Row count cannot be negative", str(context.exception))

    def test_invalid_columns(self):
        """Test creating CsvFileMetadata with invalid columns."""
        with self.assertRaises(ValueError) as context:
            CsvFileMetadata("test.csv", 1024, 100, -1, "timestamp")
        self.assertIn("Column count cannot be negative",
                      str(context.exception))

    def test_invalid_first_column(self):
        """Test creating CsvFileMetadata with invalid first column."""
        with self.assertRaises(ValueError) as context:
            CsvFileMetadata("test.csv", 1024, 100, 5, "")
        self.assertIn("First column name cannot be empty",
                      str(context.exception))

    def test_equality(self):
        """Test CsvFileMetadata equality."""
        metadata1 = CsvFileMetadata("test.csv", 1024, 100, 5, "timestamp")
        metadata2 = CsvFileMetadata("test.csv", 1024, 100, 5, "timestamp")
        metadata3 = CsvFileMetadata("test2.csv", 1024, 100, 5, "timestamp")

        self.assertEqual(metadata1, metadata2)
        self.assertNotEqual(metadata1, metadata3)

    def test_hash(self):
        """Test CsvFileMetadata hashing."""
        metadata1 = CsvFileMetadata("test.csv", 1024, 100, 5, "timestamp")
        metadata2 = CsvFileMetadata("test.csv", 1024, 100, 5, "timestamp")

        self.assertEqual(hash(metadata1), hash(metadata2))

    def test_string_representation(self):
        """Test CsvFileMetadata string representation."""
        metadata = CsvFileMetadata("test.csv", 1024, 100, 5, "timestamp")
        str_repr = str(metadata)

        self.assertIn("test.csv", str_repr)
        self.assertIn("100", str_repr)
        self.assertIn("5", str_repr)


class TestRtuTimestamp(unittest.TestCase):
    """Test RtuTimestamp value object."""

    def test_valid_creation(self):
        """Test creating valid RtuTimestamp."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        timestamp = RtuTimestamp(dt)

        self.assertEqual(timestamp.value, dt)
        self.assertEqual(timestamp.iso_format, dt.isoformat())

    def test_invalid_creation(self):
        """Test creating RtuTimestamp with invalid values."""
        with self.assertRaises(ValueError) as context:
            RtuTimestamp(None)
        self.assertIn("Timestamp cannot be None", str(context.exception))

        with self.assertRaises(ValueError) as context:
            RtuTimestamp("not a datetime")
        self.assertIn("Timestamp must be a datetime object",
                      str(context.exception))

    def test_from_string_iso_format(self):
        """Test creating RtuTimestamp from ISO format string."""
        timestamp_str = "2023-01-01T12:00:00"
        timestamp = RtuTimestamp.from_string(timestamp_str)

        expected_dt = datetime(2023, 1, 1, 12, 0, 0)
        self.assertEqual(timestamp.value, expected_dt)

    def test_from_string_standard_format(self):
        """Test creating RtuTimestamp from standard format string."""
        timestamp_str = "2023-01-01 12:00:00"
        timestamp = RtuTimestamp.from_string(timestamp_str)

        expected_dt = datetime(2023, 1, 1, 12, 0, 0)
        self.assertEqual(timestamp.value, expected_dt)

    def test_from_string_zulu_format(self):
        """Test creating RtuTimestamp from Zulu format string."""
        timestamp_str = "2023-01-01T12:00:00Z"
        timestamp = RtuTimestamp.from_string(timestamp_str)

        # Should handle Z suffix correctly
        self.assertIsInstance(timestamp.value, datetime)

    def test_from_string_invalid(self):
        """Test creating RtuTimestamp from invalid string."""
        with self.assertRaises(ValueError) as context:
            RtuTimestamp.from_string("")
        self.assertIn("Timestamp string cannot be empty",
                      str(context.exception))

        with self.assertRaises(ValueError) as context:
            RtuTimestamp.from_string("invalid")
        self.assertIn("Invalid timestamp format", str(context.exception))

    def test_now(self):
        """Test creating RtuTimestamp for current time."""
        timestamp = RtuTimestamp.now()

        self.assertIsInstance(timestamp.value, datetime)
        # Should be close to current time (within 1 second)
        time_diff = abs((datetime.now() - timestamp.value).total_seconds())
        self.assertLess(time_diff, 1.0)

    def test_equality(self):
        """Test RtuTimestamp equality."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        timestamp1 = RtuTimestamp(dt)
        timestamp2 = RtuTimestamp(dt)
        timestamp3 = RtuTimestamp(datetime(2023, 1, 1, 13, 0, 0))

        self.assertEqual(timestamp1, timestamp2)
        self.assertNotEqual(timestamp1, timestamp3)


class TestRtuDataPoint(unittest.TestCase):
    """Test RtuDataPoint value object."""

    def setUp(self):
        """Set up test fixtures."""
        self.timestamp = RtuTimestamp(datetime(2023, 1, 1, 12, 0, 0))

    def test_valid_creation(self):
        """Test creating valid RtuDataPoint."""
        data_point = RtuDataPoint(self.timestamp, "TAG001", 123.45, 1)

        self.assertEqual(data_point.timestamp, self.timestamp)
        self.assertEqual(data_point.tag_name, "TAG001")
        self.assertEqual(data_point.value, 123.45)
        self.assertEqual(data_point.quality, 1)
        self.assertTrue(data_point.is_good_quality)

    def test_invalid_timestamp(self):
        """Test creating RtuDataPoint with invalid timestamp."""
        with self.assertRaises(ValueError) as context:
            RtuDataPoint(None, "TAG001", 123.45, 1)
        self.assertIn("Timestamp cannot be None", str(context.exception))

        with self.assertRaises(ValueError) as context:
            RtuDataPoint("not a timestamp", "TAG001", 123.45, 1)
        self.assertIn("Timestamp must be RtuTimestamp instance",
                      str(context.exception))

    def test_invalid_tag_name(self):
        """Test creating RtuDataPoint with invalid tag name."""
        with self.assertRaises(ValueError) as context:
            RtuDataPoint(self.timestamp, "", 123.45, 1)
        self.assertIn("Tag name cannot be empty", str(context.exception))

        with self.assertRaises(ValueError):
            RtuDataPoint(self.timestamp, "   ", 123.45, 1)

    def test_invalid_value(self):
        """Test creating RtuDataPoint with invalid value."""
        with self.assertRaises(ValueError) as context:
            RtuDataPoint(self.timestamp, "TAG001", "not a number", 1)
        self.assertIn("Value must be numeric", str(context.exception))

    def test_invalid_quality(self):
        """Test creating RtuDataPoint with invalid quality."""
        with self.assertRaises(ValueError) as context:
            RtuDataPoint(self.timestamp, "TAG001", 123.45, 2)
        self.assertIn("Quality must be 0 (bad) or 1 (good)",
                      str(context.exception))

    def test_from_csv_data_valid(self):
        """Test creating RtuDataPoint from valid CSV data."""
        data_point = RtuDataPoint.from_csv_data(
            "2023-01-01 12:00:00", "TAG001", "123.45")

        self.assertEqual(data_point.tag_name, "TAG001")
        self.assertEqual(data_point.value, 123.45)
        self.assertEqual(data_point.quality, 1)
        self.assertTrue(data_point.is_good_quality)

    def test_from_csv_data_invalid_value(self):
        """Test creating RtuDataPoint from CSV data with invalid value."""
        data_point = RtuDataPoint.from_csv_data(
            "2023-01-01 12:00:00", "TAG001", "nan")

        self.assertEqual(data_point.tag_name, "TAG001")
        self.assertEqual(data_point.value, 0.0)
        self.assertEqual(data_point.quality, 0)
        self.assertFalse(data_point.is_good_quality)

    def test_from_csv_data_none_value(self):
        """Test creating RtuDataPoint from CSV data with None value."""
        data_point = RtuDataPoint.from_csv_data(
            "2023-01-01 12:00:00", "TAG001", None)

        self.assertEqual(data_point.tag_name, "TAG001")
        self.assertEqual(data_point.value, 0.0)
        self.assertEqual(data_point.quality, 0)
        self.assertFalse(data_point.is_good_quality)

    def test_equality(self):
        """Test RtuDataPoint equality."""
        data_point1 = RtuDataPoint(self.timestamp, "TAG001", 123.45, 1)
        data_point2 = RtuDataPoint(self.timestamp, "TAG001", 123.45, 1)
        data_point3 = RtuDataPoint(self.timestamp, "TAG002", 123.45, 1)

        self.assertEqual(data_point1, data_point2)
        self.assertNotEqual(data_point1, data_point3)


class TestConversionRequest(unittest.TestCase):
    """Test ConversionRequest value object."""

    def setUp(self):
        """Set up test fixtures."""
        self.metadata = CsvFileMetadata("test.csv", 1024, 100, 5, "timestamp")

    def test_valid_creation(self):
        """Test creating valid ConversionRequest."""
        request = ConversionRequest("/path/test.csv", "/output", self.metadata)

        self.assertEqual(request.csv_file_path, "/path/test.csv")
        self.assertEqual(request.output_directory, "/output")
        self.assertEqual(request.metadata, self.metadata)
        self.assertEqual(request.expected_rtu_filename, "test.dt")
        self.assertEqual(request.expected_rtu_path, "/output/test.dt")

    def test_invalid_csv_file_path(self):
        """Test creating ConversionRequest with invalid CSV file path."""
        with self.assertRaises(ValueError) as context:
            ConversionRequest("", "/output", self.metadata)
        self.assertIn("CSV file path cannot be empty", str(context.exception))

    def test_invalid_output_directory(self):
        """Test creating ConversionRequest with invalid output directory."""
        with self.assertRaises(ValueError) as context:
            ConversionRequest("/path/test.csv", "", self.metadata)
        self.assertIn("Output directory cannot be empty",
                      str(context.exception))

    def test_invalid_metadata(self):
        """Test creating ConversionRequest with invalid metadata."""
        with self.assertRaises(ValueError) as context:
            ConversionRequest("/path/test.csv", "/output", None)
        self.assertIn("Metadata cannot be None", str(context.exception))

        with self.assertRaises(ValueError) as context:
            ConversionRequest("/path/test.csv", "/output", "not metadata")
        self.assertIn("Metadata must be CsvFileMetadata instance",
                      str(context.exception))


class TestConversionResult(unittest.TestCase):
    """Test ConversionResult value object."""

    def setUp(self):
        """Set up test fixtures."""
        self.metadata = CsvFileMetadata("test.csv", 1024, 100, 5, "timestamp")
        self.request = ConversionRequest(
            "/path/test.csv", "/output", self.metadata)

    def test_successful_result(self):
        """Test creating successful ConversionResult."""
        result = ConversionResult.create_success(
            self.request, 100, 400, "/output/test.dt")

        self.assertTrue(result.success)
        self.assertEqual(result.request, self.request)
        self.assertEqual(result.records_processed, 100)
        self.assertEqual(result.tags_written, 400)
        self.assertEqual(result.rtu_file_path, "/output/test.dt")
        self.assertIsNone(result.error_message)
        self.assertEqual(result.filename, "test.csv")
        self.assertEqual(result.output_filename, "test.dt")

    def test_failed_result(self):
        """Test creating failed ConversionResult."""
        result = ConversionResult.create_failure(self.request, "Test error")

        self.assertFalse(result.success)
        self.assertEqual(result.request, self.request)
        self.assertEqual(result.records_processed, 0)
        self.assertEqual(result.tags_written, 0)
        self.assertIsNone(result.rtu_file_path)
        self.assertEqual(result.error_message, "Test error")
        self.assertEqual(result.filename, "test.csv")
        self.assertEqual(result.output_filename, "test.dt")

    def test_invalid_creation(self):
        """Test creating ConversionResult with invalid values."""
        with self.assertRaises(ValueError) as context:
            ConversionResult(None, True, 100, 400)
        self.assertIn("Request cannot be None", str(context.exception))

        with self.assertRaises(ValueError) as context:
            ConversionResult(self.request, True, -1, 400)
        self.assertIn("Records processed cannot be negative",
                      str(context.exception))

        with self.assertRaises(ValueError) as context:
            ConversionResult(self.request, True, 100, -1)
        self.assertIn("Tags written cannot be negative",
                      str(context.exception))


class TestConversionConstants(unittest.TestCase):
    """Test ConversionConstants."""

    def test_constants_exist(self):
        """Test that all required constants exist."""
        self.assertIsInstance(
            ConversionConstants.SUPPORTED_CSV_EXTENSIONS, list)
        self.assertIn('.csv', ConversionConstants.SUPPORTED_CSV_EXTENSIONS)

        self.assertEqual(ConversionConstants.RTU_EXTENSION, '.dt')
        self.assertEqual(ConversionConstants.QUALITY_GOOD, 1)
        self.assertEqual(ConversionConstants.QUALITY_BAD, 0)
        self.assertEqual(ConversionConstants.DEFAULT_OUTPUT_DIR, 'RTU_Output')

        self.assertIsInstance(ConversionConstants.MAX_FILE_SIZE_BYTES, int)
        self.assertIsInstance(ConversionConstants.MIN_COLUMNS, int)
        self.assertIsInstance(ConversionConstants.MAX_COLUMNS, int)

        self.assertIsInstance(ConversionConstants.SPS_API_NOT_AVAILABLE, str)
        self.assertIsInstance(ConversionConstants.EMPTY_CSV_FILE, str)
        self.assertIsInstance(ConversionConstants.INVALID_CSV_FORMAT, str)


if __name__ == '__main__':
    unittest.main()
