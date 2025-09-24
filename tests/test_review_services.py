"""
Unit tests for Review services.
Tests business logic and service layer implementations.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from datetime import datetime
from pathlib import Path

from core.interfaces import Result
from services.review_file_reader_service import ReviewFileReaderService
from services.review_processor_service import ReviewProcessorService
from services.review_to_csv_converter_service import ReviewToCsvConverterService
from domain.review_models import ReviewFilePath, ReviewFileInfo


class TestReviewFileReaderService(unittest.TestCase):
    """Test ReviewFileReaderService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = ReviewFileReaderService()

    def test_get_file_info_valid_file(self):
        """Test getting file info for valid file."""
        # Create a temporary review file
        with tempfile.NamedTemporaryFile(suffix='.review', delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name

        try:
            result = self.service.get_file_info(temp_file_path)

            self.assertTrue(result.success)
            self.assertIn('file_path', result.data)
            self.assertIn('filename', result.data)
            self.assertIn('file_size_bytes', result.data)
            self.assertIn('exists', result.data)
            self.assertTrue(result.data['exists'])
        finally:
            os.unlink(temp_file_path)

    def test_get_file_info_nonexistent_file(self):
        """Test getting file info for nonexistent file."""
        result = self.service.get_file_info("nonexistent.review")

        self.assertFalse(result.success)
        self.assertIn("File not found", result.error)

    def test_get_file_info_invalid_extension(self):
        """Test getting file info for invalid extension."""
        result = self.service.get_file_info("test.txt")

        self.assertFalse(result.success)
        self.assertIn("must have .review extension", result.error)

    def test_validate_file_valid(self):
        """Test validating a valid file."""
        # Create a temporary review file
        with tempfile.NamedTemporaryFile(suffix='.review', delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name

        try:
            result = self.service.validate_file(temp_file_path)

            self.assertTrue(result.success)
            self.assertTrue(result.data)
        finally:
            os.unlink(temp_file_path)

    def test_validate_file_nonexistent(self):
        """Test validating nonexistent file."""
        result = self.service.validate_file("nonexistent.review")

        self.assertFalse(result.success)
        self.assertIn("File not found", result.error)

    def test_validate_file_empty(self):
        """Test validating empty file."""
        # Create an empty review file
        with tempfile.NamedTemporaryFile(suffix='.review', delete=False) as temp_file:
            temp_file_path = temp_file.name

        try:
            result = self.service.validate_file(temp_file_path)

            self.assertFalse(result.success)
            self.assertIn("File is empty", result.error)
        finally:
            os.unlink(temp_file_path)


class TestReviewProcessorService(unittest.TestCase):
    """Test ReviewProcessorService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = ReviewProcessorService()

    def test_validate_processing_options_valid(self):
        """Test validating valid processing options."""
        result = self.service.validate_processing_options(
            start_time="2023-01-01 10:00:00",
            end_time="2023-01-01 12:00:00",
            peek_items=["tag1", "tag2"]
        )

        self.assertTrue(result.success)
        self.assertTrue(result.data)

    def test_validate_processing_options_invalid_time_range(self):
        """Test validating invalid time range."""
        result = self.service.validate_processing_options(
            start_time="2023-01-01 12:00:00",  # After end time
            end_time="2023-01-01 10:00:00",
            peek_items=["tag1", "tag2"]
        )

        self.assertFalse(result.success)
        self.assertIn("start time must be before end time",
                      result.error.lower())

    @patch('subprocess.Popen')
    def test_process_review_file_successful(self, mock_popen):
        """Test successful review file processing."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process completed
        mock_process.communicate.return_value = ("output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.review', delete=False) as input_file:
            input_file.write(b"test content")
            input_file_path = input_file.name

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as output_file:
            output_file.write(b"csv content")
            output_file_path = output_file.name

        try:
            result = self.service.process_review_file(
                review_file_path=input_file_path,
                output_csv_path=output_file_path,
                start_time="2023-01-01 10:00:00",
                end_time="2023-01-01 12:00:00",
                peek_items=["tag1", "tag2"]
            )

            self.assertTrue(result.success)
            self.assertIn('input_file', result.data)
            self.assertIn('output_file', result.data)
            self.assertIn('processing_time_seconds', result.data)

        finally:
            os.unlink(input_file_path)
            os.unlink(output_file_path)

    def test_process_review_file_nonexistent_input(self):
        """Test processing nonexistent input file."""
        result = self.service.process_review_file(
            review_file_path="nonexistent.review",
            output_csv_path="output.csv",
            start_time="2023-01-01 10:00:00",
            end_time="2023-01-01 12:00:00"
        )

        self.assertFalse(result.success)
        self.assertIn("not found", result.error)


class TestReviewToCsvConverterService(unittest.TestCase):
    """Test ReviewToCsvConverterService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_file_reader = Mock()
        self.mock_processor = Mock()
        self.service = ReviewToCsvConverterService(
            self.mock_file_reader, self.mock_processor)

    def test_get_system_info(self):
        """Test getting system information."""
        result = self.service.get_system_info()

        self.assertTrue(result.success)
        self.assertIn('component', result.data)
        self.assertIn('version', result.data)
        self.assertEqual(result.data['component'], 'Review to CSV Converter')

    def test_convert_directory_nonexistent(self):
        """Test converting nonexistent directory."""
        result = self.service.convert_directory(
            review_directory_path="nonexistent_directory",
            output_directory="output"
        )

        self.assertFalse(result.success)
        self.assertIn("not found", result.error)

    def test_convert_files_empty_list(self):
        """Test converting empty file list."""
        result = self.service.convert_files([], "output")

        self.assertFalse(result.success)
        self.assertIn("No files provided", result.error)

    def test_convert_files_invalid_output_directory(self):
        """Test converting with invalid output directory."""
        result = self.service.convert_files(
            ["test.review"],
            "nonexistent_output_directory"
        )

        self.assertFalse(result.success)
        self.assertIn("Output directory not found", result.error)

    def test_cancel_conversion(self):
        """Test cancelling conversion."""
        result = self.service.cancel_conversion()

        self.assertTrue(result.success)
        self.assertTrue(result.data)

    def test_parse_processing_options_missing_times(self):
        """Test parsing processing options with missing times."""
        options_dict = {}
        result = self.service._parse_processing_options(options_dict)

        self.assertFalse(result.success)
        self.assertIn("required", result.error)

    def test_parse_processing_options_valid(self):
        """Test parsing valid processing options."""
        options_dict = {
            'start_time': '2023-01-01 10:00:00',
            'end_time': '2023-01-01 12:00:00',
            'peek_file': {'tags': ['tag1', 'tag2']},
            'dump_all': False,
            'frequency_minutes': 5.0
        }

        result = self.service._parse_processing_options(options_dict)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
        self.assertFalse(result.data.dump_all)
        self.assertEqual(result.data.frequency_minutes, 5.0)

    def test_merge_csv_files_successful(self):
        """Test successful CSV file merging."""
        # Create temporary directory with CSV files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test CSV files
            csv_file1 = os.path.join(temp_dir, "test1.csv")
            csv_file2 = os.path.join(temp_dir, "test2.csv")

            with open(csv_file1, 'w') as f:
                f.write("col1,col2\nunits,GPM\nval1,val2\n")
            with open(csv_file2, 'w') as f:
                f.write("col1,col2\nunits,GPM\nval3,val4\n")

            # Test uses real CSV files - no mocking needed

            result = self.service._merge_csv_files(
                output_directory=Path(temp_dir),
                merged_filename="merged.csv"
            )

            self.assertTrue(result.success)
            self.assertIn('merged_file_path', result.data)


if __name__ == '__main__':
    unittest.main()
