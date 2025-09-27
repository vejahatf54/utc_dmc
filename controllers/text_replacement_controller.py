"""
Text replacement controller handling UI interactions.
Separates UI logic from business logic following SOLID principles.
"""

import tempfile
import os
from typing import Dict, Any
from core.interfaces import ITextReplacementController, Result
from services.text_replacement_service_v2 import ITextReplacementService
from validation.text_replacement_validators import (
    CsvContentValidator, DirectoryPathValidator, FileExtensionsValidator,
    SubstitutionDataValidator
)
from logging_config import get_logger

logger = get_logger(__name__)


class TextReplacementPageController(ITextReplacementController):
    """Controller for text replacement page handling UI interactions."""

    def __init__(self, text_replacement_service: ITextReplacementService,
                 csv_validator: CsvContentValidator = None,
                 directory_validator: DirectoryPathValidator = None,
                 extensions_validator: FileExtensionsValidator = None):
        self._service = text_replacement_service
        self._csv_validator = csv_validator or CsvContentValidator()
        self._directory_validator = directory_validator or DirectoryPathValidator()
        self._extensions_validator = extensions_validator or FileExtensionsValidator()

    def handle_csv_upload(self, contents: str, filename: str) -> Result[Dict[str, Any]]:
        """Handle CSV file upload and validation."""
        try:
            # Validate CSV upload
            csv_data = {'contents': contents, 'filename': filename}
            validation_result = self._csv_validator.validate(csv_data)

            if not validation_result.success:
                return Result.fail(validation_result.error)

            # Parse substitution count
            substitution_validator = SubstitutionDataValidator()
            content_type, content_string = contents.split(',')
            sub_result = substitution_validator.validate(content_string)

            if not sub_result.success:
                return Result.fail(sub_result.error)

            substitution_count = len(sub_result.data)

            return Result.ok({
                'filename': filename,
                'content': content_string,
                'substitution_count': substitution_count,
                'status': 'valid',
                'message': f"CSV file loaded successfully with {substitution_count} substitutions"
            })

        except Exception as e:
            logger.error(f"Error handling CSV upload: {str(e)}")
            return Result.fail(f"Error processing CSV file: {str(e)}")

    def handle_text_replacement(self, directory: str, csv_data: Dict[str, Any],
                                extensions: str, match_case: bool) -> Result[Dict[str, Any]]:
        """Handle text replacement request."""
        try:
            # Validate inputs
            validation_errors = []

            # Validate directory
            if directory:
                dir_result = self._directory_validator.validate(directory)
                if not dir_result.success:
                    validation_errors.append(f"Directory: {dir_result.error}")
            else:
                validation_errors.append("Target directory is required")

            # Validate CSV data
            if not csv_data or not csv_data.get('content'):
                validation_errors.append("CSV file is required")

            # Validate extensions
            if extensions:
                ext_result = self._extensions_validator.validate(extensions)
                if not ext_result.success:
                    validation_errors.append(f"Extensions: {ext_result.error}")
            else:
                validation_errors.append("File extensions are required")

            if validation_errors:
                return Result.fail("; ".join(validation_errors))

            # Parse extensions
            extension_list = []
            for ext in extensions.split(','):
                ext = ext.strip().lstrip('*').lstrip('.')
                if ext:
                    extension_list.append(ext)

            if not extension_list:
                return Result.fail("No valid extensions specified")

            # Execute text replacement
            result = self._service.replace_text_in_files(
                directory=directory,
                substitution_source=csv_data['content'],
                extensions=extension_list,
                match_case=match_case
            )

            if not result.success:
                return Result.fail(result.error)

            return Result.ok(result.data, result.message)

        except Exception as e:
            logger.error(
                f"Error handling text replacement: {str(e)}", exc_info=True)
            return Result.fail(f"Processing error: {str(e)}")


class TextReplacementUIResponseFormatter:
    """Formats controller responses for Dash UI components."""

    @staticmethod
    def format_csv_upload_response(result: Result[Dict[str, Any]]) -> tuple:
        """Format CSV upload response for UI callback."""
        if result.success:
            csv_data = result.data

            # Create success status component
            status_component = {
                'type': 'success',
                'title': 'CSV File Loaded Successfully',
                'message': result.message,
                'filename': csv_data['filename'],
                'substitution_count': csv_data['substitution_count']
            }

            return csv_data, status_component
        else:
            # Create error status component
            status_component = {
                'type': 'error',
                'title': 'File Processing Error',
                'message': result.error
            }

            return {}, status_component

    @staticmethod
    def format_replacement_response(result: Result[Dict[str, Any]]) -> dict:
        """Format text replacement response for UI notification."""
        if result.success:
            data = result.data

            if data.get('errors'):
                # Partial success with errors
                return {
                    'type': 'warning',
                    'title': 'Partially Completed',
                    'message': result.message,
                    'details': {
                        'processed_files': data['processed_files'],
                        'total_files': data['total_files'],
                        'error_count': len(data['errors'])
                    }
                }
            else:
                # Complete success
                return {
                    'type': 'success',
                    'title': 'Completed Successfully',
                    'message': result.message,
                    'details': {
                        'processed_files': data['processed_files'],
                        'total_files': data['total_files']
                    }
                }
        else:
            # Error
            return {
                'type': 'error',
                'title': 'Processing Error',
                'message': result.error
            }


# Factory function
def create_text_replacement_controller(service: ITextReplacementService) -> ITextReplacementController:
    """Create a text replacement controller with dependencies."""
    return TextReplacementPageController(
        text_replacement_service=service,
        csv_validator=CsvContentValidator(),
        directory_validator=DirectoryPathValidator(),
        extensions_validator=FileExtensionsValidator()
    )
