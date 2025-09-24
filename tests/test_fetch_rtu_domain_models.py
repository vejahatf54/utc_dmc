"""
Unit tests for RTU Fetch Data domain models.
Tests new value objects created for the refactored fetch RTU data functionality.
"""

import unittest
from datetime import date, datetime
from pathlib import Path
import tempfile
import os

from domain.rtu_models import (
    RtuDate, RtuDateRange, RtuServerFilter, RtuLineSelection, 
    RtuOutputDirectory, RtuFetchResult, RtuFetchConstants
)


class TestRtuDate(unittest.TestCase):
    """Test RTU date value object."""

    def test_valid_date_creation(self):
        """Test creating RTU date with valid date."""
        test_date = date(2024, 1, 15)
        rtu_date = RtuDate(test_date)
        
        self.assertEqual(rtu_date.value, test_date)
        self.assertEqual(rtu_date.folder_name, "20240115")
        self.assertEqual(rtu_date.iso_format, "2024-01-15")
        self.assertEqual(rtu_date.display_format, "January 15, 2024")

    def test_invalid_future_date(self):
        """Test that future dates are rejected."""
        future_date = date(2030, 12, 31)
        with self.assertRaises(ValueError) as context:
            RtuDate(future_date)
        self.assertIn("cannot be in the future", str(context.exception))

    def test_invalid_too_old_date(self):
        """Test that very old dates are rejected."""
        old_date = date(1999, 1, 1)
        with self.assertRaises(ValueError) as context:
            RtuDate(old_date)
        self.assertIn("cannot be before 2000-01-01", str(context.exception))

    def test_invalid_type(self):
        """Test that non-date types are rejected."""
        with self.assertRaises(ValueError):
            RtuDate("2024-01-15")
        
        with self.assertRaises(ValueError):
            RtuDate(None)


class TestRtuDateRange(unittest.TestCase):
    """Test RTU date range value object."""

    def test_valid_date_range(self):
        """Test creating valid date range."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        date_range = RtuDateRange(start_date, end_date)
        
        self.assertEqual(date_range.start_date.value, start_date)
        self.assertEqual(date_range.end_date.value, end_date)
        self.assertEqual(date_range.day_count, 31)
        self.assertFalse(date_range.is_single_date)

    def test_single_date_to_today(self):
        """Test single date range (to today)."""
        start_date = date(2024, 1, 1)
        date_range = RtuDateRange(start_date)  # No end date = today
        
        self.assertEqual(date_range.start_date.value, start_date)
        self.assertEqual(date_range.end_date.value, date.today())
        self.assertTrue(date_range.is_single_date)

    def test_invalid_date_order(self):
        """Test that start date after end date is rejected."""
        start_date = date(2024, 1, 31)
        end_date = date(2024, 1, 1)
        
        with self.assertRaises(ValueError) as context:
            RtuDateRange(start_date, end_date)
        self.assertIn("Start date cannot be after end date", str(context.exception))

    def test_date_list_generation(self):
        """Test generating list of dates in range."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 3)
        date_range = RtuDateRange(start_date, end_date)
        
        date_list = date_range.date_list
        expected_dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
        self.assertEqual(date_list, expected_dates)

    def test_contains_date(self):
        """Test date containment check."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        date_range = RtuDateRange(start_date, end_date)
        
        self.assertTrue(date_range.contains_date(date(2024, 1, 15)))
        self.assertTrue(date_range.contains_date(date(2024, 1, 1)))
        self.assertTrue(date_range.contains_date(date(2024, 1, 31)))
        self.assertFalse(date_range.contains_date(date(2023, 12, 31)))
        self.assertFalse(date_range.contains_date(date(2024, 2, 1)))


class TestRtuServerFilter(unittest.TestCase):
    """Test RTU server filter value object."""

    def test_empty_filter(self):
        """Test empty filter (no filtering)."""
        filter_obj = RtuServerFilter(None)
        self.assertTrue(filter_obj.is_empty)
        self.assertFalse(filter_obj.is_wildcard)
        self.assertTrue(filter_obj.matches("any_server"))

        filter_obj2 = RtuServerFilter("")
        self.assertTrue(filter_obj2.is_empty)

    def test_exact_match_filter(self):
        """Test exact match filter."""
        filter_obj = RtuServerFilter("LPP02WVSPSS15")
        self.assertFalse(filter_obj.is_empty)
        self.assertFalse(filter_obj.is_wildcard)
        
        self.assertTrue(filter_obj.matches("LPP02WVSPSS15"))
        self.assertTrue(filter_obj.matches("lpp02wvspss15"))  # Case insensitive
        self.assertFalse(filter_obj.matches("LPP02WVSPSS16"))

    def test_wildcard_filter(self):
        """Test wildcard filter."""
        filter_obj = RtuServerFilter("LPP02WV*")
        self.assertFalse(filter_obj.is_empty)
        self.assertTrue(filter_obj.is_wildcard)
        
        self.assertTrue(filter_obj.matches("LPP02WVSPSS15"))
        self.assertTrue(filter_obj.matches("LPP02WVTEST"))
        self.assertFalse(filter_obj.matches("LPP03WVSPSS15"))

    def test_complex_wildcard_filter(self):
        """Test complex wildcard patterns."""
        filter_obj = RtuServerFilter("LPP02*SPSS*")
        self.assertTrue(filter_obj.is_wildcard)
        
        self.assertTrue(filter_obj.matches("LPP02WVSPSS15"))
        self.assertTrue(filter_obj.matches("LPP02ABSPSSTEST"))
        self.assertFalse(filter_obj.matches("LPP02WVTEST"))


class TestRtuLineSelection(unittest.TestCase):
    """Test RTU line selection value object."""

    def test_valid_line_selection(self):
        """Test valid line selection."""
        lines = ["l01", "l02", "l03"]
        selection = RtuLineSelection(lines)
        
        self.assertEqual(selection.line_ids, lines)
        self.assertEqual(selection.count, 3)
        self.assertFalse(selection.is_empty)
        self.assertTrue(selection.contains_line("l01"))
        self.assertFalse(selection.contains_line("l04"))

    def test_single_line_selection(self):
        """Test single line selection."""
        lines = ["l01"]
        selection = RtuLineSelection(lines)
        
        self.assertEqual(selection.count, 1)
        self.assertEqual(str(selection), "1 line: l01")

    def test_multiple_lines_string_representation(self):
        """Test string representation for multiple lines."""
        lines = ["l01", "l02", "l03", "l04", "l05"]
        selection = RtuLineSelection(lines)
        
        str_repr = str(selection)
        self.assertIn("5 lines:", str_repr)
        self.assertIn("l01, l02, l03...", str_repr)

    def test_empty_line_selection(self):
        """Test that empty line selection is rejected."""
        with self.assertRaises(ValueError) as context:
            RtuLineSelection([])
        self.assertIn("At least one line must be selected", str(context.exception))

    def test_invalid_line_types(self):
        """Test that non-string line IDs are rejected."""
        with self.assertRaises(ValueError):
            RtuLineSelection([1, 2, 3])
        
        with self.assertRaises(ValueError):
            RtuLineSelection(["l01", ""])


class TestRtuOutputDirectory(unittest.TestCase):
    """Test RTU output directory value object."""

    def test_valid_directory_creation(self):
        """Test creating valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = RtuOutputDirectory(temp_dir)
            
            self.assertTrue(output_dir.exists)
            self.assertTrue(output_dir.is_writable)
            self.assertEqual(str(output_dir.path), str(Path(temp_dir).resolve()))

    def test_directory_creation(self):
        """Test automatic directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "new_subdir")
            output_dir = RtuOutputDirectory(new_dir)
            
            # Directory should be created when checking writability
            self.assertTrue(output_dir.is_writable)
            self.assertTrue(os.path.exists(new_dir))

    def test_line_subdirectory_creation(self):
        """Test creating line subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = RtuOutputDirectory(temp_dir)
            line_dir = output_dir.create_line_subdirectory("l01")
            
            self.assertIsInstance(line_dir, RtuOutputDirectory)
            self.assertTrue(str(line_dir.path).endswith("l01"))

    def test_invalid_directory_path(self):
        """Test invalid directory paths."""
        with self.assertRaises(ValueError):
            RtuOutputDirectory("")
        
        with self.assertRaises(ValueError):
            RtuOutputDirectory(None)


class TestRtuFetchResult(unittest.TestCase):
    """Test RTU fetch result value object."""

    def test_successful_result(self):
        """Test successful fetch result."""
        result = RtuFetchResult.create_success(
            lines_processed=3,
            total_files_extracted=15,
            extraction_errors=["error1"],
            missing_dates=["missing1"]
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.lines_processed, 3)
        self.assertEqual(result.total_files_extracted, 15)
        self.assertTrue(result.has_errors)
        self.assertTrue(result.has_missing_dates)
        self.assertIn("Success!", result.summary_text)

    def test_failed_result(self):
        """Test failed fetch result."""
        result = RtuFetchResult.create_failure("Network error")
        
        self.assertFalse(result.success)
        self.assertEqual(result.lines_processed, 0)
        self.assertEqual(result.total_files_extracted, 0)
        self.assertFalse(result.has_errors)
        self.assertFalse(result.has_missing_dates)
        self.assertIn("Failed:", result.summary_text)

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = RtuFetchResult.create_success(2, 10)
        result_dict = result.to_dict()
        
        self.assertTrue(result_dict['success'])
        self.assertEqual(result_dict['summary']['lines_processed'], 2)
        self.assertEqual(result_dict['summary']['total_files_extracted'], 10)


class TestRtuFetchConstants(unittest.TestCase):
    """Test RTU fetch constants."""

    def test_system_info(self):
        """Test system info generation."""
        system_info = RtuFetchConstants.get_system_info()
        
        self.assertIn('zip_file_pattern', system_info)
        self.assertIn('dt_file_extension', system_info)
        self.assertIn('default_max_parallel_workers', system_info)
        self.assertEqual(system_info['dt_file_extension'], '.dt')
        self.assertEqual(system_info['default_max_parallel_workers'], 4)


if __name__ == '__main__':
    unittest.main()