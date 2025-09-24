"""
Unit tests for Review domain models.
Tests value objects and business logic for Review processing.
"""

import unittest
from datetime import datetime, timedelta
from domain.review_models import (
    ReviewFilePath, ReviewDirectoryPath, ReviewTimeRange, ReviewPeekFile,
    ReviewProcessingOptions, ReviewFileInfo, ReviewConversionResult,
    ReviewConversionConstants
)


class TestReviewFilePath(unittest.TestCase):
    """Test ReviewFilePath value object."""

    def test_valid_review_file_path(self):
        """Test creating a valid Review file path."""
        file_path = ReviewFilePath("test.review")
        self.assertEqual(file_path.extension, ".review")
        self.assertEqual(file_path.csv_filename, "test.csv")

    def test_invalid_extension_raises_error(self):
        """Test that invalid extension raises error."""
        with self.assertRaises(ValueError):
            ReviewFilePath("test.txt")

    def test_empty_path_raises_error(self):
        """Test that empty path raises error."""
        with self.assertRaises(ValueError):
            ReviewFilePath("")

    def test_non_string_path_raises_error(self):
        """Test that non-string path raises error."""
        with self.assertRaises(ValueError):
            ReviewFilePath(123)


class TestReviewDirectoryPath(unittest.TestCase):
    """Test ReviewDirectoryPath value object."""

    def test_valid_directory_path(self):
        """Test creating a valid directory path."""
        dir_path = ReviewDirectoryPath("c:/temp")
        self.assertIsNotNone(dir_path.value)
        self.assertIsNotNone(dir_path.path_obj)

    def test_empty_directory_raises_error(self):
        """Test that empty directory raises error."""
        with self.assertRaises(ValueError):
            ReviewDirectoryPath("")

    def test_non_string_directory_raises_error(self):
        """Test that non-string directory raises error."""
        with self.assertRaises(ValueError):
            ReviewDirectoryPath(123)


class TestReviewTimeRange(unittest.TestCase):
    """Test ReviewTimeRange value object."""

    def test_valid_time_range(self):
        """Test creating a valid time range."""
        start = "2023-01-01 10:00:00"
        end = "2023-01-01 12:00:00"
        time_range = ReviewTimeRange(start, end)

        self.assertEqual(time_range.start_time, start)
        self.assertEqual(time_range.end_time, end)
        self.assertTrue(time_range.is_valid_range())

    def test_invalid_time_range_raises_error(self):
        """Test that invalid time range raises error."""
        start = "2023-01-01 12:00:00"
        end = "2023-01-01 10:00:00"  # End before start

        with self.assertRaises(ValueError):
            ReviewTimeRange(start, end)

    def test_format_for_dreview(self):
        """Test formatting times for dreview command."""
        start = "2023-01-01 10:30:45"
        end = "2023-01-01 12:15:30"
        time_range = ReviewTimeRange(start, end)

        start_formatted, end_formatted = time_range.format_for_dreview()
        self.assertEqual(start_formatted, "23/01/01_10:30:45")
        self.assertEqual(end_formatted, "23/01/01_12:15:30")

    def test_empty_times_raise_error(self):
        """Test that empty times raise error."""
        with self.assertRaises(ValueError):
            ReviewTimeRange("", "2023-01-01 12:00:00")

        with self.assertRaises(ValueError):
            ReviewTimeRange("2023-01-01 10:00:00", "")


class TestReviewPeekFile(unittest.TestCase):
    """Test ReviewPeekFile value object."""

    def test_valid_peek_items(self):
        """Test creating peek file with valid items."""
        items = ["tag1", "tag2", "tag3"]
        peek_file = ReviewPeekFile(items)

        self.assertEqual(len(peek_file.peek_items), 3)
        self.assertTrue(peek_file.has_items)
        self.assertEqual(peek_file.items_count, 3)

    def test_empty_peek_items(self):
        """Test creating peek file with empty items."""
        peek_file = ReviewPeekFile([])

        self.assertEqual(len(peek_file.peek_items), 0)
        self.assertFalse(peek_file.has_items)
        self.assertEqual(peek_file.items_count, 0)

    def test_format_for_dreview(self):
        """Test formatting peek items for dreview command."""
        items = ["tag1", "tag2", "tag3"]
        peek_file = ReviewPeekFile(items)

        formatted = peek_file.format_for_dreview()
        self.assertEqual(formatted, "tag1,tag2,tag3")

    def test_from_file_content(self):
        """Test creating peek file from file content."""
        content = "tag1\ntag2\n# comment\ntag3\n"
        peek_file = ReviewPeekFile.from_file_content(content)

        self.assertEqual(len(peek_file.peek_items), 3)
        self.assertIn("tag1", peek_file.peek_items)
        self.assertIn("tag2", peek_file.peek_items)
        self.assertIn("tag3", peek_file.peek_items)

    def test_from_uploaded_file_with_tags(self):
        """Test creating peek file from uploaded file with tags."""
        file_dict = {'tags': ['tag1', 'tag2', 'tag3']}
        peek_file = ReviewPeekFile.from_uploaded_file(file_dict)

        self.assertEqual(len(peek_file.peek_items), 3)

    def test_from_uploaded_file_with_content(self):
        """Test creating peek file from uploaded file with base64 content."""
        import base64
        content = "tag1\ntag2\ntag3"
        encoded_content = base64.b64encode(
            content.encode('utf-8')).decode('utf-8')
        file_dict = {'content': encoded_content}

        peek_file = ReviewPeekFile.from_uploaded_file(file_dict)

        self.assertEqual(len(peek_file.peek_items), 3)

    def test_invalid_peek_items_raise_error(self):
        """Test that invalid peek items raise error."""
        with self.assertRaises(ValueError):
            ReviewPeekFile("not a list")

        with self.assertRaises(ValueError):
            ReviewPeekFile([123, "tag2"])


class TestReviewProcessingOptions(unittest.TestCase):
    """Test ReviewProcessingOptions value object."""

    def setUp(self):
        """Set up test fixtures."""
        self.time_range = ReviewTimeRange(
            "2023-01-01 10:00:00", "2023-01-01 12:00:00")
        self.peek_file = ReviewPeekFile(["tag1", "tag2"])

    def test_valid_processing_options(self):
        """Test creating valid processing options."""
        options = ReviewProcessingOptions(
            time_range=self.time_range,
            peek_file=self.peek_file,
            dump_all=False,
            frequency_minutes=5.0
        )

        self.assertEqual(options.time_range, self.time_range)
        self.assertEqual(options.peek_file, self.peek_file)
        self.assertFalse(options.dump_all)
        self.assertEqual(options.frequency_minutes, 5.0)

    def test_dump_all_processing_options(self):
        """Test creating dump all processing options."""
        options = ReviewProcessingOptions(
            time_range=self.time_range,
            peek_file=self.peek_file,
            dump_all=True
        )

        self.assertTrue(options.dump_all)
        self.assertIsNone(options.frequency_minutes)

    def test_get_dreview_duration_arg(self):
        """Test getting dreview duration argument."""
        # Test with frequency
        options = ReviewProcessingOptions(
            time_range=self.time_range,
            peek_file=self.peek_file,
            dump_all=False,
            frequency_minutes=10.0
        )
        self.assertEqual(options.get_dreview_duration_arg(), "-DT=10.0")

        # Test with dump_all
        options = ReviewProcessingOptions(
            time_range=self.time_range,
            peek_file=self.peek_file,
            dump_all=True
        )
        self.assertEqual(options.get_dreview_duration_arg(), "")

    def test_invalid_time_range_raises_error(self):
        """Test that invalid time range raises error."""
        with self.assertRaises(ValueError):
            ReviewProcessingOptions(
                time_range="not a time range",
                peek_file=self.peek_file
            )

    def test_invalid_peek_file_raises_error(self):
        """Test that invalid peek file raises error."""
        with self.assertRaises(ValueError):
            ReviewProcessingOptions(
                time_range=self.time_range,
                peek_file="not a peek file"
            )

    def test_invalid_frequency_raises_error(self):
        """Test that invalid frequency raises error."""
        with self.assertRaises(ValueError):
            ReviewProcessingOptions(
                time_range=self.time_range,
                peek_file=self.peek_file,
                dump_all=False,
                frequency_minutes=-5.0  # Negative frequency
            )


class TestReviewFileInfo(unittest.TestCase):
    """Test ReviewFileInfo dataclass."""

    def test_create_review_file_info(self):
        """Test creating ReviewFileInfo."""
        info = ReviewFileInfo(
            file_path="test.review",
            filename="test.review",
            file_size_bytes=1024,
            last_modified=datetime.now(),
            exists=True,
            is_valid=True
        )

        self.assertEqual(info.file_path, "test.review")
        self.assertEqual(info.filename, "test.review")
        self.assertEqual(info.file_size_bytes, 1024)
        self.assertTrue(info.exists)
        self.assertTrue(info.is_valid)


class TestReviewConversionResult(unittest.TestCase):
    """Test ReviewConversionResult dataclass."""

    def test_successful_conversion_result(self):
        """Test creating successful conversion result."""
        result = ReviewConversionResult(
            success=True,
            output_directory="c:/temp",
            processed_files_count=5,
            merged_file_path="c:/temp/merged.csv",
            processing_time_seconds=120.5
        )

        self.assertTrue(result.success)
        self.assertEqual(result.output_directory, "c:/temp")
        self.assertEqual(result.processed_files_count, 5)
        self.assertEqual(result.merged_file_path, "c:/temp/merged.csv")
        self.assertEqual(result.processing_time_seconds, 120.5)

    def test_failed_conversion_result(self):
        """Test creating failed conversion result."""
        result = ReviewConversionResult(
            success=False,
            output_directory="c:/temp",
            processed_files_count=0,
            error_message="Processing failed"
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Processing failed")


class TestReviewConversionConstants(unittest.TestCase):
    """Test ReviewConversionConstants."""

    def test_constants_values(self):
        """Test constants have expected values."""
        self.assertEqual(ReviewConversionConstants.REVIEW_EXTENSION, ".review")
        self.assertEqual(ReviewConversionConstants.CSV_EXTENSION, ".csv")
        self.assertEqual(
            ReviewConversionConstants.DEFAULT_MERGED_FILENAME, "MergedReviewData.csv")
        self.assertEqual(
            ReviewConversionConstants.DREVIEW_EXECUTABLE, "dreview.exe")

    def test_get_system_info(self):
        """Test getting system information."""
        info = ReviewConversionConstants.get_system_info()

        self.assertIn("component", info)
        self.assertIn("version", info)
        self.assertIn("architecture", info)
        self.assertIn("supported_formats", info)
        self.assertIn("dependencies", info)
        self.assertIn("features", info)

        self.assertEqual(info["component"], "Review to CSV Converter")
        self.assertIn(".review", info["supported_formats"])


if __name__ == '__main__':
    unittest.main()
