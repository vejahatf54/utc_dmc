"""
Input validators for CSV to RTU conversion.
Each validator follows Single Responsibility Principle.
"""

import os
import pandas as pd
import base64
import io
from typing import Any, Dict, List, Optional
from core.interfaces import IValidator, ICsvValidator, Result
from domain.csv_rtu_models import CsvFileMetadata, ConversionConstants


class CsvFilePathValidator(IValidator):
    """Validates CSV file path and existence."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate CSV file path."""
        if value is None:
            return Result.fail("File path cannot be None", "Please provide a valid file path")

        if not isinstance(value, str):
            return Result.fail("File path must be a string", "File path must be text")

        value = value.strip()
        if not value:
            return Result.fail("File path cannot be empty", "Please provide a file path")

        # Check if file exists
        if not os.path.exists(value):
            return Result.fail("File does not exist", f"The file '{value}' does not exist")

        # Check file extension
        _, ext = os.path.splitext(value)
        if ext.lower() not in ConversionConstants.SUPPORTED_CSV_EXTENSIONS:
            return Result.fail(
                f"Unsupported file extension: {ext}",
                f"Only CSV files ({', '.join(ConversionConstants.SUPPORTED_CSV_EXTENSIONS)}) are supported"
            )

        return Result.ok(True, "File path is valid")


class CsvFileSizeValidator(IValidator):
    """Validates CSV file size constraints."""

    def __init__(self, max_size_bytes: Optional[int] = None):
        self._max_size_bytes = max_size_bytes or ConversionConstants.MAX_FILE_SIZE_BYTES

    def validate(self, value: Any) -> Result[bool]:
        """Validate file size from file path or size value."""
        if isinstance(value, str):
            # File path provided
            if not os.path.exists(value):
                return Result.fail("File does not exist", "Cannot validate size of non-existent file")
            size = os.path.getsize(value)
        elif isinstance(value, int):
            # Size value provided directly
            size = value
        else:
            return Result.fail("Invalid input type", "Expected file path or size value")

        if size < 0:
            return Result.fail("Invalid file size", "File size cannot be negative")

        if size == 0:
            return Result.fail("Empty file", "CSV file cannot be empty")

        if size > self._max_size_bytes:
            max_mb = self._max_size_bytes / (1024 * 1024)
            actual_mb = size / (1024 * 1024)
            return Result.fail(
                f"File too large: {actual_mb:.1f}MB",
                f"File size exceeds maximum limit of {max_mb:.1f}MB"
            )

        return Result.ok(True, f"File size is valid ({size / 1024:.1f} KB)")


class CsvStructureValidator(IValidator):
    """Validates CSV file structure and format."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate CSV structure from DataFrame or file path."""
        df = None

        if isinstance(value, str):
            # File path provided
            try:
                df = pd.read_csv(value)
            except Exception as e:
                return Result.fail(f"Cannot read CSV file: {str(e)}", "Invalid CSV format")
        elif isinstance(value, pd.DataFrame):
            # DataFrame provided directly
            df = value
        else:
            return Result.fail("Invalid input type", "Expected file path or DataFrame")

        # Check if DataFrame is empty
        if df.empty:
            return Result.fail("Empty CSV file", "CSV file contains no data")

        # Check minimum columns (timestamp + at least one tag)
        if len(df.columns) < ConversionConstants.MIN_COLUMNS:
            return Result.fail(
                f"Insufficient columns: {len(df.columns)}",
                f"CSV must have at least {ConversionConstants.MIN_COLUMNS} columns (timestamp + tags)"
            )

        # Check maximum columns
        if len(df.columns) > ConversionConstants.MAX_COLUMNS:
            return Result.fail(
                f"Too many columns: {len(df.columns)}",
                f"CSV cannot have more than {ConversionConstants.MAX_COLUMNS} columns"
            )

        # Check for empty column names
        empty_columns = [i for i, col in enumerate(
            df.columns) if not str(col).strip()]
        if empty_columns:
            return Result.fail(
                f"Empty column names at positions: {empty_columns}",
                "All columns must have names"
            )

        return Result.ok(True, f"CSV structure is valid ({len(df)} rows, {len(df.columns)} columns)")


class CsvTimestampValidator(IValidator):
    """Validates the timestamp column in CSV files."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate timestamp column from DataFrame or file path."""
        df = None

        if isinstance(value, str):
            # File path provided
            try:
                df = pd.read_csv(value)
            except Exception as e:
                return Result.fail(f"Cannot read CSV file: {str(e)}", "Invalid CSV format")
        elif isinstance(value, pd.DataFrame):
            # DataFrame provided directly
            df = value
        else:
            return Result.fail("Invalid input type", "Expected file path or DataFrame")

        if df.empty:
            return Result.fail("Empty CSV file", "Cannot validate timestamps in empty file")

        # Check first column (assumed to be timestamp)
        first_column = df.iloc[:, 0]

        # Sample a few rows to validate timestamp format
        sample_size = min(5, len(df))
        sample_rows = df.head(sample_size)

        valid_timestamps = 0
        for idx, value in enumerate(sample_rows.iloc[:, 0]):
            try:
                if pd.isna(value):
                    continue

                value_str = str(value).strip()
                if not value_str:
                    continue

                # Try to parse timestamp
                from domain.csv_rtu_models import RtuTimestamp
                RtuTimestamp.from_string(value_str)
                valid_timestamps += 1

            except Exception:
                continue

        if valid_timestamps == 0:
            return Result.fail(
                "No valid timestamps found",
                "First column should contain valid timestamp data"
            )

        success_rate = valid_timestamps / sample_size
        if success_rate < 0.5:  # At least 50% should be valid
            return Result.fail(
                f"Too many invalid timestamps: {valid_timestamps}/{sample_size}",
                "First column should contain valid timestamp data"
            )

        return Result.ok(True, f"Timestamp validation passed ({valid_timestamps}/{sample_size} valid)")


class OutputDirectoryValidator(IValidator):
    """Validates output directory for RTU files."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate output directory path."""
        if value is None:
            return Result.fail("Output directory cannot be None", "Please provide an output directory")

        if not isinstance(value, str):
            return Result.fail("Output directory must be a string", "Directory path must be text")

        value = value.strip()
        if not value:
            return Result.fail("Output directory cannot be empty", "Please provide an output directory")

        # Try to create directory if it doesn't exist
        try:
            os.makedirs(value, exist_ok=True)
        except Exception as e:
            return Result.fail(
                f"Cannot create directory: {str(e)}",
                "Please check directory path and permissions"
            )

        # Check if directory is writable
        if not os.access(value, os.W_OK):
            return Result.fail(
                "Directory is not writable",
                "Please check directory permissions"
            )

        return Result.ok(True, "Output directory is valid")


class CsvContentValidator(IValidator):
    """Validates CSV content from upload data."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate CSV content from base64 encoded upload data."""
        if not isinstance(value, str):
            return Result.fail("Invalid content type", "Expected string content")

        try:
            # Decode base64 content
            if ',' in value:
                content_type, content_string = value.split(',', 1)
            else:
                content_string = value

            decoded = base64.b64decode(content_string)
            csv_content = decoded.decode('utf-8')

            # Parse CSV content
            df = pd.read_csv(io.StringIO(csv_content))

            # Validate structure using existing validator
            structure_validator = CsvStructureValidator()
            structure_result = structure_validator.validate(df)

            if not structure_result.success:
                return structure_result

            # Validate timestamps using existing validator
            timestamp_validator = CsvTimestampValidator()
            timestamp_result = timestamp_validator.validate(df)

            return timestamp_result

        except Exception as e:
            return Result.fail(f"Error processing CSV content: {str(e)}", "Invalid CSV content")


class CompositeValidator(IValidator):
    """Validator that combines multiple validators using AND logic."""

    def __init__(self, *validators: IValidator):
        self._validators = validators

    def validate(self, value: Any) -> Result[bool]:
        """Validate using all validators. Fails if any validator fails."""
        for validator in self._validators:
            result = validator.validate(value)
            if not result.success:
                return result

        return Result.ok(True, "All validations passed")


class CsvToRtuValidator(ICsvValidator):
    """Main CSV validator that implements ICsvValidator interface."""

    def __init__(self):
        self._file_path_validator = CsvFilePathValidator()
        self._file_size_validator = CsvFileSizeValidator()
        self._structure_validator = CsvStructureValidator()
        self._timestamp_validator = CsvTimestampValidator()
        self._content_validator = CsvContentValidator()

    def validate(self, value: Any) -> Result[bool]:
        """General validation method."""
        if isinstance(value, str) and os.path.exists(value):
            return self.validate_file_structure(value).success
        else:
            return Result.fail("Invalid input", "Expected file path or content")

    def validate_file_structure(self, file_path: str) -> Result[Dict[str, Any]]:
        """Validate CSV file structure and return metadata."""
        try:
            # Validate file path
            path_result = self._file_path_validator.validate(file_path)
            if not path_result.success:
                return Result.fail(path_result.error, path_result.message)

            # Validate file size
            size_result = self._file_size_validator.validate(file_path)
            if not size_result.success:
                return Result.fail(size_result.error, size_result.message)

            # Validate structure
            structure_result = self._structure_validator.validate(file_path)
            if not structure_result.success:
                return Result.fail(structure_result.error, structure_result.message)

            # Validate timestamps
            timestamp_result = self._timestamp_validator.validate(file_path)
            if not timestamp_result.success:
                return Result.fail(timestamp_result.error, timestamp_result.message)

            # Create metadata if all validations pass
            df = pd.read_csv(file_path)
            metadata = CsvFileMetadata(
                filename=os.path.basename(file_path),
                size=os.path.getsize(file_path),
                rows=len(df),
                columns=len(df.columns),
                first_column=df.columns[0]
            )

            return Result.ok({
                'metadata': metadata,
                'valid': True,
                'columns': len(df.columns),
                'rows': len(df),
                'tags': metadata.tag_count,
                'total_points': metadata.total_points,
                'first_column': metadata.first_column,
                'size': metadata.size
            }, "File validation successful")

        except Exception as e:
            return Result.fail(f"Validation error: {str(e)}", "Error validating CSV file")

    def validate_file_content(self, content: str, filename: str) -> Result[Dict[str, Any]]:
        """Validate CSV content from upload and return metadata."""
        try:
            # Validate content
            content_result = self._content_validator.validate(content)
            if not content_result.success:
                return Result.fail(content_result.error, content_result.message)

            # Decode and parse content to create metadata
            if ',' in content:
                content_type, content_string = content.split(',', 1)
            else:
                content_string = content

            decoded = base64.b64decode(content_string)
            csv_content = decoded.decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))

            metadata = CsvFileMetadata(
                filename=filename,
                size=len(decoded),
                rows=len(df),
                columns=len(df.columns),
                first_column=df.columns[0]
            )

            return Result.ok({
                'metadata': metadata,
                'valid': True,
                'columns': len(df.columns),
                'rows': len(df),
                'tags': metadata.tag_count,
                'total_points': metadata.total_points,
                'first_column': metadata.first_column,
                'size': metadata.size
            }, "Content validation successful")

        except Exception as e:
            return Result.fail(f"Content validation error: {str(e)}", "Error validating CSV content")


# Factory functions for creating pre-configured validators
def create_csv_file_validator() -> CsvToRtuValidator:
    """Create a pre-configured CSV file validator."""
    return CsvToRtuValidator()


def create_output_directory_validator() -> OutputDirectoryValidator:
    """Create a pre-configured output directory validator."""
    return OutputDirectoryValidator()


def create_file_upload_validator() -> CompositeValidator:
    """Create a validator for file uploads."""
    return CompositeValidator(
        CsvFileSizeValidator(),
        CsvContentValidator()
    )
