"""
RTU Resizer page controller following MVC pattern.
Handles UI logic and coordinates between UI components and business services.
"""

from typing import Dict, Any, Optional, Tuple
import dash_mantine_components as dmc
import os
import threading
from datetime import datetime, date, timedelta
from pathlib import Path

from core.interfaces import IPageController, IRtuResizer, IRtuFileReader, Result
from components.bootstrap_icon import BootstrapIcon
from domain.rtu_models import RtuFilePath, RtuTimeRange, RtuFileInfo, RtuConversionConstants
from logging_config import get_logger

logger = get_logger(__name__)


class RtuResizerPageController(IPageController):
    """Controller for RTU resizer page."""

    def __init__(self, resizer_service: IRtuResizer, file_reader: IRtuFileReader):
        """Initialize controller with resizer service and file reader."""
        self._resizer_service = resizer_service
        self._file_reader = file_reader
        self._current_file_info = None
        self._background_thread = None
        self._cancel_requested = False

    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle input changes and return UI updates."""
        # This method is required by IPageController but not heavily used in RTU resizer page
        return Result.ok({}, "Input change handled")

    def handle_file_selection(self, file_path: str) -> Result[Dict[str, Any]]:
        """Handle RTU file selection and load file information."""
        try:
            if not file_path:
                self._current_file_info = None
                return Result.ok({
                    'file_loaded': False,
                    'file_info': {},
                    'resize_disabled': True,
                    'status_message': "No file selected"
                }, "No file selected")

            # Validate file path
            rtu_path = RtuFilePath(file_path)
            if not rtu_path.exists():
                return Result.fail("File not found", f"RTU file not found: {file_path}")

            # Get file information
            info_result = self._file_reader.get_file_info(file_path)
            if not info_result.success:
                return Result.fail(info_result.error, "Failed to read RTU file information")

            file_info = info_result.data
            self._current_file_info = file_info

            # Format file information for UI
            ui_info = {
                'path': file_path,
                'name': rtu_path.filename,
                'first_timestamp': file_info.get('first_timestamp'),
                'last_timestamp': file_info.get('last_timestamp'),
                'total_points': file_info.get('total_points', 0),
                'tags_count': file_info.get('tags_count', 0),
                'duration_seconds': file_info.get('duration_seconds', 0)
            }

            return Result.ok({
                'file_loaded': True,
                'file_info': ui_info,
                'resize_disabled': False,
                'status_message': f"Loaded RTU file: {rtu_path.filename}"
            }, "RTU file loaded successfully")

        except ValueError as e:
            logger.error(f"Invalid file path: {str(e)}")
            return Result.fail(str(e), "Invalid RTU file path")
        except Exception as e:
            logger.error(f"Error loading RTU file: {str(e)}")
            return Result.fail(f"File loading error: {str(e)}", "Error loading RTU file")

    def handle_resize_request(self, input_file_path: str, output_file_path: str,
                              start_time: Optional[str] = None, end_time: Optional[str] = None,
                              tag_mapping_file: Optional[str] = None) -> Result[Dict[str, Any]]:
        """Handle RTU file resize request."""
        try:
            # Validate resize request
            validation_result = self._resizer_service.validate_resize_request(
                input_file_path, output_file_path, start_time, end_time)

            if not validation_result.success:
                return Result.fail(validation_result.error, "Invalid resize request")

            # Perform resize operation
            resize_result = self._resizer_service.resize_file(
                input_file_path, output_file_path, start_time, end_time, tag_mapping_file)

            if resize_result.success:
                result_data = resize_result.data
                return Result.ok({
                    'status': 'completed',
                    'message': "RTU file resized successfully",
                    'output_file': output_file_path,
                    'input_points': result_data.get('input_points', 0),
                    'output_points': result_data.get('output_points', 0),
                    'processing_time': result_data.get('processing_time', 0)
                }, "Resize completed successfully")
            else:
                return Result.fail(resize_result.error, "Resize operation failed")

        except Exception as e:
            logger.error(f"Error in resize request: {str(e)}")
            return Result.fail(f"Resize error: {str(e)}", "Error during RTU file resize")

    def handle_background_resize(self, input_file_path: str, output_file_path: str,
                                 start_time: Optional[str] = None, end_time: Optional[str] = None,
                                 tag_mapping_file: Optional[str] = None,
                                 task_manager=None) -> str:
        """Start RTU resize operation in background thread."""
        task_id = f"rtu_resize_task_{int(datetime.now().timestamp())}"

        self._cancel_requested = False
        self._background_thread = threading.Thread(
            target=self._background_resize_worker,
            args=(task_id, input_file_path, output_file_path,
                  start_time, end_time, tag_mapping_file, task_manager)
        )
        self._background_thread.daemon = True
        self._background_thread.start()

        return task_id

    def cancel_background_resize(self) -> None:
        """Cancel the background resize process."""
        self._cancel_requested = True
        if self._background_thread and self._background_thread.is_alive():
            logger.info("Background resize cancellation requested")

    def validate_time_range(self, start_time: Optional[str], end_time: Optional[str]) -> Result[Dict[str, Any]]:
        """Validate the specified time range against current file bounds."""
        try:
            if not self._current_file_info:
                return Result.fail("No file loaded", "Please load an RTU file first")

            file_start = self._current_file_info.get('first_timestamp')
            file_end = self._current_file_info.get('last_timestamp')

            if not file_start or not file_end:
                return Result.fail("Invalid file timestamps", "Cannot validate time range - file timestamps unavailable")

            # Parse input times if provided
            parsed_start = None
            parsed_end = None

            if start_time:
                try:
                    parsed_start = datetime.strptime(
                        start_time, RtuConversionConstants.TIME_FORMAT_DMY)
                except ValueError:
                    return Result.fail("Invalid start time format", f"Expected format: {RtuConversionConstants.TIME_FORMAT_DMY}")

            if end_time:
                try:
                    parsed_end = datetime.strptime(
                        end_time, RtuConversionConstants.TIME_FORMAT_DMY)
                except ValueError:
                    return Result.fail("Invalid end time format", f"Expected format: {RtuConversionConstants.TIME_FORMAT_DMY}")

            # Validate range logic
            if parsed_start and parsed_end and parsed_start >= parsed_end:
                return Result.fail("Invalid time range", "Start time must be before end time")

            # Validate against file bounds
            warnings = []
            if parsed_start and parsed_start < file_start:
                warnings.append(
                    f"Start time is before file start ({file_start.strftime(RtuConversionConstants.TIME_FORMAT_DMY)})")

            if parsed_end and parsed_end > file_end:
                warnings.append(
                    f"End time is after file end ({file_end.strftime(RtuConversionConstants.TIME_FORMAT_DMY)})")

            return Result.ok({
                'valid': True,
                'warnings': warnings,
                'file_start': file_start,
                'file_end': file_end,
                'requested_start': parsed_start,
                'requested_end': parsed_end
            }, "Time range validated")

        except Exception as e:
            logger.error(f"Error validating time range: {str(e)}")
            return Result.fail(f"Validation error: {str(e)}", "Error validating time range")

    def get_file_time_bounds(self) -> Result[Dict[str, Any]]:
        """Get the time bounds of the currently loaded file."""
        if not self._current_file_info:
            return Result.fail("No file loaded", "Please load an RTU file first")

        file_start = self._current_file_info.get('first_timestamp')
        file_end = self._current_file_info.get('last_timestamp')

        if not file_start or not file_end:
            return Result.fail("Invalid file timestamps", "File timestamps unavailable")

        return Result.ok({
            'first_timestamp': file_start,
            'last_timestamp': file_end,
            'first_timestamp_str': file_start.strftime(RtuConversionConstants.TIME_FORMAT_DMY),
            'last_timestamp_str': file_end.strftime(RtuConversionConstants.TIME_FORMAT_DMY),
            'duration_seconds': (file_end - file_start).total_seconds()
        }, "File time bounds retrieved")

    def generate_output_filename(self, input_file_path: str, start_time: Optional[str] = None,
                                 end_time: Optional[str] = None) -> Result[str]:
        """Generate an appropriate output filename based on input and time range."""
        try:
            input_path = Path(input_file_path)
            base_name = input_path.stem
            extension = input_path.suffix

            # Add time range to filename if specified
            if start_time or end_time:
                time_suffix = ""
                if start_time:
                    # Convert to safe filename format
                    safe_start = start_time.replace(
                        "/", "").replace(":", "").replace(" ", "_")
                    time_suffix += f"_from_{safe_start}"
                if end_time:
                    safe_end = end_time.replace(
                        "/", "").replace(":", "").replace(" ", "_")
                    time_suffix += f"_to_{safe_end}"

                output_filename = f"{base_name}{time_suffix}{extension}"
            else:
                output_filename = f"{base_name}_resized{extension}"

            return Result.ok(output_filename, "Output filename generated")

        except Exception as e:
            logger.error(f"Error generating output filename: {str(e)}")
            return Result.fail(f"Filename generation error: {str(e)}", "Error generating output filename")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for the help modal."""
        return self._resizer_service.get_system_info()

    def clear_current_file(self) -> None:
        """Clear the currently loaded file information."""
        self._current_file_info = None
        logger.debug("Cleared current RTU file")

    def _background_resize_worker(self, task_id: str, input_file_path: str, output_file_path: str,
                                  start_time: Optional[str], end_time: Optional[str],
                                  tag_mapping_file: Optional[str], task_manager=None):
        """Background worker for RTU resize operation."""
        try:
            logger.info(f"Starting background RTU resize: {task_id}")

            if task_manager:
                task_manager.update_task_status(
                    task_id, "running", "Starting resize operation...")

            # Perform resize
            result = self._resizer_service.resize_file(
                input_file_path, output_file_path, start_time, end_time, tag_mapping_file)

            if self._cancel_requested:
                if task_manager:
                    task_manager.update_task_status(
                        task_id, "cancelled", "Resize cancelled by user")
                logger.info(f"Background resize cancelled: {task_id}")
                return

            if result.success:
                result_data = result.data
                message = f"Successfully resized RTU file. Output: {output_file_path}"
                if task_manager:
                    task_manager.update_task_status(
                        task_id, "completed", message)
                logger.info(f"Background resize completed: {task_id}")
            else:
                if task_manager:
                    task_manager.update_task_status(
                        task_id, "failed", result.error)
                logger.error(
                    f"Background resize failed: {task_id} - {result.error}")

        except Exception as e:
            error_msg = f"Background resize error: {str(e)}"
            logger.error(f"{task_id} - {error_msg}")
            if task_manager:
                task_manager.update_task_status(task_id, "failed", error_msg)

    def _create_success_alert(self, message: str) -> dmc.Alert:
        """Create a success alert component."""
        return dmc.Alert(
            title="Resize Successful",
            children=message,
            color="green",
            icon=BootstrapIcon(icon="check")
        )

    def _create_error_alert(self, error: str) -> dmc.Alert:
        """Create an error alert component."""
        return dmc.Alert(
            title="Resize Error",
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
