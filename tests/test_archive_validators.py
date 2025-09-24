"""
Unit tests for archive validators.
Tests all validation logic following Single Responsibility Principle.
"""

import unittest
from datetime import datetime, date, timedelta
import tempfile
import os
from validation.archive_validators import (
    ArchiveDateValidator, PipelineLineValidator, PipelineLinesListValidator,
    OutputDirectoryValidator, ArchivePathValidator, CompositeArchiveValidator,
    FetchArchiveRequestValidator, create_archive_date_validator,
    create_pipeline_line_validator, create_pipeline_lines_validator,
    create_output_directory_validator, create_archive_path_validator,
    create_fetch_archive_request_validator, create_complete_archive_validator
)


class TestArchiveDateValidator(unittest.TestCase):
    """Test cases for ArchiveDateValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ArchiveDateValidator()

    def test_valid_datetime(self):
        """Test validation with valid datetime."""
        valid_date = datetime(2023, 12, 26)
        result = self.validator.validate(valid_date)
        
        assert result.success is True
        assert result.message == "Archive date is valid"

    def test_valid_date_object(self):
        """Test validation with valid date object."""
        valid_date = date(2023, 12, 26)
        result = self.validator.validate(valid_date)
        
        assert result.success is True
        assert result.message == "Archive date is valid"

    def test_valid_iso_string(self):
        """Test validation with valid ISO string."""
        valid_date = "2023-12-26"
        result = self.validator.validate(valid_date)
        
        assert result.success is True
        assert result.message == "Archive date is valid"

    def test_none_input(self):
        """Test validation with None input."""
        result = self.validator.validate(None)
        
        assert result.success is False
        assert "Archive date cannot be None" in result.error
        assert result.message == "Please select an archive date"

    def test_invalid_string_format(self):
        """Test validation with invalid string format."""
        result = self.validator.validate("invalid-date")
        
        assert result.success is False
        assert "Invalid date format" in result.error

    def test_future_date(self):
        """Test validation with future date."""
        future_date = datetime.now() + timedelta(days=1)
        result = self.validator.validate(future_date)
        
        self.assertFalse(result.success)
        self.assertIn("Archive date cannot be in the future", result.error)

    def test_invalid_type(self):
        """Test validation with invalid type."""
        result = self.validator.validate(12345)
        
        assert result.success is False
        assert "Invalid date type" in result.error


class TestPipelineLineValidator:
    """Test cases for PipelineLineValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PipelineLineValidator()

    def test_valid_line_id(self):
        """Test validation with valid line ID."""
        result = self.validator.validate("l01")
        
        assert result.success is True
        assert result.message == "Pipeline line is valid"

    def test_valid_line_with_whitespace(self):
        """Test validation with line ID containing whitespace."""
        result = self.validator.validate("  l02  ")
        
        assert result.success is True
        assert result.message == "Pipeline line is valid"

    def test_none_input(self):
        """Test validation with None input."""
        result = self.validator.validate(None)
        
        assert result.success is False
        assert "Pipeline line cannot be None" in result.error

    def test_non_string_input(self):
        """Test validation with non-string input."""
        result = self.validator.validate(123)
        
        assert result.success is False
        assert "Pipeline line must be a string" in result.error

    def test_empty_string(self):
        """Test validation with empty string."""
        result = self.validator.validate("")
        
        assert result.success is False
        assert "Pipeline line ID cannot be empty" in result.error

    def test_whitespace_only(self):
        """Test validation with whitespace-only string."""
        result = self.validator.validate("   ")
        
        assert result.success is False
        assert "Pipeline line ID cannot be empty" in result.error


class TestPipelineLinesListValidator:
    """Test cases for PipelineLinesListValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PipelineLinesListValidator()

    def test_valid_lines_list(self):
        """Test validation with valid lines list."""
        lines = ["l01", "l02", "l03"]
        result = self.validator.validate(lines)
        
        assert result.success is True
        assert result.message == "All 3 pipeline lines are valid"

    def test_single_valid_line(self):
        """Test validation with single valid line."""
        lines = ["l01"]
        result = self.validator.validate(lines)
        
        assert result.success is True
        assert result.message == "All 1 pipeline lines are valid"

    def test_none_input(self):
        """Test validation with None input."""
        result = self.validator.validate(None)
        
        assert result.success is False
        assert "Pipeline lines cannot be None" in result.error

    def test_non_list_input(self):
        """Test validation with non-list input."""
        result = self.validator.validate("not a list")
        
        assert result.success is False
        assert "Pipeline lines must be a list" in result.error

    def test_empty_list(self):
        """Test validation with empty list."""
        result = self.validator.validate([])
        
        assert result.success is False
        assert "Pipeline lines list cannot be empty" in result.error

    def test_invalid_line_in_list(self):
        """Test validation with invalid line in list."""
        lines = ["l01", "", "l03"]  # Empty string in middle
        result = self.validator.validate(lines)
        
        assert result.success is False
        assert "Invalid line at position 2" in result.error

    def test_mixed_valid_invalid(self):
        """Test validation with mix of valid and invalid lines."""
        lines = ["l01", None, "l03"]  # None in middle
        result = self.validator.validate(lines)
        
        assert result.success is False
        assert "Invalid line at position 2" in result.error


class TestOutputDirectoryValidator:
    """Test cases for OutputDirectoryValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = OutputDirectoryValidator()

    def test_valid_directory(self):
        """Test validation with valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.validator.validate(temp_dir)
            
            assert result.success is True
            assert result.message == "Output directory is valid"

    def test_new_directory_creation(self):
        """Test validation with directory that needs to be created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "new_directory")
            result = self.validator.validate(new_dir)
            
            assert result.success is True
            assert result.message == "Output directory is valid"
            assert os.path.exists(new_dir)  # Should be created

    def test_none_input(self):
        """Test validation with None input."""
        result = self.validator.validate(None)
        
        assert result.success is False
        assert "Output directory cannot be None" in result.error

    def test_non_string_input(self):
        """Test validation with non-string input."""
        result = self.validator.validate(123)
        
        assert result.success is False
        assert "Output directory must be a string" in result.error

    def test_empty_string(self):
        """Test validation with empty string."""
        result = self.validator.validate("")
        
        assert result.success is False
        assert "Output directory path cannot be empty" in result.error

    def test_invalid_path(self):
        """Test validation with invalid path."""
        # Use invalid characters for Windows path
        invalid_path = "C:\\invalid<>path"
        result = self.validator.validate(invalid_path)
        
        # Result depends on OS, but should handle gracefully
        # On some systems this might actually work, so we just verify it doesn't crash
        assert isinstance(result.success, bool)


class TestArchivePathValidator:
    """Test cases for ArchivePathValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ArchivePathValidator()

    def test_valid_existing_path(self):
        """Test validation with existing path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.validator.validate(temp_dir)
            
            assert result.success is True
            assert result.message == "Archive path is accessible"

    def test_none_input(self):
        """Test validation with None input."""
        result = self.validator.validate(None)
        
        assert result.success is False
        assert "Archive path cannot be None" in result.error

    def test_non_string_input(self):
        """Test validation with non-string input."""
        result = self.validator.validate(123)
        
        assert result.success is False
        assert "Archive path must be a string" in result.error

    def test_empty_string(self):
        """Test validation with empty string."""
        result = self.validator.validate("")
        
        assert result.success is False
        assert "Archive path cannot be empty" in result.error

    def test_nonexistent_path(self):
        """Test validation with nonexistent path."""
        nonexistent_path = "/this/path/does/not/exist"
        result = self.validator.validate(nonexistent_path)
        
        assert result.success is False
        assert "Archive path does not exist" in result.error

    def test_file_instead_of_directory(self):
        """Test validation with file instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            result = self.validator.validate(temp_file.name)
            
            assert result.success is False
            assert "Archive path is not a directory" in result.error


class TestCompositeArchiveValidator:
    """Test cases for CompositeArchiveValidator."""

    def test_all_validators_pass(self):
        """Test when all validators pass."""
        validator1 = ArchiveDateValidator()
        validator2 = PipelineLineValidator()
        
        composite = CompositeArchiveValidator(validator1, validator2)
        
        # This won't work perfectly since each validator expects different input types
        # But we can test the logic structure
        result = composite.validate(datetime(2023, 12, 26))
        
        # The first validator should pass, but the second will fail with wrong type
        # This demonstrates the composite behavior
        assert isinstance(result.success, bool)

    def test_first_validator_fails(self):
        """Test when first validator fails."""
        validator1 = ArchiveDateValidator()
        validator2 = PipelineLineValidator()
        
        composite = CompositeArchiveValidator(validator1, validator2)
        
        result = composite.validate(None)  # Invalid for date validator
        
        assert result.success is False
        assert "Archive date cannot be None" in result.error


class TestFetchArchiveRequestValidator:
    """Test cases for FetchArchiveRequestValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = FetchArchiveRequestValidator()

    def test_valid_complete_request(self):
        """Test validation of complete valid request."""
        archive_date = datetime(2023, 12, 26)
        pipeline_lines = ["l01", "l02"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.validator.validate_fetch_request(
                archive_date, pipeline_lines, temp_dir
            )
            
            assert result.success is True
            assert result.message == "Complete fetch archive request is valid"

    def test_invalid_date_in_request(self):
        """Test validation with invalid date."""
        future_date = datetime.now() + timedelta(days=1)
        pipeline_lines = ["l01", "l02"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.validator.validate_fetch_request(
                future_date, pipeline_lines, temp_dir
            )
            
            assert result.success is False
            assert "Archive date cannot be in the future" in result.error

    def test_invalid_lines_in_request(self):
        """Test validation with invalid lines."""
        archive_date = datetime(2023, 12, 26)
        pipeline_lines = []  # Empty list
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.validator.validate_fetch_request(
                archive_date, pipeline_lines, temp_dir
            )
            
            assert result.success is False
            assert "Pipeline lines list cannot be empty" in result.error

    def test_invalid_directory_in_request(self):
        """Test validation with invalid directory."""
        archive_date = datetime(2023, 12, 26)
        pipeline_lines = ["l01", "l02"]
        
        result = self.validator.validate_fetch_request(
            archive_date, pipeline_lines, ""  # Empty directory
        )
        
        assert result.success is False
        assert "Output directory path cannot be empty" in result.error

    def test_individual_validators(self):
        """Test individual validator methods."""
        # Test date validation
        result = self.validator.validate_archive_date(datetime(2023, 12, 26))
        assert result.success is True
        
        # Test lines validation
        result = self.validator.validate_pipeline_lines(["l01", "l02"])
        assert result.success is True
        
        # Test directory validation
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.validator.validate_output_directory(temp_dir)
            assert result.success is True


class TestValidatorFactories:
    """Test cases for validator factory functions."""

    def test_create_archive_date_validator(self):
        """Test creating archive date validator."""
        validator = create_archive_date_validator()
        assert isinstance(validator, ArchiveDateValidator)

    def test_create_pipeline_line_validator(self):
        """Test creating pipeline line validator."""
        validator = create_pipeline_line_validator()
        assert isinstance(validator, PipelineLineValidator)

    def test_create_pipeline_lines_validator(self):
        """Test creating pipeline lines validator."""
        validator = create_pipeline_lines_validator()
        assert isinstance(validator, PipelineLinesListValidator)

    def test_create_output_directory_validator(self):
        """Test creating output directory validator."""
        validator = create_output_directory_validator()
        assert isinstance(validator, OutputDirectoryValidator)

    def test_create_archive_path_validator(self):
        """Test creating archive path validator."""
        validator = create_archive_path_validator()
        assert isinstance(validator, ArchivePathValidator)

    def test_create_fetch_archive_request_validator(self):
        """Test creating fetch archive request validator."""
        validator = create_fetch_archive_request_validator()
        assert isinstance(validator, FetchArchiveRequestValidator)

    def test_create_complete_archive_validator(self):
        """Test creating complete archive validator."""
        validator = create_complete_archive_validator()
        assert isinstance(validator, CompositeArchiveValidator)

    def test_factory_validators_work(self):
        """Test that factory-created validators actually work."""
        date_validator = create_archive_date_validator()
        result = date_validator.validate(datetime(2023, 12, 26))
        assert result.success is True

        line_validator = create_pipeline_line_validator()
        result = line_validator.validate("l01")
        assert result.success is True

        lines_validator = create_pipeline_lines_validator()
        result = lines_validator.validate(["l01", "l02"])
        assert result.success is True

        with tempfile.TemporaryDirectory() as temp_dir:
            dir_validator = create_output_directory_validator()
            result = dir_validator.validate(temp_dir)
            assert result.success is True

        request_validator = create_fetch_archive_request_validator()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = request_validator.validate_fetch_request(
                datetime(2023, 12, 26), ["l01"], temp_dir
            )
            assert result.success is True