"""
RTU to CSV page controller following MVC pattern.
Handles UI logic and coordinates between UI components and business services.
"""

from typing import Dict, Any, List, Tuple, Optional
import dash_mantine_components as dmc
import tempfile
import shutil
import os
import threading
import time
from datetime import datetime, timedelta

from core.interfaces import IPageController, IRtuToCSVConverter, IRtuFileReader, Result
from components.bootstrap_icon import BootstrapIcon
from domain.rtu_models import RtuFilePath, RtuTimeRange, RtuFileInfo, RtuProcessingOptions, RtuConversionConstants
from logging_config import get_logger

logger = get_logger(__name__)


class RtuToCsvPageController(IPageController):
    """Controller for RTU to CSV converter page."""

    def __init__(self, converter_service: IRtuToCSVConverter, file_reader: IRtuFileReader):
        """Initialize controller with converter service and file reader."""
        self._converter_service = converter_service
        self._file_reader = file_reader
        self._background_thread = None
        self._cancel_requested = False

    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle input changes and return UI updates."""
        # This method is required by IPageController but not heavily used in RTU to CSV page
        return Result.ok({}, "Input change handled")

    def handle_file_selection(self, selected_files: List[str]) -> Result[Dict[str, Any]]:
        """Handle RTU file selection and validation."""
        try:
            if not selected_files:
                return Result.ok({
                    'files': [],
                    'file_components': [],
                    'status_message': "No files selected",
                    'process_disabled': True
                }, "No files selected")

            validated_files = []
            invalid_files = []

            # Validate each selected file
            for file_path in selected_files:
                try:
                    rtu_path = RtuFilePath(file_path)
                    if rtu_path.exists():
                        # Get file info
                        info_result = self._file_reader.get_file_info(
                            file_path)
                        if info_result.success:
                            file_info = info_result.data
                            file_info['path'] = file_path
                            file_info['name'] = rtu_path.filename
                            validated_files.append(file_info)
                        else:
                            invalid_files.append(
                                f"{rtu_path.filename}: {info_result.error}")
                    else:
                        invalid_files.append(
                            f"{rtu_path.filename}: File not found")
                except ValueError as e:
                    invalid_files.append(
                        f"{os.path.basename(file_path)}: {str(e)}")

            # Create UI components
            file_components = self._create_file_components(validated_files)

            # Create status message
            status_message = ""
            if invalid_files:
                status_message = f"Warning: {len(invalid_files)} invalid files: {', '.join(invalid_files)}"

            return Result.ok({
                'files': validated_files,
                'file_components': file_components,
                'status_message': status_message,
                'process_disabled': len(validated_files) == 0
            }, f"Validated {len(validated_files)} RTU files")

        except Exception as e:
            logger.error(f"Error in file selection: {str(e)}")
            return Result.fail(f"File selection error: {str(e)}", "Error processing file selection")

    def handle_conversion_start(self, files: List[Dict[str, Any]], output_directory: str,
                                processing_options: Dict[str, Any]) -> Result[Dict[str, Any]]:
        """Handle RTU to CSV conversion process."""
        try:
            if not files:
                return Result.fail("No files to process", "No RTU files selected")

            if not output_directory or not os.path.exists(output_directory):
                return Result.fail("Invalid output directory", "Please select a valid output directory")

            # Create processing options object
            options = self._create_processing_options(processing_options)

            # Extract file paths
            file_paths = [file['path'] for file in files]

            # Start conversion
            if len(file_paths) == 1:
                result = self._converter_service.convert_file(
                    file_paths[0], output_directory, options.__dict__)
            else:
                result = self._converter_service.convert_multiple_files(
                    file_paths, output_directory, options.__dict__)

            if result.success:
                return Result.ok({
                    'status': 'completed',
                    'message': f"Successfully converted {len(file_paths)} files",
                    'output_directory': output_directory,
                    'files_processed': len(file_paths)
                }, "Conversion completed successfully")
            else:
                return Result.fail(result.error, "Conversion failed")

        except Exception as e:
            logger.error(f"Error in conversion: {str(e)}")
            return Result.fail(f"Conversion error: {str(e)}", "Error during RTU to CSV conversion")

    def handle_background_conversion(self, files: List[Dict[str, Any]], output_directory: str,
                                     processing_options: Dict[str, Any], task_manager=None) -> str:
        """Start RTU to CSV conversion in background thread."""
        task_id = f"rtu_csv_task_{int(datetime.now().timestamp())}"

        self._cancel_requested = False
        self._background_thread = threading.Thread(
            target=self._background_conversion_worker,
            args=(task_id, files, output_directory,
                  processing_options, task_manager)
        )
        self._background_thread.daemon = True
        self._background_thread.start()

        return task_id

    def cancel_background_conversion(self) -> None:
        """Cancel the background conversion process."""
        self._cancel_requested = True
        if self._background_thread and self._background_thread.is_alive():
            # The actual cancellation needs to be handled by the service
            logger.info("Background conversion cancellation requested")

    def get_file_info(self, file_path: str) -> Result[Dict[str, Any]]:
        """Get information about an RTU file."""
        try:
            rtu_path = RtuFilePath(file_path)
            if not rtu_path.exists():
                return Result.fail("File not found", f"RTU file not found: {file_path}")

            return self._file_reader.get_file_info(file_path)

        except ValueError as e:
            return Result.fail(str(e), "Invalid RTU file path")
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return Result.fail(f"File info error: {str(e)}", "Error reading RTU file information")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for the help modal."""
        return self._converter_service.get_system_info()

    def _create_processing_options(self, options_dict: Dict[str, Any]) -> RtuProcessingOptions:
        """Create processing options from dictionary."""
        # Parse time range if provided
        time_range = None
        if options_dict.get('start_time') or options_dict.get('end_time'):
            start_time = None
            end_time = None

            if options_dict.get('start_time'):
                start_time = datetime.fromisoformat(options_dict['start_time'])
            if options_dict.get('end_time'):
                end_time = datetime.fromisoformat(options_dict['end_time'])

            time_range = RtuTimeRange(start_time, end_time)

        return RtuProcessingOptions(
            enable_peek_file_filtering=options_dict.get(
                'enable_peek_filtering', False),
            peek_file_pattern=options_dict.get('peek_pattern', "*.dt"),
            time_range=time_range,
            tags_file=options_dict.get('tags_file'),
            selected_tags=options_dict.get('selected_tags'),
            enable_sampling=options_dict.get('enable_sampling', False),
            sample_interval=options_dict.get('sample_interval', 60),
            sample_mode=options_dict.get('sample_mode', "actual"),
            output_format="csv",
            output_directory=options_dict.get('output_directory'),
            enable_parallel_processing=options_dict.get(
                'enable_parallel', True),
            max_workers=options_dict.get('max_workers'),
            tag_mapping_file=options_dict.get('tag_mapping_file'),
            tag_renaming_enabled=options_dict.get('enable_tag_renaming', False)
        )

    def _create_file_components(self, files: List[Dict[str, Any]]) -> List[dmc.Paper]:
        """Create UI components for file display."""
        if not files:
            return []

        components = []
        for i, file_info in enumerate(files):
            # Format file information
            filename = file_info.get('name', 'Unknown')
            first_timestamp = file_info.get('first_timestamp', 'Unknown')
            last_timestamp = file_info.get('last_timestamp', 'Unknown')
            total_points = file_info.get('total_points', 0)
            tags_count = file_info.get('tags_count', 0)

            # Format timestamps for display
            if isinstance(first_timestamp, datetime):
                first_str = first_timestamp.strftime('%d/%m/%y %H:%M:%S')
            else:
                first_str = str(first_timestamp)

            if isinstance(last_timestamp, datetime):
                last_str = last_timestamp.strftime('%d/%m/%y %H:%M:%S')
            else:
                last_str = str(last_timestamp)

            component = dmc.Paper(
                children=[
                    dmc.Group([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(
                                    icon="file-earmark-text", width=16),
                                dmc.Text(filename, fw=500, size="sm")
                            ], gap=5),
                            dmc.Text(
                                f"Time Range: {first_str} to {last_str}", size="xs", c="dimmed"),
                            dmc.Text(
                                f"Data Points: {total_points:,} | Tags: {tags_count}", size="xs", c="dimmed")
                        ], gap=2)
                    ], justify="space-between"),
                ],
                p="sm",
                shadow="xs",
                style={"marginBottom": "8px"}
            )
            components.append(component)

        return components

    def _background_conversion_worker(self, task_id: str, files: List[Dict[str, Any]],
                                      output_directory: str, processing_options: Dict[str, Any],
                                      task_manager=None):
        """Background worker for RTU to CSV conversion."""
        try:
            logger.info(
                f"Starting background RTU to CSV conversion: {task_id}")

            if task_manager:
                task_manager.update_task_status(
                    task_id, "running", "Starting conversion...")

            # Create processing options
            options = self._create_processing_options(processing_options)
            file_paths = [file['path'] for file in files]

            # Perform conversion
            if len(file_paths) == 1:
                result = self._converter_service.convert_file(
                    file_paths[0], output_directory, options.__dict__)
            else:
                result = self._converter_service.convert_multiple_files(
                    file_paths, output_directory, options.__dict__)

            if self._cancel_requested:
                if task_manager:
                    task_manager.update_task_status(
                        task_id, "cancelled", "Conversion cancelled by user")
                logger.info(f"Background conversion cancelled: {task_id}")
                return

            if result.success:
                if task_manager:
                    task_manager.update_task_status(task_id, "completed",
                                                    f"Successfully converted {len(file_paths)} files")
                logger.info(f"Background conversion completed: {task_id}")
            else:
                if task_manager:
                    task_manager.update_task_status(
                        task_id, "failed", result.error)
                logger.error(
                    f"Background conversion failed: {task_id} - {result.error}")

        except Exception as e:
            error_msg = f"Background conversion error: {str(e)}"
            logger.error(f"{task_id} - {error_msg}")
            if task_manager:
                task_manager.update_task_status(task_id, "failed", error_msg)

    def _create_success_alert(self, message: str) -> dmc.Alert:
        """Create a success alert component."""
        return dmc.Alert(
            title="Conversion Successful",
            children=message,
            color="green",
            icon=BootstrapIcon(icon="check")
        )

    def _create_error_alert(self, error: str) -> dmc.Alert:
        """Create an error alert component."""
        return dmc.Alert(
            title="Conversion Error",
            children=error,
            color="red",
            icon=BootstrapIcon(icon="exclamation-circle")
        )

    def _create_warning_alert(self, warning: str) -> dmc.Alert:
        """Create a warning alert component."""
        return dmc.Alert(
            title="Warning",
            children=warning,
            color="yellow",
            icon=BootstrapIcon(icon="exclamation-triangle")
        )
