"""
Input validation for text replacement functionality.
Contains validators following Single Responsibility Principle.
"""

import os
import base64
import io
import pandas as pd
from typing import List, Dict, Any
from core.interfaces import IValidator, Result


class CsvContentValidator(IValidator):
    """Validates CSV content for text replacement."""

    def validate(self, value: Dict[str, Any]) -> Result[bool]:
        """Validate CSV upload content."""
        if not value:
            return Result.fail("No CSV data provided")

        contents = value.get('contents')
        filename = value.get('filename')

        if not contents:
            return Result.fail("No file contents provided")

        if not filename:
            return Result.fail("No filename provided")

        # Validate file extension
        if not filename.lower().endswith('.csv'):
            return Result.fail("File must be a CSV file (.csv extension)")

        try:
            # Parse the file content
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)

            # Try to read as CSV to validate format
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), header=None)

            if df.shape[1] < 2:
                return Result.fail("CSV file must have at least 2 columns (old text, new text)")

            if len(df) == 0:
                return Result.fail("CSV file cannot be empty")

            # Check for valid substitution pairs
            valid_pairs = 0
            for _, row in df.iterrows():
                if len(row) >= 2 and pd.notna(row[0]) and str(row[0]).strip():
                    valid_pairs += 1

            if valid_pairs == 0:
                return Result.fail("CSV file must contain at least one valid substitution pair")

            return Result.ok(True, f"CSV file contains {valid_pairs} valid substitution pairs")

        except Exception as e:
            return Result.fail(f"Error reading CSV file: {str(e)}")


class DirectoryPathValidator(IValidator):
    """Validates directory paths for text replacement."""

    def validate(self, value: str) -> Result[bool]:
        """Validate directory path."""
        if not value:
            return Result.fail("Directory path is required")

        if not isinstance(value, str):
            return Result.fail("Directory path must be a string")

        normalized_path = os.path.normpath(value.strip())

        if not os.path.exists(normalized_path):
            return Result.fail(f"Directory does not exist: {normalized_path}")

        if not os.path.isdir(normalized_path):
            return Result.fail(f"Path is not a directory: {normalized_path}")

        # Check if directory is readable
        if not os.access(normalized_path, os.R_OK):
            return Result.fail(f"Directory is not readable: {normalized_path}")

        return Result.ok(True, f"Valid directory: {normalized_path}")


class FileExtensionsValidator(IValidator):
    """Validates file extension inputs."""

    def validate(self, value: str) -> Result[bool]:
        """Validate file extensions string."""
        if not value:
            return Result.fail("File extensions are required")

        if not isinstance(value, str):
            return Result.fail("File extensions must be a string")

        # Parse extensions
        extensions = []
        for ext in value.split(','):
            ext = ext.strip()
            if ext:
                # Remove any dots or asterisks users might add
                clean_ext = ext.lstrip('*').lstrip('.')
                if clean_ext:
                    extensions.append(clean_ext)

        if not extensions:
            return Result.fail("At least one valid file extension is required")

        # Validate extension format (basic alphanumeric check)
        invalid_extensions = []
        for ext in extensions:
            if not ext.replace('_', '').replace('-', '').isalnum():
                invalid_extensions.append(ext)

        if invalid_extensions:
            return Result.fail(f"Invalid file extensions: {', '.join(invalid_extensions)}")

        return Result.ok(True, f"Valid extensions: {', '.join(extensions)}")


class TextReplacementInputValidator(IValidator):
    """Composite validator for all text replacement inputs."""

    def __init__(self):
        self._csv_validator = CsvContentValidator()
        self._directory_validator = DirectoryPathValidator()
        self._extensions_validator = FileExtensionsValidator()

    def validate(self, value: Dict[str, Any]) -> Result[bool]:
        """Validate all text replacement inputs."""
        if not value:
            return Result.fail("No input data provided")

        errors = []

        # Validate CSV data
        csv_data = value.get('csv_data')
        if csv_data:
            csv_result = self._csv_validator.validate(csv_data)
            if not csv_result.success:
                errors.append(f"CSV validation failed: {csv_result.error}")
        else:
            errors.append("CSV file is required")

        # Validate directory
        directory = value.get('directory')
        if directory:
            dir_result = self._directory_validator.validate(directory)
            if not dir_result.success:
                errors.append(
                    f"Directory validation failed: {dir_result.error}")
        else:
            errors.append("Target directory is required")

        # Validate extensions
        extensions = value.get('extensions')
        if extensions:
            ext_result = self._extensions_validator.validate(extensions)
            if not ext_result.success:
                errors.append(
                    f"Extensions validation failed: {ext_result.error}")
        else:
            errors.append("File extensions are required")

        if errors:
            return Result.fail("; ".join(errors))

        return Result.ok(True, "All inputs are valid")


class SubstitutionDataValidator(IValidator):
    """Validates substitution data from CSV content."""

    def validate(self, value: str) -> Result[List[tuple[str, str]]]:
        """Validate and parse substitution data from base64 CSV content."""
        if not value:
            return Result.fail("No CSV content provided")

        try:
            # Decode base64 content
            decoded = base64.b64decode(value)
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), header=None)

            substitutions = []
            invalid_rows = 0

            for index, row in df.iterrows():
                if len(row) >= 2 and pd.notna(row[0]) and pd.notna(row[1]):
                    old_text = str(row[0]).strip()
                    new_text = str(row[1]).strip()

                    if old_text:  # Old text cannot be empty
                        substitutions.append((old_text, new_text))
                    else:
                        invalid_rows += 1
                else:
                    invalid_rows += 1

            if not substitutions:
                return Result.fail("No valid substitution pairs found in CSV file")

            message = f"Found {len(substitutions)} valid substitution pairs"
            if invalid_rows > 0:
                message += f" ({invalid_rows} invalid rows skipped)"

            return Result.ok(substitutions, message)

        except Exception as e:
            return Result.fail(f"Error parsing CSV content: {str(e)}")


# Factory functions for creating validators
def create_csv_validator() -> CsvContentValidator:
    """Create a CSV content validator."""
    return CsvContentValidator()


def create_directory_validator() -> DirectoryPathValidator:
    """Create a directory path validator."""
    return DirectoryPathValidator()


def create_extensions_validator() -> FileExtensionsValidator:
    """Create a file extensions validator."""
    return FileExtensionsValidator()


def create_input_validator() -> TextReplacementInputValidator:
    """Create a composite input validator for text replacement."""
    return TextReplacementInputValidator()


def create_substitution_validator() -> SubstitutionDataValidator:
    """Create a substitution data validator."""
    return SubstitutionDataValidator()
