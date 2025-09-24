"""
Unit tests for archive domain models.
Tests all value objects and data structures for proper validation and behavior.
"""

import unittest
from datetime import datetime, date, timedelta
from pathlib import Path
import tempfile
import os
from domain.archive_models import (
    ArchiveDate, PipelineLine, ArchivePath, OutputDirectory,
    ArchiveFileInfo, FetchArchiveRequest, FetchArchiveResult,
    ArchiveConversionConstants
)


class TestArchiveDate(unittest.TestCase):
    """Test cases for ArchiveDate value object."""

    def test_valid_datetime_creation(self):
        """Test creating ArchiveDate with valid datetime."""
        dt = datetime(2023, 12, 26, 14, 30, 0)
        archive_date = ArchiveDate(dt)
        
        # ArchiveDate normalizes time to midnight
        expected_dt = datetime(2023, 12, 26, 0, 0, 0)
        self.assertEqual(archive_date.value, expected_dt)
        self.assertEqual(archive_date.date_obj, dt.date())
        self.assertEqual(archive_date.folder_name, "20231226")
        self.assertEqual(archive_date.display_format, "December 26, 2023")
        self.assertEqual(archive_date.iso_format, "2023-12-26")

    def test_valid_date_creation(self):
        """Test creating ArchiveDate with valid date object."""
        d = date(2023, 12, 26)
        archive_date = ArchiveDate(d)
        
        expected_dt = datetime.combine(d, datetime.min.time())
        self.assertEqual(archive_date.value, expected_dt)
        self.assertEqual(archive_date.date_obj, d)
        self.assertEqual(archive_date.folder_name, "20231226")

    def test_future_date_rejection(self):
        """Test that future dates are rejected."""
        future_date = datetime.now() + timedelta(days=1)
        
        with self.assertRaises(ValueError) as context:
            ArchiveDate(future_date)
        self.assertIn("Archive date cannot be in the future", str(context.exception))

    def test_too_old_date_rejection(self):
        """Test that dates before 2000 are rejected."""
        old_date = datetime(1999, 12, 31)
        
        with self.assertRaises(ValueError) as context:
            ArchiveDate(old_date)
        self.assertIn("Archive date cannot be before 2000-01-01", str(context.exception))

    def test_invalid_type_rejection(self):
        """Test that invalid types are rejected."""
        with self.assertRaises(ValueError) as context:
            ArchiveDate("2023-12-26")
        self.assertIn("Archive date must be a datetime or date object", str(context.exception))

    def test_string_representation(self):
        """Test string representations."""
        dt = datetime(2023, 12, 26)
        archive_date = ArchiveDate(dt)
        
        self.assertEqual(str(archive_date), "2023-12-26")
        self.assertEqual(repr(archive_date), "ArchiveDate('2023-12-26')")


class TestPipelineLine(unittest.TestCase):
    """Test cases for PipelineLine value object."""

    def test_valid_line_creation(self):
        """Test creating PipelineL ne with valid ID."""
        line = PipelineLine("l01")
        
        self.assertEqual(line.value, "l01")
        self.assertEqual(line.display_label, "l01")

    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed."""
        line = PipelineLine("  l02  ")
        
        self.assertEqual(line.value, "l02")

    def test_empty_string_rejection(self):
        """Test that empty strings are rejected."""
        with self.assertRaises(ValueError) as context:
            PipelineLine("")
        self.assertIn("Pipeline line ID cannot be empty", str(context.exception))

    def test_whitespace_only_rejection(self):
        """Test that whitespace-only strings are rejected."""
        with self.assertRaises(ValueError) as context:
            PipelineLine("   ")
        self.assertIn("Pipeline line ID cannot be empty", str(context.exception))

    def test_none_rejection(self):
        """Test that None is rejected."""
        with self.assertRaises(ValueError) as context:
            PipelineLine(None)
        self.assertIn("Pipeline line ID must be a string", str(context.exception))

    def test_long_string_rejection(self):
        """Test that very long strings are rejected."""
        long_string = "a" * 51
        
        with self.assertRaises(ValueError) as context:
            PipelineLine(long_string)
        self.assertIn("Pipeline line ID cannot exceed 50 characters", str(context.exception))

    def test_string_representation(self):
        """Test string representations."""
        line = PipelineLine("l01")
        
        self.assertEqual(str(line), "l01")
        self.assertEqual(repr(line), "PipelineLine('l01')")


class TestArchivePath(unittest.TestCase):
    """Test cases for ArchivePath value object."""

    def test_valid_path_creation(self):
        """Test creating ArchivePath with valid path."""
        path_str = r"\\server\archive"
        archive_path = ArchivePath(path_str)
        
        self.assertEqual(archive_path.value, path_str)
        self.assertIsInstance(archive_path.path_obj, Path)

    def test_empty_path_rejection(self):
        """Test that empty paths are rejected."""
        with self.assertRaises(ValueError) as context:
            ArchivePath("")
        self.assertIn("Archive path cannot be empty", str(context.exception))

    def test_none_rejection(self):
        """Test that None is rejected."""
        with self.assertRaises(ValueError) as context:
            ArchivePath(None)
        self.assertIn("Archive path must be a string", str(context.exception))

    def test_get_line_path(self):
        """Test getting line-specific path."""
        archive_path = ArchivePath(r"\\server\archive")
        line_path = archive_path.get_line_path("l01")
        
        expected = Path(r"\\server\archive") / "l01"
        self.assertEqual(line_path, expected)

    def test_get_date_path(self):
        """Test getting date-specific path."""
        archive_path = ArchivePath(r"\\server\archive")
        archive_date = ArchiveDate(datetime(2023, 12, 26))
        date_path = archive_path.get_date_path("l01", archive_date)
        
        expected = Path(r"\\server\archive") / "l01" / "20231226"
        self.assertEqual(date_path, expected)

    def test_string_representation(self):
        """Test string representations."""
        path_str = r"\\server\archive"
        archive_path = ArchivePath(path_str)
        
        self.assertEqual(str(archive_path), path_str)
        self.assertEqual(repr(archive_path), f"ArchivePath('{path_str}')")


class TestOutputDirectory(unittest.TestCase):
    """Test cases for OutputDirectory value object."""

    def test_valid_directory_creation(self):
        """Test creating OutputDirectory with valid path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = OutputDirectory(temp_dir)
            
            self.assertEqual(output_dir.value, str(Path(temp_dir).resolve()))
            self.assertTrue(output_dir.exists())

    def test_create_if_not_exists(self):
        """Test creating directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "new_directory")
            output_dir = OutputDirectory(new_dir)
            
            # Should create the directory
            self.assertTrue(output_dir.exists())

    def test_get_line_output_path(self):
        """Test getting line-specific output path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = OutputDirectory(temp_dir)
            archive_date = ArchiveDate(datetime(2023, 12, 26))
            line_path = output_dir.get_line_output_path("l01", archive_date)
            
            expected = Path(temp_dir) / "l01_20231226"
            self.assertEqual(line_path, expected)

    def test_empty_path_rejection(self):
        """Test that empty paths are rejected."""
        with self.assertRaises(ValueError) as context:
            OutputDirectory("")
        self.assertIn("Output directory path cannot be empty", str(context.exception))

    def test_none_rejection(self):
        """Test that None is rejected."""
        with self.assertRaises(ValueError) as context:
            OutputDirectory(None)
        self.assertIn("Output directory path must be a string", str(context.exception))


class TestArchiveFileInfo(unittest.TestCase):
    """Test cases for ArchiveFileInfo data structure."""

    def test_creation(self):
        """Test creating ArchiveFileInfo."""
        file_info = ArchiveFileInfo(
            original_zip="archive.zip",
            original_filename="data.txt",
            extracted_file="/path/to/extracted.txt",
            filename="extracted.txt",
            size_bytes=1024
        )
        
        self.assertEqual(file_info.original_zip, "archive.zip")
        self.assertEqual(file_info.original_filename, "data.txt")
        self.assertEqual(file_info.extracted_file, "/path/to/extracted.txt")
        self.assertEqual(file_info.filename, "extracted.txt")
        self.assertEqual(file_info.size_bytes, 1024)

    def test_immutability(self):
        """Test that ArchiveFileInfo is immutable."""
        file_info = ArchiveFileInfo(
            original_zip="archive.zip",
            original_filename="data.txt",
            extracted_file="/path/to/extracted.txt",
            filename="extracted.txt",
            size_bytes=1024
        )
        
        # Should not be able to modify fields
        with self.assertRaises(AttributeError):
            file_info.size_bytes = 2048


class TestFetchArchiveRequest(unittest.TestCase):
    """Test cases for FetchArchiveRequest data structure."""

    def test_valid_creation(self):
        """Test creating FetchArchiveRequest with valid data."""
        archive_date = ArchiveDate(datetime(2023, 12, 26))
        pipeline_lines = [PipelineLine("l01"), PipelineLine("l02")]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_directory = OutputDirectory(temp_dir)
            
            request = FetchArchiveRequest(
                archive_date=archive_date,
                pipeline_lines=pipeline_lines,
                output_directory=output_directory
            )
            
            self.assertEqual(request.archive_date, archive_date)
            self.assertEqual(request.pipeline_lines, pipeline_lines)
            self.assertEqual(request.output_directory, output_directory)

    def test_empty_lines_rejection(self):
        """Test that empty pipeline lines list is rejected."""
        archive_date = ArchiveDate(datetime(2023, 12, 26))
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_directory = OutputDirectory(temp_dir)
            
            with self.assertRaises(ValueError) as context:
                FetchArchiveRequest(
                    archive_date=archive_date,
                    pipeline_lines=[],
                    output_directory=output_directory
                )
            self.assertIn("At least one pipeline line must be specified", str(context.exception))

    def test_none_lines_rejection(self):
        """Test that None pipeline lines is rejected."""
        archive_date = ArchiveDate(datetime(2023, 12, 26))
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_directory = OutputDirectory(temp_dir)
            
            with self.assertRaises(ValueError) as context:
                FetchArchiveRequest(
                    archive_date=archive_date,
                    pipeline_lines=None,
                    output_directory=output_directory
                )
            self.assertIn("At least one pipeline line must be specified", str(context.exception))


class TestFetchArchiveResult(unittest.TestCase):
    """Test cases for FetchArchiveResult data structure."""

    def test_creation(self):
        """Test creating FetchArchiveResult."""
        files = [
            ArchiveFileInfo(
                original_zip="archive1.zip",
                original_filename="data1.txt",
                extracted_file="/path/to/data1.txt",
                filename="data1.txt",
                size_bytes=1024
            )
        ]
        
        result = FetchArchiveResult(
            success=True,
            files=files,
            failed_lines=[],
            message="Success",
            output_directory="/output",
            fetch_date="2023-12-26",
            requested_lines=["l01", "l02"]
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.files, files)
        self.assertEqual(result.files_count, 1)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.processed_lines_count, 2)

    def test_property_calculations(self):
        """Test calculated properties."""
        files = [
            ArchiveFileInfo(
                original_zip="archive1.zip",
                original_filename="data1.txt",
                extracted_file="/path/to/data1.txt",
                filename="data1.txt",
                size_bytes=1024
            ),
            ArchiveFileInfo(
                original_zip="archive2.zip",
                original_filename="data2.txt",
                extracted_file="/path/to/data2.txt",
                filename="data2.txt",
                size_bytes=2048
            )
        ]
        
        failed_lines = [{"line_id": "l03", "error": "Not found"}]
        
        result = FetchArchiveResult(
            success=True,
            files=files,
            failed_lines=failed_lines,
            message="Partial success",
            output_directory="/output",
            fetch_date="2023-12-26",
            requested_lines=["l01", "l02", "l03"]
        )
        
        self.assertEqual(result.files_count, 2)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.processed_lines_count, 2)  # 3 requested - 1 failed


class TestArchiveConversionConstants(unittest.TestCase):
    """Test cases for ArchiveConversionConstants."""

    def test_constants(self):
        """Test that constants are properly defined."""
        self.assertEqual(ArchiveConversionConstants.ARCHIVE_EXTENSIONS, ['.zip'])
        self.assertEqual(ArchiveConversionConstants.FOLDER_DATE_FORMAT, '%Y%m%d')
        self.assertEqual(ArchiveConversionConstants.DISPLAY_DATE_FORMAT, '%B %d, %Y')
        self.assertEqual(ArchiveConversionConstants.ISO_DATE_FORMAT, '%Y-%m-%d')
        self.assertEqual(ArchiveConversionConstants.DEFAULT_TIMEOUT, 30)
        self.assertEqual(ArchiveConversionConstants.MAX_FILENAME_LENGTH, 255)

    def test_system_info(self):
        """Test getting system info."""
        info = ArchiveConversionConstants.get_system_info()
        
        self.assertIsInstance(info, dict)
        self.assertIn('supported_archive_formats', info)
        self.assertIn('folder_date_format', info)
        self.assertIn('display_date_format', info)
        self.assertIn('iso_date_format', info)
        self.assertIn('default_timeout', info)
        self.assertIn('max_filename_length', info)
        
        self.assertEqual(info['supported_archive_formats'], ['.zip'])
        self.assertEqual(info['default_timeout'], 30)