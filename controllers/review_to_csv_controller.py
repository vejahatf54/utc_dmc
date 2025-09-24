"""
Review to CSV page controller following MVC pattern.
Handles UI logic and coordinates between UI components and business services.
"""

from typing import Dict, Any, List, Tuple, Optional
import dash_mantine_components as dmc
import tempfile
import threading
import time
from datetime import datetime

from core.interfaces import IPageController, IReviewToCsvConverter, IReviewFileReader, Result
from components.bootstrap_icon import BootstrapIcon
from domain.review_models import (
    ReviewDirectoryPath, ReviewTimeRange, ReviewPeekFile,
    ReviewProcessingOptions, ReviewConversionConstants
)
from logging_config import get_logger

logger = get_logger(__name__)


class ReviewToCsvPageController(IPageController):
    """Controller for Review to CSV converter page."""

    def __init__(self, converter_service: IReviewToCsvConverter, file_reader: IReviewFileReader):
        """Initialize controller with converter service and file reader."""
        self._converter_service = converter_service
        self._file_reader = file_reader
        self._background_task_manager = BackgroundTaskManager()

    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle input changes and return UI updates."""
        # This method is required by IPageController but not heavily used in Review to CSV page
        return Result.ok({}, "Input change handled")

    def handle_directory_selection(self, directory_path: str) -> Result[Dict[str, Any]]:
        """Handle Review directory selection and validation."""
        try:
            if not directory_path or not directory_path.strip():
                return Result.ok({
                    'directory_info': {},
                    'directory_components': [],
                    'status_message': "No directory selected",
                    'process_disabled': True
                }, "No directory selected")

            # Get directory information
            info_result = self._converter_service.get_directory_info(
                directory_path)
            if not info_result.success:
                return Result.ok({
                    'directory_info': {},
                    'directory_components': [],
                    'status_message': f"Error: {info_result.error}",
                    'process_disabled': True
                }, info_result.error)

            directory_info = info_result.data

            # Create UI components for directory info
            directory_components = self._create_directory_components(
                directory_info)

            # Create status message
            files_count = directory_info['review_files_count']
            total_size_mb = directory_info['total_size_mb']
            status_message = f"Found {files_count} Review files ({total_size_mb} MB total)"

            return Result.ok({
                'directory_info': directory_info,
                'directory_components': directory_components,
                'status_message': status_message,
                'process_disabled': files_count == 0
            }, f"Validated Review directory with {files_count} files")

        except Exception as e:
            logger.error(f"Error in directory selection: {str(e)}")
            return Result.fail(f"Directory selection error: {str(e)}", "Error processing directory selection")

    def handle_processing_start(self, directory_path: str, processing_options: Dict[str, Any]) -> Result[Dict[str, Any]]:
        """Handle Review to CSV processing start."""
        try:
            if not directory_path or not directory_path.strip():
                return Result.fail("No directory selected", "Review directory is required")

            # Validate processing options
            validation_result = self._validate_processing_options(
                processing_options)
            if not validation_result.success:
                return validation_result

            # Start background processing
            task_id = self._start_background_processing(
                directory_path, processing_options)

            return Result.ok({
                'task_id': task_id,
                'status': 'started',
                'message': 'Review processing started in background'
            }, "Review processing started successfully")

        except Exception as e:
            logger.error(f"Error starting processing: {str(e)}")
            return Result.fail(f"Processing start error: {str(e)}", "Error starting Review processing")

    def handle_processing_status_check(self) -> Result[Dict[str, Any]]:
        """Check the status of background processing."""
        try:
            status = self._background_task_manager.get_status()
            return Result.ok(status, "Status retrieved successfully")

        except Exception as e:
            logger.error(f"Error checking processing status: {str(e)}")
            return Result.fail(f"Status check error: {str(e)}", "Error checking processing status")

    def handle_processing_cancellation(self) -> Result[Dict[str, Any]]:
        """Handle cancellation of Review processing."""
        try:
            # Cancel the converter service
            cancel_result = self._converter_service.cancel_conversion()

            # Update task manager
            self._background_task_manager.cancel_task()

            if cancel_result.success:
                return Result.ok({
                    'cancelled': True,
                    'message': 'Processing cancellation requested'
                }, "Processing cancellation requested successfully")
            else:
                return Result.fail(cancel_result.error, "Error requesting cancellation")

        except Exception as e:
            logger.error(f"Error cancelling processing: {str(e)}")
            return Result.fail(f"Cancellation error: {str(e)}", "Error cancelling Review processing")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for the Review to CSV converter."""
        try:
            return self._converter_service.get_system_info()
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return Result.fail(f"System info error: {str(e)}", "Error getting system information")

    def _validate_processing_options(self, options: Dict[str, Any]) -> Result[bool]:
        """Validate processing options."""
        try:
            # Check required fields
            required_fields = ['start_time', 'end_time']
            for field in required_fields:
                if field not in options or not options[field]:
                    return Result.fail(f"Missing required field: {field}", "Invalid processing options")

            # Validate time range
            try:
                time_range = ReviewTimeRange(
                    options['start_time'], options['end_time'])
                if not time_range.is_valid_range():
                    return Result.fail("Invalid time range", "Start time must be before end time")
            except ValueError as e:
                return Result.fail(str(e), "Invalid time range format")

            # Validate frequency if provided
            if not options.get('dump_all', False):
                frequency = options.get('frequency_minutes')
                if frequency is not None:
                    if not isinstance(frequency, (int, float)) or frequency <= 0:
                        return Result.fail("Invalid frequency", "Frequency must be a positive number")

            return Result.ok(True, "Processing options are valid")

        except Exception as e:
            logger.error(f"Error validating processing options: {str(e)}")
            return Result.fail(f"Validation error: {str(e)}", "Error validating processing options")

    def _start_background_processing(self, directory_path: str, processing_options: Dict[str, Any]) -> str:
        """Start background processing task."""
        task_id = f"review_task_{int(datetime.now().timestamp())}"

        # Start background thread
        thread = threading.Thread(
            target=self._background_processing_wrapper,
            args=(task_id, directory_path, processing_options),
            daemon=True
        )
        thread.start()

        # Update task manager
        self._background_task_manager.start_task(task_id)

        return task_id

    def _background_processing_wrapper(self, task_id: str, directory_path: str, processing_options: Dict[str, Any]):
        """Wrapper for background processing."""
        try:
            self._background_task_manager.update_progress(
                "Initializing Review file processing...")

            # Convert the directory
            result = self._converter_service.convert_directory(
                directory_path, directory_path, processing_options)

            # Complete the task
            if result.success:
                self._background_task_manager.complete_task({
                    'success': True,
                    'task_id': task_id,
                    'output_directory': directory_path,
                    'message': 'Review files converted successfully',
                    **result.data
                })
            else:
                self._background_task_manager.complete_task({
                    'success': False,
                    'error': result.error,
                    'task_id': task_id
                })

        except Exception as e:
            logger.error(
                f"Background processing failed: {str(e)}", exc_info=True)
            self._background_task_manager.complete_task({
                'success': False,
                'error': f"Processing failed: {str(e)}",
                'task_id': task_id
            })

    def _create_directory_components(self, directory_info: Dict[str, Any]) -> List[Any]:
        """Create UI components for directory information display."""
        components = []

        if directory_info['review_files_count'] > 0:
            # Create file list component
            file_items = []
            for file_info in directory_info.get('files', []):
                file_items.append(
                    dmc.Text(
                        f"{file_info['filename']} ({file_info['file_size_mb']} MB)",
                        size="sm"
                    )
                )

            components.append(
                dmc.Stack([
                    dmc.Text(
                        f"Review Files ({directory_info['review_files_count']}):", weight=500),
                    dmc.ScrollArea(
                        dmc.Stack(file_items),
                        h=200 if len(file_items) > 10 else "auto"
                    )
                ])
            )

        return components


class BackgroundTaskManager:
    """Manages background task status and progress."""

    def __init__(self):
        self.current_task_id = None
        self.task_status = 'idle'
        self.task_result = None
        self.progress_message = ""
        self.lock = threading.Lock()

    def start_task(self, task_id: str):
        """Start a new task."""
        with self.lock:
            self.current_task_id = task_id
            self.task_status = 'running'
            self.task_result = None
            self.progress_message = "Starting processing..."

    def update_progress(self, message: str):
        """Update task progress message."""
        with self.lock:
            if self.task_status == 'running':
                self.progress_message = message

    def complete_task(self, result: Dict[str, Any]):
        """Complete the current task."""
        with self.lock:
            self.task_result = result
            self.task_status = 'completed'
            if result and result.get('success'):
                self.progress_message = "Processing completed successfully"
            else:
                error_msg = result.get(
                    'error', 'Unknown error') if result else 'Processing failed'
                self.progress_message = f"Processing failed: {error_msg}"

    def cancel_task(self):
        """Cancel the current task."""
        with self.lock:
            if self.task_status == 'running':
                self.task_status = 'cancelled'
                self.progress_message = "Processing cancelled by user"

    def get_status(self) -> Dict[str, Any]:
        """Get current task status."""
        with self.lock:
            return {
                'task_id': self.current_task_id,
                'status': self.task_status,
                'result': self.task_result,
                'progress': self.progress_message
            }


class ReviewToCsvUIResponseFormatter:
    """Formats responses for Dash UI callbacks."""

    @staticmethod
    def format_directory_selection_response(result: Result[Dict[str, Any]]) -> Tuple[List[Any], str, bool]:
        """Format directory selection response for UI."""
        if result.success:
            data = result.data
            return (
                data.get('directory_components', []),
                data.get('status_message', ''),
                data.get('process_disabled', True)
            )
        else:
            return ([], f"Error: {result.error}", True)

    @staticmethod
    def format_processing_response(result: Result[Dict[str, Any]]) -> Tuple[str, bool]:
        """Format processing response for UI."""
        if result.success:
            data = result.data
            return (data.get('message', 'Processing started'), False)
        else:
            return (f"Error: {result.error}", True)

    @staticmethod
    def format_status_response(result: Result[Dict[str, Any]]) -> Tuple[str, bool, str]:
        """Format status response for UI."""
        if result.success:
            data = result.data
            status = data.get('status', 'idle')
            progress = data.get('progress', '')

            if status == 'running':
                return (progress, False, "Processing...")
            elif status == 'completed':
                task_result = data.get('result', {})
                if task_result and task_result.get('success'):
                    return ("Processing completed successfully", True, "Complete")
                else:
                    error = task_result.get(
                        'error', 'Unknown error') if task_result else 'Processing failed'
                    return (f"Processing failed: {error}", True, "Error")
            elif status == 'cancelled':
                return ("Processing cancelled", True, "Cancelled")
            else:
                return ("Ready", True, "Ready")
        else:
            return (f"Status check error: {result.error}", True, "Error")
