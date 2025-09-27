"""
Unit tests for text replacement services.
Tests business logic with proper separation of concerns and dependency injection.
"""

import unittest
import tempfile
import base64
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from services.text_replacement_service_v2 import (
    RegexTextReplacer, CsvSubstitutionLoader, FileSystemFileProcessor,
    TextReplacementService, LegacyTextReplacementService,
    create_text_replacer, create_substitution_loader, create_file_processor,
    create_text_replacement_service
)
from validation.text_replacement_validators import SubstitutionDataValidator
from core.interfaces import Result


class TestRegexTextReplacer(unittest.TestCase):
    """Test cases for RegexTextReplacer."""

    def setUp(self):
        """Set up test fixtures."""
        self.replacer = RegexTextReplacer()

    def test_case_sensitive_replacement(self):
        """Test case-sensitive text replacement."""
        content = "Hello World, hello world"
        result = self.replacer.replace_text(
            content, "hello", "hi", match_case=True)

        self.assertEqual(result, "Hello World, hi world")

    def test_case_insensitive_replacement(self):
        """Test case-insensitive text replacement."""
        content = "Hello World, hello world"
        result = self.replacer.replace_text(
            content, "hello", "hi", match_case=False)

        self.assertEqual(result, "hi World, hi world")

    def test_empty_content(self):
        """Test replacement with empty content."""
        result = self.replacer.replace_text("", "old", "new", match_case=True)

        self.assertEqual(result, "")

    def test_empty_old_text(self):
        """Test replacement with empty old text."""
        content = "Hello World"
        result = self.replacer.replace_text(
            content, "", "new", match_case=True)

        self.assertEqual(result, content)

    def test_special_regex_characters(self):
        """Test replacement with special regex characters."""
        content = "Price: $100.50"
        result = self.replacer.replace_text(
            content, "$100.50", "$200.00", match_case=True)

        self.assertEqual(result, "Price: $200.00")

    def test_multiple_occurrences(self):
        """Test replacement of multiple occurrences."""
        content = "foo bar foo baz foo"
        result = self.replacer.replace_text(
            content, "foo", "qux", match_case=True)

        self.assertEqual(result, "qux bar qux baz qux")


class TestCsvSubstitutionLoader(unittest.TestCase):
    """Test cases for CsvSubstitutionLoader."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_validator = Mock(spec=SubstitutionDataValidator)
        self.loader = CsvSubstitutionLoader(self.mock_validator)

    def test_successful_loading(self):
        """Test successful substitution loading."""
        substitutions = [("old1", "new1"), ("old2", "new2")]
        self.mock_validator.validate.return_value = Result.ok(
            substitutions, "Success")

        result = self.loader.load_substitutions("encoded_csv_content")

        self.assertTrue(result.success)
        self.assertEqual(result.data, substitutions)
        self.mock_validator.validate.assert_called_once_with(
            "encoded_csv_content")

    def test_validation_failure(self):
        """Test loading with validation failure."""
        self.mock_validator.validate.return_value = Result.fail(
            "Validation error")

        result = self.loader.load_substitutions("invalid_content")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Validation error")

    def test_default_validator(self):
        """Test loader with default validator."""
        loader = CsvSubstitutionLoader()

        # Test with valid CSV content
        csv_content = "old1,new1\nold2,new2\n"
        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')

        result = loader.load_substitutions(encoded_content)

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)


class TestFileSystemFileProcessor(unittest.TestCase):
    """Test cases for FileSystemFileProcessor."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = FileSystemFileProcessor()
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

    def test_find_files_success(self):
        """Test successful file finding."""
        result = self.processor.find_files(self.temp_dir, ["txt"])

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)  # test.txt and sub.txt
        self.assertIn("Found 2 files", result.message)

    def test_find_files_no_matches(self):
        """Test finding files with no matches."""
        result = self.processor.find_files(self.temp_dir, ["cpp"])

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 0)
        self.assertIn("No files found", result.message)

    def test_find_files_invalid_directory(self):
        """Test finding files in invalid directory."""
        result = self.processor.find_files("/nonexistent", ["txt"])

        self.assertFalse(result.success)
        self.assertIn("does not exist", result.error)

    def test_process_file_success(self):
        """Test successful file processing."""
        file_path = Path(self.temp_dir) / "test.txt"
        file_path.write_text("old text here")

        mock_replacer = Mock()
        mock_replacer.replace_text.return_value = "new text here"

        substitutions = [("old", "new")]

        result = self.processor.process_file(
            str(file_path), substitutions, mock_replacer, True
        )

        self.assertTrue(result.success)
        self.assertEqual(file_path.read_text(), "new text here")
        mock_replacer.replace_text.assert_called_once_with(
            "old text here", "old", "new", True)

    def test_process_file_no_changes(self):
        """Test file processing with no changes."""
        file_path = Path(self.temp_dir) / "test.txt"
        original_content = "unchanged content"
        file_path.write_text(original_content)

        mock_replacer = Mock()
        mock_replacer.replace_text.return_value = original_content  # No changes

        substitutions = [("nonexistent", "replacement")]

        result = self.processor.process_file(
            str(file_path), substitutions, mock_replacer, True
        )

        self.assertTrue(result.success)
        self.assertEqual(file_path.read_text(), original_content)

    def test_process_nonexistent_file(self):
        """Test processing nonexistent file."""
        nonexistent_path = str(Path(self.temp_dir) / "nonexistent.txt")
        mock_replacer = Mock()

        result = self.processor.process_file(
            nonexistent_path, [], mock_replacer, True
        )

        self.assertFalse(result.success)
        self.assertIn("File not found", result.error)

    def test_process_directory_instead_of_file(self):
        """Test processing directory instead of file."""
        mock_replacer = Mock()

        result = self.processor.process_file(
            self.temp_dir, [], mock_replacer, True
        )

        self.assertFalse(result.success)
        self.assertIn("not a file", result.error)

    @patch('pathlib.Path.read_text')
    def test_process_file_permission_error(self, mock_read):
        """Test processing file with permission error."""
        mock_read.side_effect = PermissionError("Permission denied")

        file_path = Path(self.temp_dir) / "test.txt"
        mock_replacer = Mock()

        result = self.processor.process_file(
            str(file_path), [], mock_replacer, True
        )

        self.assertFalse(result.success)
        self.assertIn("Permission denied", result.error)


class TestTextReplacementService(unittest.TestCase):
    """Test cases for TextReplacementService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_loader = Mock()
        self.mock_processor = Mock()
        self.mock_replacer = Mock()

        self.service = TextReplacementService(
            self.mock_loader, self.mock_processor, self.mock_replacer
        )

    def test_successful_replacement(self):
        """Test successful text replacement operation."""
        # Mock substitution loading
        substitutions = [("old1", "new1"), ("old2", "new2")]
        self.mock_loader.load_substitutions.return_value = Result.ok(
            substitutions)

        # Mock file finding
        files = ["file1.txt", "file2.txt"]
        self.mock_processor.find_files.return_value = Result.ok(
            files, "Found 2 files")

        # Mock file processing
        self.mock_processor.process_file.return_value = Result.ok(
            True, "Success")

        result = self.service.replace_text_in_files(
            "/test/dir", "encoded_csv", ["txt"], True
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data['processed_files'], 2)
        self.assertEqual(result.data['total_files'], 2)
        self.assertEqual(len(result.data['errors']), 0)

        # Verify calls
        self.mock_loader.load_substitutions.assert_called_once_with(
            "encoded_csv")
        self.mock_processor.find_files.assert_called_once_with(
            "/test/dir", ["txt"])
        self.assertEqual(self.mock_processor.process_file.call_count, 2)

    def test_substitution_loading_failure(self):
        """Test handling of substitution loading failure."""
        self.mock_loader.load_substitutions.return_value = Result.fail(
            "Load error")

        result = self.service.replace_text_in_files(
            "/test/dir", "invalid_csv", ["txt"], True
        )

        self.assertFalse(result.success)
        self.assertIn("Failed to load substitutions", result.error)

    def test_file_finding_failure(self):
        """Test handling of file finding failure."""
        substitutions = [("old", "new")]
        self.mock_loader.load_substitutions.return_value = Result.ok(
            substitutions)
        self.mock_processor.find_files.return_value = Result.fail(
            "Directory error")

        result = self.service.replace_text_in_files(
            "/invalid/dir", "encoded_csv", ["txt"], True
        )

        self.assertFalse(result.success)
        self.assertIn("Failed to find files", result.error)

    def test_no_files_found(self):
        """Test handling when no files are found."""
        substitutions = [("old", "new")]
        self.mock_loader.load_substitutions.return_value = Result.ok(
            substitutions)
        self.mock_processor.find_files.return_value = Result.ok(
            [], "No files found")

        result = self.service.replace_text_in_files(
            "/test/dir", "encoded_csv", ["txt"], True
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data['processed_files'], 0)
        self.assertEqual(result.data['total_files'], 0)
        self.assertIn("No files found to process", result.data['message'])

    def test_partial_processing_success(self):
        """Test partial success with some file processing errors."""
        substitutions = [("old", "new")]
        self.mock_loader.load_substitutions.return_value = Result.ok(
            substitutions)

        files = ["file1.txt", "file2.txt", "file3.txt"]
        self.mock_processor.find_files.return_value = Result.ok(files)

        # Mock mixed results for file processing
        self.mock_processor.process_file.side_effect = [
            Result.ok(True, "Success"),
            Result.fail("Permission denied"),
            Result.ok(True, "Success")
        ]

        result = self.service.replace_text_in_files(
            "/test/dir", "encoded_csv", ["txt"], True
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data['processed_files'], 2)
        self.assertEqual(result.data['total_files'], 3)
        self.assertEqual(len(result.data['errors']), 1)
        self.assertIn("Permission denied", result.data['errors'][0])

    def test_default_dependencies(self):
        """Test service with default dependencies."""
        service = TextReplacementService()

        # Should not raise exceptions and should have dependencies
        self.assertIsNotNone(service._substitution_loader)
        self.assertIsNotNone(service._file_processor)
        self.assertIsNotNone(service._text_replacer)


class TestLegacyTextReplacementService(unittest.TestCase):
    """Test cases for LegacyTextReplacementService."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.csv_file = Path(self.temp_dir) / "test.csv"
        self.csv_file.write_text("old,new\nfoo,bar\n")

        self.legacy_service = LegacyTextReplacementService()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_set_csv_file_valid(self):
        """Test setting valid CSV file."""
        self.legacy_service.set_csv_file(str(self.csv_file))

        self.assertEqual(self.legacy_service.csv_file_path, str(self.csv_file))

    def test_set_csv_file_nonexistent(self):
        """Test setting nonexistent CSV file."""
        with self.assertRaises(FileNotFoundError):
            self.legacy_service.set_csv_file("nonexistent.csv")

    def test_set_folder_path_valid(self):
        """Test setting valid folder path."""
        self.legacy_service.set_folder_path(self.temp_dir)

        self.assertEqual(self.legacy_service.folder_path, self.temp_dir)

    def test_set_folder_path_nonexistent(self):
        """Test setting nonexistent folder path."""
        with self.assertRaises(FileNotFoundError):
            self.legacy_service.set_folder_path("/nonexistent")

    @patch.object(TextReplacementService, 'replace_text_in_files')
    def test_replace_in_files_success(self, mock_replace):
        """Test successful text replacement through legacy wrapper."""
        mock_replace.return_value = Result.ok({
            'processed_files': 2,
            'total_files': 2,
            'errors': []
        })

        self.legacy_service.set_csv_file(str(self.csv_file))
        self.legacy_service.set_folder_path(self.temp_dir)

        # Should not raise exception
        self.legacy_service.replace_in_files(["txt"], False)

        # Verify the new service was called with base64 encoded content
        mock_replace.assert_called_once()
        args, kwargs = mock_replace.call_args

        self.assertEqual(args[0], self.temp_dir)  # directory
        self.assertIsInstance(args[1], str)  # encoded content
        self.assertEqual(args[2], ["txt"])  # extensions
        self.assertFalse(args[3])  # match_case

    def test_replace_in_files_not_configured(self):
        """Test replacement without setting paths."""
        with self.assertRaises(ValueError):
            self.legacy_service.replace_in_files(["txt"], False)

    @patch.object(TextReplacementService, 'replace_text_in_files')
    def test_replace_in_files_service_error(self, mock_replace):
        """Test handling of service error through legacy wrapper."""
        mock_replace.return_value = Result.fail("Service error")

        self.legacy_service.set_csv_file(str(self.csv_file))
        self.legacy_service.set_folder_path(self.temp_dir)

        with self.assertRaises(Exception) as context:
            self.legacy_service.replace_in_files(["txt"], False)

        self.assertIn("Service error", str(context.exception))


class TestServiceFactories(unittest.TestCase):
    """Test cases for service factory functions."""

    def test_create_text_replacer(self):
        """Test text replacer factory."""
        replacer = create_text_replacer()
        self.assertIsInstance(replacer, RegexTextReplacer)

    def test_create_substitution_loader(self):
        """Test substitution loader factory."""
        loader = create_substitution_loader()
        self.assertIsInstance(loader, CsvSubstitutionLoader)

    def test_create_file_processor(self):
        """Test file processor factory."""
        processor = create_file_processor()
        self.assertIsInstance(processor, FileSystemFileProcessor)

    def test_create_text_replacement_service(self):
        """Test text replacement service factory."""
        service = create_text_replacement_service()
        self.assertIsInstance(service, TextReplacementService)


if __name__ == '__main__':
    unittest.main()
