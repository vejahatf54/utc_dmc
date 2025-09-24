"""
Archive input validators following Single Responsibility Principle.
Each validator has one specific responsibility for archive-related validation.
"""

from typing import Any, List
from datetime import datetime, date
from pathlib import Path
from core.interfaces import IValidator, IArchiveValidator, Result
from domain.archive_models import ArchiveDate, PipelineLine, OutputDirectory


class ArchiveDateValidator(IValidator):
    """Validates archive date input."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate archive date input format and constraints."""
        if value is None:
            return Result.fail("Archive date cannot be None", "Please select an archive date")

        # Handle string inputs (ISO format)
        if isinstance(value, str):
            try:
                # Try to parse ISO format
                date_obj = datetime.fromisoformat(value).date()
                value = date_obj
            except ValueError:
                return Result.fail("Invalid date format", "Please provide a valid date in YYYY-MM-DD format")

        # Handle date objects
        if isinstance(value, date):
            value = datetime.combine(value, datetime.min.time())
        elif not isinstance(value, datetime):
            return Result.fail("Invalid date type", "Date must be a valid date object or string")

        # Validate using domain model
        try:
            ArchiveDate(value)
            return Result.ok(True, "Archive date is valid")
        except ValueError as e:
            return Result.fail(str(e), "Please select a valid archive date")


class PipelineLineValidator(IValidator):
    """Validates individual pipeline line input."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate pipeline line identifier."""
        if value is None:
            return Result.fail("Pipeline line cannot be None", "Please provide a valid pipeline line ID")

        if not isinstance(value, str):
            return Result.fail("Pipeline line must be a string", "Pipeline line ID must be text")

        # Validate using domain model
        try:
            PipelineLine(value)
            return Result.ok(True, "Pipeline line is valid")
        except ValueError as e:
            return Result.fail(str(e), "Please provide a valid pipeline line ID")


class PipelineLinesListValidator(IValidator):
    """Validates list of pipeline lines."""

    def __init__(self):
        self._line_validator = PipelineLineValidator()

    def validate(self, value: Any) -> Result[bool]:
        """Validate list of pipeline line identifiers."""
        if value is None:
            return Result.fail("Pipeline lines cannot be None", "Please select at least one pipeline line")

        if not isinstance(value, list):
            return Result.fail("Pipeline lines must be a list", "Pipeline lines must be provided as a list")

        if not value:
            return Result.fail("Pipeline lines list cannot be empty", "Please select at least one pipeline line")

        # Validate each line
        for i, line_id in enumerate(value):
            result = self._line_validator.validate(line_id)
            if not result.success:
                return Result.fail(f"Invalid line at position {i + 1}: {result.error}", 
                                   f"Line {i + 1} is invalid")

        return Result.ok(True, f"All {len(value)} pipeline lines are valid")


class OutputDirectoryValidator(IValidator):
    """Validates output directory path."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate output directory path."""
        if value is None:
            return Result.fail("Output directory cannot be None", "Please select an output directory")

        if not isinstance(value, str):
            return Result.fail("Output directory must be a string", "Output directory path must be text")

        # Validate using domain model
        try:
            OutputDirectory(value)
            return Result.ok(True, "Output directory is valid")
        except ValueError as e:
            return Result.fail(str(e), "Please select a valid output directory")


class ArchivePathValidator(IValidator):
    """Validates archive UNC path accessibility."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate archive path accessibility."""
        if value is None:
            return Result.fail("Archive path cannot be None", "Archive path is required")

        if not isinstance(value, str):
            return Result.fail("Archive path must be a string", "Archive path must be text")

        if not value.strip():
            return Result.fail("Archive path cannot be empty", "Archive path is required")

        try:
            path_obj = Path(value)
            if not path_obj.exists():
                return Result.fail("Archive path does not exist", f"Cannot access archive path: {value}")
            
            if not path_obj.is_dir():
                return Result.fail("Archive path is not a directory", f"Archive path must be a directory: {value}")

            return Result.ok(True, "Archive path is accessible")
        
        except PermissionError:
            return Result.fail("Permission denied accessing archive path", 
                               f"No permission to access: {value}")
        except Exception as e:
            return Result.fail(f"Error accessing archive path: {str(e)}", 
                               f"Cannot validate archive path: {value}")


class CompositeArchiveValidator(IValidator):
    """Validator that combines multiple archive validators using AND logic."""

    def __init__(self, *validators: IValidator):
        self._validators = validators

    def validate(self, value: Any) -> Result[bool]:
        """Validate using all validators. Fails if any validator fails."""
        for validator in self._validators:
            result = validator.validate(value)
            if not result.success:
                return result

        return Result.ok(True, "All archive validations passed")


class FetchArchiveRequestValidator(IArchiveValidator):
    """Comprehensive validator for fetch archive requests."""

    def __init__(self):
        self._date_validator = ArchiveDateValidator()
        self._lines_validator = PipelineLinesListValidator()
        self._output_validator = OutputDirectoryValidator()

    def validate(self, value: Any) -> Result[bool]:
        """Validate general input (not used in this context)."""
        return Result.ok(True, "General validation passed")

    def validate_archive_date(self, archive_date: Any) -> Result[bool]:
        """Validate archive date."""
        return self._date_validator.validate(archive_date)

    def validate_pipeline_lines(self, pipeline_lines: List[str]) -> Result[bool]:
        """Validate pipeline line selections."""
        return self._lines_validator.validate(pipeline_lines)

    def validate_output_directory(self, output_directory: str) -> Result[bool]:
        """Validate output directory path."""
        return self._output_validator.validate(output_directory)

    def validate_fetch_request(self, archive_date: Any, pipeline_lines: List[str], 
                               output_directory: str) -> Result[bool]:
        """Validate complete fetch archive request."""
        # Validate date
        date_result = self.validate_archive_date(archive_date)
        if not date_result.success:
            return date_result

        # Validate lines
        lines_result = self.validate_pipeline_lines(pipeline_lines)
        if not lines_result.success:
            return lines_result

        # Validate output directory
        output_result = self.validate_output_directory(output_directory)
        if not output_result.success:
            return output_result

        return Result.ok(True, "Complete fetch archive request is valid")


# Factory functions for creating pre-configured validators
def create_archive_date_validator() -> ArchiveDateValidator:
    """Create a pre-configured archive date validator."""
    return ArchiveDateValidator()


def create_pipeline_line_validator() -> PipelineLineValidator:
    """Create a pre-configured pipeline line validator."""
    return PipelineLineValidator()


def create_pipeline_lines_validator() -> PipelineLinesListValidator:
    """Create a pre-configured pipeline lines list validator."""
    return PipelineLinesListValidator()


def create_output_directory_validator() -> OutputDirectoryValidator:
    """Create a pre-configured output directory validator."""
    return OutputDirectoryValidator()


def create_archive_path_validator() -> ArchivePathValidator:
    """Create a pre-configured archive path validator."""
    return ArchivePathValidator()


def create_fetch_archive_request_validator() -> FetchArchiveRequestValidator:
    """Create a pre-configured fetch archive request validator."""
    return FetchArchiveRequestValidator()


def create_complete_archive_validator() -> CompositeArchiveValidator:
    """Create a validator that validates all archive components."""
    return CompositeArchiveValidator(
        create_archive_date_validator(),
        create_pipeline_lines_validator(),
        create_output_directory_validator()
    )