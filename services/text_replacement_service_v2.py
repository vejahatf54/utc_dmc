"""
Text replacement services implementing SOLID principles.
Contains business logic with proper separation of concerns.
"""

import re
import csv
import base64
import io
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Any
from core.interfaces import (
    ITextReplacer, ISubstitutionLoader, IFileProcessor,
    ITextReplacementService, Result
)
from domain.text_replacement_models import (
    SubstitutionPair, FileExtensionFilter, DirectoryPath,
    TextReplacementConfig, TextReplacementResult
)
from validation.text_replacement_validators import SubstitutionDataValidator
from logging_config import get_logger

logger = get_logger(__name__)


class RegexTextReplacer(ITextReplacer):
    """Text replacer using regex for case-insensitive operations."""

    def replace_text(self, content: str, old_text: str, new_text: str, match_case: bool = True) -> str:
        """Replace text in content with specified case sensitivity."""
        if not content or not old_text:
            return content

        if match_case:
            return content.replace(old_text, new_text)
        else:
            # Use regex for case-insensitive replacement
            pattern = re.compile(re.escape(old_text), re.IGNORECASE)
            return pattern.sub(new_text, content)


class CsvSubstitutionLoader(ISubstitutionLoader):
    """Loads substitution pairs from CSV sources."""

    def __init__(self, validator: SubstitutionDataValidator = None):
        self._validator = validator or SubstitutionDataValidator()

    def load_substitutions(self, source: str) -> Result[List[Tuple[str, str]]]:
        """Load substitution pairs from base64 encoded CSV content."""
        validation_result = self._validator.validate(source)
        if not validation_result.success:
            return Result.fail(validation_result.error)

        return Result.ok(validation_result.data, validation_result.message)


class FileSystemFileProcessor(IFileProcessor):
    """File processor for local file system operations."""

    def find_files(self, directory: str, extensions: List[str]) -> Result[List[str]]:
        """Find files in directory matching the given extensions."""
        try:
            dir_path = DirectoryPath(directory)
            extension_filter = FileExtensionFilter(extensions)

            files = dir_path.find_files(extension_filter)

            if not files:
                return Result.ok([], f"No files found with extensions: {', '.join(extensions)}")

            return Result.ok(files, f"Found {len(files)} files to process")

        except ValueError as e:
            return Result.fail(str(e))
        except Exception as e:
            logger.error(f"Error finding files: {str(e)}")
            return Result.fail(f"Error finding files: {str(e)}")

    def process_file(self, file_path: str, substitutions: List[Tuple[str, str]],
                     replacer: ITextReplacer, match_case: bool = True) -> Result[bool]:
        """Process a single file with given substitutions."""
        try:
            # Read file content
            file_obj = Path(file_path)
            if not file_obj.exists():
                return Result.fail(f"File not found: {file_path}")

            if not file_obj.is_file():
                return Result.fail(f"Path is not a file: {file_path}")

            # Read with UTF-8 encoding
            content = file_obj.read_text(encoding='utf-8')
            original_content = content

            # Apply all substitutions
            for old_text, new_text in substitutions:
                content = replacer.replace_text(
                    content, old_text, new_text, match_case)

            # Write back only if content changed
            if content != original_content:
                file_obj.write_text(content, encoding='utf-8')
                logger.debug(f"Processed file: {file_path}")

            return Result.ok(True, f"Successfully processed: {file_path}")

        except PermissionError:
            error_msg = f"Permission denied accessing file: {file_path}"
            logger.error(error_msg)
            return Result.fail(error_msg)
        except UnicodeDecodeError:
            error_msg = f"Unable to read file as UTF-8: {file_path}"
            logger.error(error_msg)
            return Result.fail(error_msg)
        except Exception as e:
            error_msg = f"Error processing file {file_path}: {str(e)}"
            logger.error(error_msg)
            return Result.fail(error_msg)


class TextReplacementService(ITextReplacementService):
    """Main service orchestrating text replacement operations."""

    def __init__(self, substitution_loader: ISubstitutionLoader = None,
                 file_processor: IFileProcessor = None,
                 text_replacer: ITextReplacer = None):
        self._substitution_loader = substitution_loader or CsvSubstitutionLoader()
        self._file_processor = file_processor or FileSystemFileProcessor()
        self._text_replacer = text_replacer or RegexTextReplacer()

    def replace_text_in_files(self, directory: str, substitution_source: str,
                              extensions: List[str], match_case: bool = True) -> Result[Dict[str, Any]]:
        """Replace text in files based on substitution mappings."""
        try:
            # Load substitutions
            sub_result = self._substitution_loader.load_substitutions(
                substitution_source)
            if not sub_result.success:
                return Result.fail(f"Failed to load substitutions: {sub_result.error}")

            substitutions = sub_result.data
            if not substitutions:
                return Result.fail("No substitutions loaded")

            # Find files to process
            files_result = self._file_processor.find_files(
                directory, extensions)
            if not files_result.success:
                return Result.fail(f"Failed to find files: {files_result.error}")

            files_to_process = files_result.data
            if not files_to_process:
                return Result.ok({
                    'processed_files': 0,
                    'total_files': 0,
                    'errors': [],
                    'message': 'No files found to process'
                })

            # Process files
            processed_count = 0
            errors = []

            for file_path in files_to_process:
                process_result = self._file_processor.process_file(
                    file_path, substitutions, self._text_replacer, match_case
                )

                if process_result.success:
                    processed_count += 1
                else:
                    errors.append(process_result.error)

            # Create result
            result_data = {
                'processed_files': processed_count,
                'total_files': len(files_to_process),
                'errors': errors,
                'substitution_count': len(substitutions)
            }

            if errors:
                result_data['message'] = f"Processed {processed_count} of {len(files_to_process)} files with {len(errors)} errors"
            else:
                result_data['message'] = f"Successfully processed all {processed_count} files"

            return Result.ok(result_data, result_data['message'])

        except Exception as e:
            error_msg = f"Text replacement service error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Result.fail(error_msg)


# Legacy wrapper for backward compatibility
class LegacyTextReplacementService:
    """Legacy wrapper maintaining compatibility with old ReplaceTextService API."""

    def __init__(self):
        self._service = TextReplacementService()
        self.csv_file_path: str = None
        self.folder_path: str = None

    def set_csv_file(self, csv_file_path: str):
        """Set the path to the CSV file containing substitutions."""
        if not Path(csv_file_path).exists():
            raise FileNotFoundError(
                f"CSV file does not exist: {csv_file_path}")
        self.csv_file_path = csv_file_path
        logger.debug("CSV file set to: %s", csv_file_path)

    def set_folder_path(self, folder_path: str):
        """Set the folder containing files to process."""
        if not Path(folder_path).is_dir():
            raise FileNotFoundError(
                f"Folder path does not exist: {folder_path}")
        self.folder_path = folder_path
        logger.debug("Folder path set to: %s", folder_path)

    def replace_in_files(self, extensions: List[str], match_case: bool = False):
        """Replace text in all files with the given extensions."""
        if not self.csv_file_path or not self.folder_path:
            raise ValueError(
                "CSV file and folder path must be set before replacing text.")

        # Read CSV file and encode to base64 for the new service
        with open(self.csv_file_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()

        encoded_content = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')

        # Use the new service
        result = self._service.replace_text_in_files(
            self.folder_path, encoded_content, extensions, match_case
        )

        if not result.success:
            raise Exception(result.error)

        logger.debug("Legacy wrapper completed successfully")


# Factory functions
def create_text_replacer() -> ITextReplacer:
    """Create a text replacer instance."""
    return RegexTextReplacer()


def create_substitution_loader() -> ISubstitutionLoader:
    """Create a substitution loader instance."""
    return CsvSubstitutionLoader()


def create_file_processor() -> IFileProcessor:
    """Create a file processor instance."""
    return FileSystemFileProcessor()


def create_text_replacement_service() -> ITextReplacementService:
    """Create a text replacement service with all dependencies."""
    return TextReplacementService(
        substitution_loader=create_substitution_loader(),
        file_processor=create_file_processor(),
        text_replacer=create_text_replacer()
    )
