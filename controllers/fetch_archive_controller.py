"""
Fetch Archive page controller following MVC pattern.
Handles UI logic and coordinates between UI components and business services.
"""

from typing import Dict, Any, List, Tuple, Optional
import dash_mantine_components as dmc
from datetime import datetime, date

from core.interfaces import IFetchArchiveController, IFetchArchiveService, Result
from components.bootstrap_icon import BootstrapIcon
from domain.archive_models import ArchiveDate, PipelineLine, OutputDirectory, ArchiveConversionConstants
from logging_config import get_logger

logger = get_logger(__name__)


class FetchArchivePageController(IFetchArchiveController):
    """Controller for fetch archive page following SOLID principles."""

    def __init__(self, archive_service: IFetchArchiveService):
        """Initialize controller with archive service dependency."""
        self._archive_service = archive_service
        logger.debug("FetchArchivePageController initialized with dependency injection")

    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle input changes and return UI updates."""
        # This method is required by IPageController but not heavily used in fetch archive page
        return Result.ok({}, "Input change handled")

    def handle_date_selection(self, archive_date: Any) -> Result[Dict[str, Any]]:
        """Handle archive date selection and validation."""
        try:
            if not archive_date:
                return Result.ok({
                    'date_status': '',
                    'valid': False,
                    'fetch_disabled': True
                }, "No date selected")

            # Create domain object to validate
            try:
                if isinstance(archive_date, str):
                    date_obj = datetime.fromisoformat(archive_date).date()
                else:
                    date_obj = archive_date

                archive_date_obj = ArchiveDate(datetime.combine(date_obj, datetime.min.time()))
                
                # Create status message
                date_status = self._create_date_status_component(archive_date_obj)
                
                return Result.ok({
                    'date_status': date_status,
                    'valid': True,
                    'fetch_disabled': False,
                    'archive_date': archive_date_obj.iso_format
                }, "Valid archive date selected")

            except ValueError as e:
                error_status = self._create_error_status_component(str(e))
                return Result.ok({
                    'date_status': error_status,
                    'valid': False,
                    'fetch_disabled': True
                }, f"Invalid date: {str(e)}")

        except Exception as e:
            logger.error(f"Error handling date selection: {str(e)}")
            error_status = self._create_error_status_component("Invalid date selected")
            return Result.ok({
                'date_status': error_status,
                'valid': False,
                'fetch_disabled': True
            }, f"Date selection error: {str(e)}")

    def handle_line_selection(self, selected_lines: List[str]) -> Result[Dict[str, Any]]:
        """Handle pipeline line selection and validation."""
        try:
            if not selected_lines:
                return Result.ok({
                    'lines_valid': False,
                    'selected_count': 0,
                    'fetch_disabled': True
                }, "No lines selected")

            # Validate each line using domain model
            valid_lines = []
            invalid_lines = []

            for line_id in selected_lines:
                try:
                    pipeline_line = PipelineLine(line_id)
                    valid_lines.append(pipeline_line.value)
                except ValueError as e:
                    invalid_lines.append(f"{line_id}: {str(e)}")

            if invalid_lines:
                return Result.fail(
                    f"Invalid lines: {', '.join(invalid_lines)}",
                    "Some selected lines are invalid"
                )

            return Result.ok({
                'lines_valid': True,
                'selected_count': len(valid_lines),
                'valid_lines': valid_lines,
                'fetch_disabled': False
            }, f"Selected {len(valid_lines)} valid pipeline lines")

        except Exception as e:
            logger.error(f"Error handling line selection: {str(e)}")
            return Result.fail(f"Line selection error: {str(e)}", "Error processing line selection")

    def handle_output_directory_selection(self, output_directory: str) -> Result[Dict[str, Any]]:
        """Handle output directory selection and validation."""
        try:
            if not output_directory:
                return Result.ok({
                    'directory_valid': False,
                    'fetch_disabled': True
                }, "No directory selected")

            # Validate using domain model
            try:
                output_dir = OutputDirectory(output_directory)
                return Result.ok({
                    'directory_valid': True,
                    'directory_path': output_dir.value,
                    'fetch_disabled': False
                }, "Valid output directory selected")

            except ValueError as e:
                return Result.fail(str(e), "Invalid output directory")

        except Exception as e:
            logger.error(f"Error handling directory selection: {str(e)}")
            return Result.fail(f"Directory selection error: {str(e)}", "Error processing directory selection")

    def handle_fetch_request(self, archive_date: Any, selected_lines: List[str], 
                             output_directory: str) -> Result[Dict[str, Any]]:
        """Handle fetch archive request execution."""
        try:
            logger.info(f"Processing fetch request for {len(selected_lines)} lines on {archive_date}")

            # Validate all inputs
            validation_result = self._validate_fetch_inputs(archive_date, selected_lines, output_directory)
            if not validation_result.success:
                return validation_result

            # Execute fetch operation
            result = self._archive_service.fetch_archive_data(archive_date, selected_lines, output_directory)
            
            if result.success:
                # Format success response for UI
                data = result.data
                files_count = len(data.get('files', []))
                failed_count = len(data.get('failed_lines', []))
                processed_lines = len(selected_lines) - failed_count

                return Result.ok({
                    'status': 'completed',
                    'files_count': files_count,
                    'processed_lines': processed_lines,
                    'failed_count': failed_count,
                    'output_directory': output_directory,
                    'notification': self._create_success_notification(files_count, processed_lines, failed_count, output_directory),
                    'result_data': data
                }, "Archive fetch completed successfully")
            else:
                return Result.fail(result.error, result.message or "Archive fetch failed")

        except Exception as e:
            logger.error(f"Error handling fetch request: {str(e)}")
            return Result.fail(f"Fetch request error: {str(e)}", "Error executing fetch request")

    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """Get available pipeline lines for UI."""
        try:
            result = self._archive_service.get_available_lines()
            
            if result.success:
                # Format lines for UI checkboxes
                checkbox_children = []
                for line in result.data:
                    checkbox_children.append(
                        dmc.Checkbox(
                            label=line['label'],
                            value=line['value'],
                            styles={
                                "input": {"border-radius": "4px"},
                                "body": {"align-items": "flex-start"},
                                "labelWrapper": {"margin-left": "8px"}
                            }
                        )
                    )

                return Result.ok({
                    'lines': result.data,
                    'checkbox_children': checkbox_children,
                    'error_message': ''
                }, f"Retrieved {len(result.data)} pipeline lines")
            else:
                # Create error message component
                error_component = dmc.Alert(
                    children=[
                        dmc.Group([
                            BootstrapIcon(icon="exclamation-triangle", width=16),
                            dmc.Text(f"Error: {result.error}", size="sm")
                        ], gap="xs")
                    ],
                    color="red",
                    variant="light",
                    className="mb-3"
                )

                return Result.ok({
                    'lines': [],
                    'checkbox_children': [],
                    'error_message': error_component
                }, result.error)

        except Exception as e:
            logger.error(f"Error getting available lines: {e}")
            error_component = dmc.Alert(
                children=[
                    dmc.Group([
                        BootstrapIcon(icon="x-circle", width=16),
                        dmc.Text(f"Error loading pipeline lines: {str(e)}", size="sm")
                    ], gap="xs")
                ],
                color="red",
                variant="light",
                className="mb-3"
            )

            return Result.ok({
                'lines': [],
                'checkbox_children': [],
                'error_message': error_component
            }, f"Error loading lines: {str(e)}")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for help modal."""
        return self._archive_service.get_system_info()

    def validate_form_state(self, archive_date: Any, selected_lines: List[str], 
                            output_directory: str, fetch_status: str) -> Result[bool]:
        """Validate complete form state for enabling/disabling fetch button."""
        try:
            # Disable if currently processing
            if fetch_status == 'processing':
                return Result.ok(False, "Processing in progress")

            # Check if all required fields are present
            if not archive_date:
                return Result.ok(False, "Archive date not selected")

            if not selected_lines:
                return Result.ok(False, "No pipeline lines selected")

            if not output_directory:
                return Result.ok(False, "Output directory not selected")

            # Validate individual components
            validation_result = self._validate_fetch_inputs(archive_date, selected_lines, output_directory)
            if not validation_result.success:
                return Result.ok(False, validation_result.error)

            return Result.ok(True, "Form is valid")

        except Exception as e:
            logger.error(f"Error validating form state: {str(e)}")
            return Result.ok(False, f"Validation error: {str(e)}")

    def _validate_fetch_inputs(self, archive_date: Any, selected_lines: List[str], 
                               output_directory: str) -> Result[bool]:
        """Validate all inputs for fetch operation."""
        try:
            # Use the service's validation method
            return self._archive_service.validate_fetch_parameters(archive_date, selected_lines, output_directory)
        except Exception as e:
            logger.error(f"Error validating fetch inputs: {str(e)}")
            return Result.fail(f"Validation error: {str(e)}", "Failed to validate inputs")

    def _create_date_status_component(self, archive_date: ArchiveDate) -> dmc.Alert:
        """Create date status component for UI."""
        return dmc.Alert(
            children=[
                dmc.Group([
                    BootstrapIcon(icon="calendar-check", width=16),
                    dmc.Text(
                        f"Selected: {archive_date.display_format} (Folder: {archive_date.folder_name})", 
                        size="sm"
                    )
                ], gap="xs")
            ],
            color="blue",
            variant="light"
        )

    def _create_error_status_component(self, error_message: str) -> dmc.Alert:
        """Create error status component for UI."""
        return dmc.Alert(
            children=[
                dmc.Group([
                    BootstrapIcon(icon="exclamation-triangle", width=16),
                    dmc.Text(error_message, size="sm")
                ], gap="xs")
            ],
            color="yellow",
            variant="light"
        )

    def _create_success_notification(self, files_count: int, processed_lines: int, 
                                     failed_count: int, output_directory: str) -> Dict[str, Any]:
        """Create success notification for UI."""
        if failed_count == 0:
            # Complete success
            if processed_lines == 1:
                title = "Fetch Complete!"
                message = f"Successfully processed 1 line ({files_count} file(s) extracted) to {output_directory}"
            else:
                title = "Fetch Complete!"
                message = f"Successfully processed {processed_lines} lines ({files_count} file(s) extracted) to {output_directory}"
            color = "green"
        else:
            # Partial success
            title = "Partial Success"
            message = f"Processed {processed_lines} line(s), {failed_count} failed ({files_count} file(s) extracted). Check logs for details."
            color = "yellow"

        return {
            "title": title,
            "message": message,
            "color": color,
            "autoClose": 7000,
            "action": "show"
        }


class FetchArchiveUIResponseFormatter:
    """Formats controller responses for Dash callback returns."""

    @staticmethod
    def format_lines_response(controller_result: Result) -> Tuple[List, List, Any]:
        """Format get available lines response for UI callback."""
        if controller_result.success:
            data = controller_result.data
            return data['lines'], data['checkbox_children'], data['error_message']
        else:
            return [], [], controller_result.error

    @staticmethod
    def format_date_status_response(controller_result: Result) -> Any:
        """Format date selection response for UI callback."""
        if controller_result.success:
            return controller_result.data.get('date_status', '')
        else:
            return FetchArchivePageController._create_error_status_component(controller_result.error)

    @staticmethod
    def format_fetch_response(controller_result: Result) -> Tuple[str, Dict, bool, List]:
        """Format fetch request response for UI callback."""
        if controller_result.success:
            data = controller_result.data
            return (
                "",  # Clear processing status
                {'status': data['status']},  # Update status store
                False,  # Re-enable button
                [data['notification']]  # Send notification
            )
        else:
            error_notification = {
                "title": "Fetch Failed",
                "message": controller_result.error,
                "color": "red",
                "autoClose": 7000,
                "action": "show"
            }
            return (
                "",  # Clear processing status
                {'status': 'error'},  # Update status store
                False,  # Re-enable button
                [error_notification]  # Send error notification
            )

    @staticmethod
    def format_form_validation_response(controller_result: Result) -> bool:
        """Format form validation response for UI callback."""
        if controller_result.success:
            return not controller_result.data  # Return True to disable button if form invalid
        else:
            return True  # Disable button on validation error