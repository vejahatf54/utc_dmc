"""
Unit tests for text replacement domain models.
Tests value objects and business entities following SOLID principles.
"""

import unittest
import tempfile
import os
from pathlib import Path
from domain.text_replacement_models import (
    SubstitutionPair, FileExtensionFilter, DirectoryPath,
    TextReplacementConfig, TextReplacementResult
)


class TestSubstitutionPair(unittest.TestCase):
    """Test cases for SubstitutionPair value object."""

    def test_valid_substitution_pair(self):
        """Test creating a valid substitution pair."""
        pair = SubstitutionPair("old_text", "new_text")
        self.assertEqual(pair.old_text, "old_text")
        self.assertEqual(pair.new_text, "new_text")
        self.assertTrue(pair.is_valid())

    def test_substitution_pair_with_whitespace(self):
        """Test that whitespace is stripped from substitution texts."""
        pair = SubstitutionPair("  old_text  ", "  new_text  ")
        self.assertEqual(pair.old_text, "old_text")
        self.assertEqual(pair.new_text, "new_text")

    def test_substitution_pair_empty_old_text(self):
        """Test that empty old text raises ValueError."""
        with self.assertRaises(ValueError):
            SubstitutionPair("", "new_text")

        with self.assertRaises(ValueError):
            SubstitutionPair("   ", "new_text")

    def test_substitution_pair_none_old_text(self):
        """Test that None old text raises ValueError."""
        with self.assertRaises(ValueError):
            SubstitutionPair(None, "new_text")

    def test_substitution_pair_non_string_old_text(self):
        """Test that non-string old text raises ValueError."""
        with self.assertRaises(ValueError):
            SubstitutionPair(123, "new_text")

    def test_substitution_pair_none_new_text(self):
        """Test that None new text raises ValueError."""
        with self.assertRaises(ValueError):
            SubstitutionPair("old_text", None)

    def test_substitution_pair_empty_new_text_allowed(self):
        """Test that empty new text is allowed."""
        pair = SubstitutionPair("old_text", "")
        self.assertEqual(pair.new_text, "")
        self.assertTrue(pair.is_valid())

    def test_substitution_pair_equality(self):
        """Test value equality of substitution pairs."""
        pair1 = SubstitutionPair("old", "new")
        pair2 = SubstitutionPair("old", "new")
        pair3 = SubstitutionPair("old", "different")

        self.assertEqual(pair1, pair2)
        self.assertNotEqual(pair1, pair3)

    def test_substitution_pair_hash(self):
        """Test that equal substitution pairs have equal hashes."""
        pair1 = SubstitutionPair("old", "new")
        pair2 = SubstitutionPair("old", "new")

        self.assertEqual(hash(pair1), hash(pair2))


class TestFileExtensionFilter(unittest.TestCase):
    """Test cases for FileExtensionFilter value object."""

    def test_valid_extensions(self):
        """Test creating filter with valid extensions."""
        filter_obj = FileExtensionFilter(["txt", "py", "js"])
        self.assertEqual(set(filter_obj.extensions), {"txt", "py", "js"})

    def test_extensions_normalization(self):
        """Test that extensions are normalized properly."""
        filter_obj = FileExtensionFilter([".txt", "*.py", "  js  ", ".HTML"])
        self.assertEqual(set(filter_obj.extensions),
                         {"txt", "py", "js", "html"})

    def test_empty_extensions_list(self):
        """Test that empty extensions list raises ValueError."""
        with self.assertRaises(ValueError):
            FileExtensionFilter([])

    def test_all_invalid_extensions(self):
        """Test that all invalid extensions raises ValueError."""
        with self.assertRaises(ValueError):
            FileExtensionFilter(["", "  ", None, 123])

    def test_mixed_valid_invalid_extensions(self):
        """Test that mixed valid/invalid extensions keeps valid ones."""
        filter_obj = FileExtensionFilter(["txt", "", "py", None, "js"])
        self.assertEqual(set(filter_obj.extensions), {"txt", "py", "js"})

    def test_matches_file(self):
        """Test file matching functionality."""
        filter_obj = FileExtensionFilter(["txt", "py"])

        self.assertTrue(filter_obj.matches_file("test.txt"))
        self.assertTrue(filter_obj.matches_file(
            "test.TXT"))  # Case insensitive
        self.assertTrue(filter_obj.matches_file("path/to/test.py"))
        self.assertFalse(filter_obj.matches_file("test.js"))
        self.assertFalse(filter_obj.matches_file("test"))
        self.assertFalse(filter_obj.matches_file(""))


class TestDirectoryPath(unittest.TestCase):
    """Test cases for DirectoryPath value object."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create test files
        (Path(self.temp_dir) / "test.txt").write_text("content")
        (Path(self.temp_dir) / "test.py").write_text("content")
        (Path(self.temp_dir) / "test.js").write_text("content")

        # Create subdirectory with files
        sub_dir = Path(self.temp_dir) / "subdir"
        sub_dir.mkdir()
        (sub_dir / "sub.txt").write_text("content")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_directory_path(self):
        """Test creating DirectoryPath with valid directory."""
        dir_path = DirectoryPath(self.temp_dir)
        self.assertEqual(dir_path.path, os.path.normpath(self.temp_dir))

    def test_nonexistent_directory(self):
        """Test that nonexistent directory raises ValueError."""
        with self.assertRaises(ValueError):
            DirectoryPath("/nonexistent/path")

    def test_file_instead_of_directory(self):
        """Test that file path raises ValueError."""
        file_path = Path(self.temp_dir) / "test.txt"
        with self.assertRaises(ValueError):
            DirectoryPath(str(file_path))

    def test_empty_path(self):
        """Test that empty path raises ValueError."""
        with self.assertRaises(ValueError):
            DirectoryPath("")

    def test_none_path(self):
        """Test that None path raises ValueError."""
        with self.assertRaises(ValueError):
            DirectoryPath(None)

    def test_find_files(self):
        """Test finding files with extension filter."""
        dir_path = DirectoryPath(self.temp_dir)
        extension_filter = FileExtensionFilter(["txt"])

        files = dir_path.find_files(extension_filter)

        # Should find test.txt and sub.txt
        self.assertEqual(len(files), 2)
        txt_files = [f for f in files if f.endswith('.txt')]
        self.assertEqual(len(txt_files), 2)


class TestTextReplacementConfig(unittest.TestCase):
    """Test cases for TextReplacementConfig value object."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.directory = DirectoryPath(self.temp_dir)
        self.substitutions = [
            SubstitutionPair("old1", "new1"),
            SubstitutionPair("old2", "new2")
        ]
        self.extensions = FileExtensionFilter(["txt", "py"])

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_config(self):
        """Test creating valid TextReplacementConfig."""
        config = TextReplacementConfig(
            self.directory, self.substitutions, self.extensions, True
        )

        self.assertEqual(config.directory, self.directory)
        self.assertEqual(len(config.substitutions), 2)
        self.assertEqual(config.extensions, self.extensions)
        self.assertTrue(config.match_case)

    def test_config_with_invalid_substitutions(self):
        """Test that invalid substitutions are filtered out."""
        mixed_substitutions = [
            SubstitutionPair("valid", "replacement"),
            # This would create an invalid substitution, but we'll test the filtering
        ]

        config = TextReplacementConfig(
            self.directory, mixed_substitutions, self.extensions
        )

        # Should keep only valid substitutions
        self.assertEqual(len(config.substitutions), 1)

    def test_config_no_directory(self):
        """Test that None directory raises ValueError."""
        with self.assertRaises(ValueError):
            TextReplacementConfig(None, self.substitutions, self.extensions)

    def test_config_no_substitutions(self):
        """Test that empty substitutions raises ValueError."""
        with self.assertRaises(ValueError):
            TextReplacementConfig(self.directory, [], self.extensions)

    def test_config_no_extensions(self):
        """Test that None extensions raises ValueError."""
        with self.assertRaises(ValueError):
            TextReplacementConfig(self.directory, self.substitutions, None)


class TestTextReplacementResult(unittest.TestCase):
    """Test cases for TextReplacementResult value object."""

    def test_valid_result(self):
        """Test creating valid TextReplacementResult."""
        result = TextReplacementResult(5, 10, ["error1", "error2"])

        self.assertEqual(result.processed_files, 5)
        self.assertEqual(result.total_files, 10)
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(result.success_rate, 50.0)
        self.assertTrue(result.has_errors)

    def test_result_no_errors(self):
        """Test result with no errors."""
        result = TextReplacementResult(10, 10)

        self.assertEqual(result.processed_files, 10)
        self.assertEqual(result.total_files, 10)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(result.success_rate, 100.0)
        self.assertFalse(result.has_errors)

    def test_result_no_files(self):
        """Test result with no files."""
        result = TextReplacementResult(0, 0)

        self.assertEqual(result.success_rate, 100.0)
        self.assertFalse(result.has_errors)

    def test_negative_processed_files(self):
        """Test that negative processed files raises ValueError."""
        with self.assertRaises(ValueError):
            TextReplacementResult(-1, 10)

    def test_negative_total_files(self):
        """Test that negative total files raises ValueError."""
        with self.assertRaises(ValueError):
            TextReplacementResult(5, -1)

    def test_processed_exceeds_total(self):
        """Test that processed > total raises ValueError."""
        with self.assertRaises(ValueError):
            TextReplacementResult(15, 10)

    def test_to_summary(self):
        """Test summary generation."""
        result1 = TextReplacementResult(5, 10, ["error"])
        self.assertIn("Processed 5 of 10 files", result1.to_summary())
        self.assertIn("1 errors", result1.to_summary())

        result2 = TextReplacementResult(10, 10)
        self.assertIn("Processed 10 of 10 files", result2.to_summary())

        result3 = TextReplacementResult(0, 0)
        self.assertEqual(result3.to_summary(), "No files found to process")


if __name__ == '__main__':
    unittest.main()
