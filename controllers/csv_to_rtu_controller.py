"""
CSV to RTU page controller following MVC pattern.
Handles UI logic and coordinates between UI components and business services.
"""

from typing import Dict, Any, List, Tuple, Optional
import dash_mantine_components as dmc
import tempfile
import shutil
import os
import base64
import io
import pandas as pd

from core.interfaces import IPageController, ICsvToRtuConverter, ICsvValidator, Result
from components.bootstrap_icon import BootstrapIcon
from domain.csv_rtu_models import CsvFileMetadata, ConversionConstants


class CsvToRtuPageController(IPageController):
    """Controller for CSV to RTU converter page."""

    def __init__(self, converter_service: ICsvToRtuConverter, csv_validator: ICsvValidator):
        """Initialize controller with converter service and validator."""
        self._converter_service = converter_service
        self._csv_validator = csv_validator

    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle input changes and return UI updates."""
        # This method is required by IPageController but not used in CSV to RTU page
        return Result.ok({}, "Input change handled")

    def handle_csv_upload(self, contents: List[str], filenames: List[str],
                          stored_files: List[Dict[str, Any]]) -> Result[Dict[str, Any]]:
        """Handle CSV file upload and validation."""
        try:
            if not contents:
                # No new upload, return existing files
                existing_files = stored_files or []
                file_components = self._create_file_components(existing_files)
                return Result.ok({
                    'files': existing_files,
                    'file_components': file_components,
                    'status_message': "",
                    'upload_disabled': len(existing_files) == 0
                }, "No new files uploaded")

            # Ensure contents and filenames are lists
            if not isinstance(contents, list):
                contents = [contents]
                filenames = [filenames] if filenames else []

            new_files = stored_files or []

            # Process each uploaded file
            for content, filename in zip(contents, filenames or []):
                if filename and filename.lower().endswith('.csv'):
                    validation_result = self._validate_uploaded_file(
                        content, filename)
                    if validation_result.success:
                        file_info = validation_result.data
                        # Store the content for processing
                        file_info['content'] = content

                        # Add file if not already present
                        if not any(f['name'] == filename for f in new_files):
                            new_files.append(file_info)

            # Create UI components
            file_components = self._create_file_components(new_files)
            status_message = ""

            return Result.ok({
                'files': new_files,
                'file_components': file_components,
                'status_message': status_message,
                'upload_disabled': len(new_files) == 0
            }, f"Processed {len(new_files)} files")

        except Exception as e:
            return Result.fail(f"Upload error: {str(e)}", "Error processing uploaded files")

    def handle_file_removal(self, filename_to_remove: str,
                            stored_files: List[Dict[str, Any]]) -> Result[Dict[str, Any]]:
        """Handle removal of a specific CSV file."""
        try:
            if not stored_files:
                return Result.ok({
                    'files': [],
                    'file_components': self._create_file_components([]),
                    'status_message': "",
                    'upload_disabled': True
                }, "No files to remove")

            # Filter out the file to remove
            updated_files = [f for f in stored_files if f.get(
                'name') != filename_to_remove]

            # Create new file components
            file_components = self._create_file_components(updated_files)

            return Result.ok({
                'files': updated_files,
                'file_components': file_components,
                'status_message': "",
                'upload_disabled': len(updated_files) == 0
            }, f"Removed file: {filename_to_remove}")

        except Exception as e:
            return Result.fail(f"File removal error: {str(e)}", "Error removing file")

    def handle_directory_selection(self) -> Result[Dict[str, Any]]:
        """Handle output directory selection."""
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()  # Hide the main window
            root.lift()      # Bring to front
            root.attributes("-topmost", True)

            directory = filedialog.askdirectory(
                title="Select Output Directory for RTU Files")
            root.destroy()

            if directory:
                return Result.ok({
                    'directory': directory,
                    'status': "",
                    'store_data': {'path': directory}
                }, f"Selected directory: {directory}")
            else:
                return Result.ok({
                    'directory': "",
                    'status': "",
                    'store_data': {'path': ''}
                }, "Directory selection cancelled")

        except Exception as e:
            status = dmc.Alert(
                title="Error",
                children=f"Error selecting directory: {str(e)}",
                icon=BootstrapIcon(icon="exclamation-circle"),
                color="red",
                withCloseButton=False
            )

            return Result.ok({
                'directory': "",
                'status': status,
                'store_data': {'path': ''}
            }, f"Directory selection error: {str(e)}")

    def handle_rtu_conversion(self, csv_files: List[Dict[str, Any]],
                              output_dir_data: Dict[str, str]) -> Result[Dict[str, Any]]:
        """Handle RTU conversion process."""
        try:
            if not csv_files:
                return Result.fail("No files to convert", "Please upload CSV files first")

            # Get output directory with fallback
            output_dir = output_dir_data.get(
                'path', '') if output_dir_data else ''
            if not output_dir or output_dir.strip() == '':
                output_dir = os.path.join(
                    os.getcwd(), ConversionConstants.DEFAULT_OUTPUT_DIR)

            # Ensure output directory exists
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                return Result.fail(
                    f"Could not create output directory '{output_dir}': {str(e)}",
                    "Please check the directory path and permissions."
                )

            # Create temporary files from uploaded content
            temp_dir = tempfile.mkdtemp(prefix="csv_upload_")
            csv_file_paths = []

            try:
                # Save uploaded files to temporary location
                for file_info in csv_files:
                    try:
                        # Decode file content
                        content_type, content_string = file_info['content'].split(
                            ',')
                        decoded = base64.b64decode(content_string)
                        csv_content = decoded.decode('utf-8')

                        # Save to temp file
                        temp_file_path = os.path.join(
                            temp_dir, file_info['name'])
                        with open(temp_file_path, 'w', encoding='utf-8') as f:
                            f.write(csv_content)

                        csv_file_paths.append(temp_file_path)
                    except Exception:
                        continue  # Skip problematic files

                if not csv_file_paths:
                    return Result.fail(
                        "No valid CSV files found to convert",
                        "Please check your uploaded files"
                    )

                # Convert files using the service
                conversion_result = self._converter_service.convert_multiple_files(
                    csv_file_paths, output_dir)

                if conversion_result.success:
                    result_data = conversion_result.data
                    return Result.ok({
                        'success': True,
                        'result': result_data,
                        'notification': {
                            "title": "Conversion Complete",
                            "message": f"Successfully converted {result_data['successful_conversions']} of {result_data['total_files']} files. Output directory: {output_dir}",
                            "color": "green",
                            "autoClose": 7000,
                            "action": "show"
                        }
                    }, "Conversion completed successfully")
                else:
                    return Result.fail(
                        conversion_result.error,
                        "Conversion failed"
                    )

            finally:
                # Cleanup temp directory
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            return Result.fail(f"Conversion error: {str(e)}", "An unexpected error occurred during conversion")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for the help modal."""
        return self._converter_service.get_system_info()

    def _validate_uploaded_file(self, content: str, filename: str) -> Result[Dict[str, Any]]:
        """Validate uploaded file content and return file info."""
        try:
            # Use validator to validate content
            validation_result = self._csv_validator.validate_file_content(
                content, filename)
            if not validation_result.success:
                return validation_result

            # Extract metadata and create file info
            metadata = validation_result.data['metadata']

            file_info = {
                'name': filename,
                'rows': metadata.rows,
                'columns': metadata.columns,
                'size': metadata.size
            }

            return Result.ok(file_info, "File validation successful")

        except Exception as e:
            return Result.fail(f"File validation error: {str(e)}", "Error validating uploaded file")

    def _create_file_components(self, file_list: List[Dict[str, Any]]):
        """Create file display components with pattern-matching IDs for removal."""
        if not file_list:
            return [
                dmc.Alert([
                    dmc.Group([
                        BootstrapIcon(icon="info-circle", width=20),
                        dmc.Text(
                            "No files selected. Upload CSV files to get started.", size="sm")
                    ], gap="xs")
                ], color="blue", variant="light", radius="md")
            ]

        components = []
        for file_info in file_list:
            component = dmc.Paper([
                dmc.Group([
                    BootstrapIcon(icon="file-earmark-spreadsheet",
                                  width=24, color="green"),
                    dmc.Stack([
                        dmc.Text(file_info['name'], fw=500, size="sm"),
                        dmc.Group([
                            dmc.Badge(
                                f"{file_info['rows']} rows", color="blue", variant="light", size="xs"),
                            dmc.Badge(
                                f"{file_info['columns']} cols", color="cyan", variant="light", size="xs"),
                            dmc.Badge(
                                f"{file_info['size']/1024:.1f} KB", color="gray", variant="light", size="xs"),
                        ], gap="xs")
                    ], gap="xs", flex=1),
                    dmc.ActionIcon(
                        BootstrapIcon(icon="x", width=16),
                        id={'type': 'remove-file-btn',
                            'index': file_info['name']},
                        color='red', variant="light", size="sm"
                    )
                ], justify="space-between", align="center")
            ], p="md", radius="md", withBorder=True, className="mb-2")

            components.append(component)

        return components


class CsvToRtuUIResponseFormatter:
    """Formatter for UI responses from the controller."""

    @staticmethod
    def format_upload_response(result: Result[Dict[str, Any]]) -> Tuple:
        """Format upload response for Dash callback."""
        if result.success:
            data = result.data
            return (
                data['files'],
                data['file_components'],
                data['status_message'],
                data['upload_disabled']
            )
        else:
            # Error case
            error_alert = dmc.Alert(
                title="Upload Error",
                children=result.message,
                color="red",
                icon=BootstrapIcon(icon="exclamation-circle")
            )
            return [], [error_alert], "", True

    @staticmethod
    def format_file_removal_response(result: Result[Dict[str, Any]]) -> Tuple:
        """Format file removal response for Dash callback."""
        if result.success:
            data = result.data
            return (
                data['files'],
                data['file_components'],
                data['status_message'],
                data['upload_disabled']
            )
        else:
            # Error case - keep existing state but show error
            error_alert = dmc.Alert(
                title="Removal Error",
                children=result.message,
                color="red",
                icon=BootstrapIcon(icon="exclamation-circle")
            )
            return [], [error_alert], "", True

    @staticmethod
    def format_directory_selection_response(result: Result[Dict[str, Any]]) -> Tuple:
        """Format directory selection response for Dash callback."""
        if result.success:
            data = result.data
            return (
                data['directory'],
                data['status'],
                data['store_data']
            )
        else:
            return "", "", {'path': ''}

    @staticmethod
    def format_conversion_response(result: Result[Dict[str, Any]]) -> Tuple:
        """Format conversion response for Dash callback."""
        if result.success:
            data = result.data

            # Success button state
            success_button = dmc.Button([
                BootstrapIcon(icon="download", width=20),
                "Write RTU Data"
            ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")

            return (
                {'status': 'completed', 'result': data['result']},
                "",
                success_button,
                [data['notification']]
            )
        else:
            # Error notification
            error_notification = [{
                "title": "Conversion Failed",
                "message": result.message,
                "color": "red",
                "autoClose": 5000,
                "action": "show"
            }]

            # Error button state
            error_button = dmc.Button([
                BootstrapIcon(icon="download", width=20),
                "Write RTU Data"
            ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")

            return (
                {'status': 'error', 'error': result.error},
                "",
                error_button,
                error_notification
            )
