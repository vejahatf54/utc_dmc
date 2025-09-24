"""
Fetch RTU Data page controller following MVC pattern and SOLID principles.
Handles UI logic and coordinates between UI components and business services.
"""

from typing import Dict, Any, List, Optional
import dash_mantine_components as dmc
from datetime import datetime, date

from core.interfaces import IFetchRtuDataController, IFetchRtuDataService, Result
from components.bootstrap_icon import BootstrapIcon
from domain.rtu_models import (
    RtuDate, RtuDateRange, RtuServerFilter, RtuLineSelection, 
    RtuOutputDirectory, RtuFetchResult, RtuFetchConstants
)
from validation.rtu_validators import (
    RtuDateInputValidator, RtuDateRangeValidator, RtuLineSelectionValidator,
    RtuOutputDirectoryValidator, RtuServerFilterValidator, RtuParallelWorkersValidator,
    CompositeRtuValidator
)
from logging_config import get_logger

logger = get_logger(__name__)


class FetchRtuDataPageController(IFetchRtuDataController):
    """Controller for fetch RTU data page following SOLID principles."""

    def __init__(self, 
                 rtu_service: IFetchRtuDataService,
                 composite_validator: CompositeRtuValidator = None):
        """Initialize controller with service dependencies."""
        self._rtu_service = rtu_service
        self._composite_validator = composite_validator or CompositeRtuValidator()
        
        # Individual validators for specific operations
        self._date_validator = RtuDateInputValidator()
        self._date_range_validator = RtuDateRangeValidator(self._date_validator)
        self._line_validator = RtuLineSelectionValidator()
        self._directory_validator = RtuOutputDirectoryValidator()
        self._filter_validator = RtuServerFilterValidator()
        self._workers_validator = RtuParallelWorkersValidator()
        
        logger.debug("FetchRtuDataPageController initialized with dependency injection")

    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle generic input changes."""
        # This method is required by IPageController but not heavily used in RTU fetch page
        return Result.ok({}, "Input change handled")

    def handle_date_mode_change(self, mode: str) -> Result[Dict[str, Any]]:
        """Handle date mode selection (single/range)."""
        try:
            if mode not in ['single', 'range']:
                return Result.fail("Invalid date mode. Must be 'single' or 'range'")

            # Return UI state updates for date mode change
            if mode == 'single':
                return Result.ok({
                    'single_date_container_style': {"display": "block"},
                    'date_range_container_style': {"display": "none"},
                    'date_mode': 'single'
                }, "Single date mode selected")
            else:
                return Result.ok({
                    'single_date_container_style': {"display": "none"},
                    'date_range_container_style': {"display": "block"},
                    'date_mode': 'range'
                }, "Date range mode selected")

        except Exception as e:
            logger.error(f"Error handling date mode change: {str(e)}")
            return Result.fail(f"Date mode change error: {str(e)}")

    def handle_single_date_selection(self, date_value: Any) -> Result[Dict[str, Any]]:
        """Handle single date selection and validation."""
        try:
            if not date_value:
                return Result.ok({
                    'date_status': '',
                    'valid': False
                }, "No date selected")

            # Validate single date
            date_result = self._date_validator.validate(date_value)
            
            if date_result.success:
                rtu_date = date_result.data
                status_component = self._create_date_status_component(rtu_date, is_single=True)
                
                return Result.ok({
                    'date_status': status_component,
                    'valid': True,
                    'rtu_date': rtu_date
                }, f"Valid single date: {rtu_date.display_format}")
            else:
                error_status = self._create_error_status_component(date_result.error)
                return Result.ok({
                    'date_status': error_status,
                    'valid': False
                }, f"Invalid single date: {date_result.error}")

        except Exception as e:
            logger.error(f"Error handling single date selection: {str(e)}")
            error_status = self._create_error_status_component("Invalid date selected")
            return Result.ok({
                'date_status': error_status,
                'valid': False
            }, f"Single date selection error: {str(e)}")

    def handle_date_range_selection(self, start_date: Any, end_date: Any) -> Result[Dict[str, Any]]:
        """Handle date range selection and validation."""
        try:
            if not start_date or not end_date:
                return Result.ok({
                    'date_status': '',
                    'valid': False
                }, "Incomplete date range")

            # Validate date range
            date_range_data = {
                'start_date': start_date,
                'end_date': end_date
            }
            
            range_result = self._date_range_validator.validate(date_range_data)
            
            if range_result.success:
                date_range = range_result.data
                status_component = self._create_date_range_status_component(date_range)
                
                return Result.ok({
                    'date_status': status_component,
                    'valid': True,
                    'date_range': date_range
                }, f"Valid date range: {str(date_range)}")
            else:
                error_status = self._create_error_status_component(range_result.error)
                return Result.ok({
                    'date_status': error_status,
                    'valid': False
                }, f"Invalid date range: {range_result.error}")

        except Exception as e:
            logger.error(f"Error handling date range selection: {str(e)}")
            error_status = self._create_error_status_component("Invalid date range selected")
            return Result.ok({
                'date_status': error_status,
                'valid': False
            }, f"Date range selection error: {str(e)}")

    def handle_line_selection(self, selected_lines: List[str]) -> Result[Dict[str, Any]]:
        """Handle pipeline line selection and validation."""
        try:
            if not selected_lines:
                return Result.ok({
                    'lines_valid': False,
                    'selected_count': 0
                }, "No lines selected")

            # Validate line selection
            line_result = self._line_validator.validate(selected_lines)
            
            if line_result.success:
                line_selection = line_result.data
                return Result.ok({
                    'lines_valid': True,
                    'selected_count': line_selection.count,
                    'line_selection': line_selection
                }, f"Valid line selection: {str(line_selection)}")
            else:
                return Result.ok({
                    'lines_valid': False,
                    'selected_count': 0,
                    'error': line_result.error
                }, f"Invalid line selection: {line_result.error}")

        except Exception as e:
            logger.error(f"Error handling line selection: {str(e)}")
            return Result.ok({
                'lines_valid': False,
                'selected_count': 0,
                'error': str(e)
            }, f"Line selection error: {str(e)}")

    def handle_output_directory_selection(self, output_directory: str) -> Result[Dict[str, Any]]:
        """Handle output directory selection and validation."""
        try:
            if not output_directory:
                return Result.ok({
                    'directory_valid': False,
                    'directory_status': ''
                }, "No directory selected")

            # Validate output directory
            dir_result = self._directory_validator.validate(output_directory)
            
            if dir_result.success:
                output_dir = dir_result.data
                return Result.ok({
                    'directory_valid': True,
                    'directory_status': f"✓ {output_dir.path_str}",
                    'output_directory': output_dir
                }, f"Valid output directory: {output_dir.path_str}")
            else:
                return Result.ok({
                    'directory_valid': False,
                    'directory_status': f"✗ {dir_result.error}",
                    'error': dir_result.error
                }, f"Invalid output directory: {dir_result.error}")

        except Exception as e:
            logger.error(f"Error handling output directory selection: {str(e)}")
            return Result.ok({
                'directory_valid': False,
                'directory_status': f"✗ Error: {str(e)}",
                'error': str(e)
            }, f"Directory selection error: {str(e)}")

    def handle_server_filter_change(self, filter_pattern: str) -> Result[Dict[str, Any]]:
        """Handle server filter pattern changes."""
        try:
            # Validate server filter
            filter_result = self._filter_validator.validate(filter_pattern)
            
            if filter_result.success:
                server_filter = filter_result.data
                return Result.ok({
                    'filter_valid': True,
                    'server_filter': server_filter
                }, f"Valid server filter: {str(server_filter)}")
            else:
                return Result.ok({
                    'filter_valid': False,
                    'error': filter_result.error
                }, f"Invalid server filter: {filter_result.error}")

        except Exception as e:
            logger.error(f"Error handling server filter change: {str(e)}")
            return Result.ok({
                'filter_valid': False,
                'error': str(e)
            }, f"Server filter error: {str(e)}")

    def handle_fetch_request(self, mode: str, single_date: Any, start_date: Any, end_date: Any,
                             selected_lines: List[str], output_directory: str, 
                             server_filter: str = None, max_parallel_workers: int = 4) -> Result[Dict[str, Any]]:
        """Handle RTU data fetch request execution."""
        try:
            logger.info("Processing RTU data fetch request")

            # Prepare request data for validation
            fetch_request = {
                'mode': mode,
                'single_date': single_date,
                'start_date': start_date,
                'end_date': end_date,
                'selected_lines': selected_lines,
                'output_directory': output_directory,
                'server_filter': server_filter,
                'max_parallel_workers': max_parallel_workers
            }

            # Validate complete request
            validation_result = self._composite_validator.validate(fetch_request)
            if not validation_result.success:
                return Result.fail(validation_result.error)

            validated_data = validation_result.data

            # Extract validated domain objects
            date_range = validated_data['date_range']
            line_selection = validated_data['line_selection']
            output_dir = validated_data['output_directory']
            server_filter_obj = validated_data['server_filter']
            workers = validated_data['max_parallel_workers']

            # Execute fetch operation
            fetch_result = self._rtu_service.fetch_rtu_data(
                line_selection=line_selection,
                date_range=date_range,
                output_directory=output_dir,
                server_filter=server_filter_obj,
                max_parallel_workers=workers
            )

            if fetch_result.success:
                rtu_result = fetch_result.data
                
                # Create success response
                success_status = self._create_success_status_component(rtu_result)
                notification = self._create_success_notification(rtu_result)
                
                return Result.ok({
                    'processing_status': success_status,
                    'fetch_result': rtu_result,
                    'notification': notification,
                    'button_disabled': False
                }, "RTU data fetch completed successfully")
            else:
                # Create error response
                error_status = self._create_error_status_component(fetch_result.error)
                notification = self._create_error_notification(fetch_result.error)
                
                return Result.ok({
                    'processing_status': error_status,
                    'notification': notification,
                    'button_disabled': False
                }, f"RTU data fetch failed: {fetch_result.error}")

        except Exception as e:
            logger.error(f"Unexpected error in RTU fetch request: {str(e)}")
            error_status = self._create_error_status_component(f"Unexpected error: {str(e)}")
            notification = self._create_error_notification(f"Unexpected error: {str(e)}")
            
            return Result.ok({
                'processing_status': error_status,
                'notification': notification,
                'button_disabled': False
            }, f"RTU fetch request error: {str(e)}")

    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """Get available pipeline lines for UI."""
        try:
            lines_result = self._rtu_service.get_available_lines()
            
            if lines_result.success:
                return Result.ok(lines_result.data, f"Retrieved {len(lines_result.data)} available lines")
            else:
                return Result.fail(lines_result.error)

        except Exception as e:
            logger.error(f"Error getting available lines: {str(e)}")
            return Result.fail(f"Error loading pipeline lines: {str(e)}")

    def validate_fetch_form(self, mode: str, single_date: Any, start_date: Any, end_date: Any,
                            selected_lines: List[str], output_directory: str) -> Result[bool]:
        """Validate fetch form inputs."""
        try:
            # Check basic requirements
            if not selected_lines:
                return Result.ok(False, "No lines selected")

            if not output_directory:
                return Result.ok(False, "No output directory selected")

            # Validate dates based on mode
            if mode == 'single':
                if not single_date:
                    return Result.ok(False, "No single date selected")
            else:  # range mode
                if not start_date or not end_date:
                    return Result.ok(False, "Incomplete date range")

            # All basic validations passed
            return Result.ok(True, "Form validation passed")

        except Exception as e:
            logger.error(f"Error validating fetch form: {str(e)}")
            return Result.fail(f"Form validation error: {str(e)}")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for help modal."""
        try:
            # Get system info from domain constants
            system_info = RtuFetchConstants.get_system_info()
            
            # Add data source availability
            availability_result = self._rtu_service.validate_data_source_availability()
            system_info['data_source_available'] = availability_result.data if availability_result.success else False
            system_info['data_source_message'] = availability_result.message or availability_result.error

            return Result.ok(system_info, "System information retrieved")

        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return Result.fail(f"Error retrieving system information: {str(e)}")

    # Helper methods for UI component creation
    def _create_date_status_component(self, rtu_date: RtuDate, is_single: bool = False) -> dmc.Text:
        """Create date status component for single date."""
        if is_single:
            text = f"✓ From {rtu_date.display_format} to Today"
        else:
            text = f"✓ {rtu_date.display_format}"
        
        return dmc.Text(text, c="green", size="sm", fw=500)

    def _create_date_range_status_component(self, date_range: RtuDateRange) -> dmc.Text:
        """Create date status component for date range."""
        text = f"✓ {str(date_range)} ({date_range.day_count} days)"
        return dmc.Text(text, c="green", size="sm", fw=500)

    def _create_error_status_component(self, error_message: str) -> dmc.Text:
        """Create error status component."""
        return dmc.Text(f"✗ {error_message}", c="red", size="sm")

    def _create_success_status_component(self, rtu_result: RtuFetchResult) -> dmc.Text:
        """Create success status component."""
        return dmc.Text(rtu_result.summary_text, c="green", size="sm", fw=500)

    def _create_success_notification(self, rtu_result: RtuFetchResult) -> Dict[str, Any]:
        """Create success notification."""
        return {
            'id': f'rtu-fetch-success-{datetime.now().timestamp()}',
            'message': rtu_result.summary_text,
            'color': 'green',
            'autoClose': 5000,
            'icon': BootstrapIcon(icon="check-circle", width=20)
        }

    def _create_error_notification(self, error_message: str) -> Dict[str, Any]:
        """Create error notification."""
        return {
            'id': f'rtu-fetch-error-{datetime.now().timestamp()}',
            'message': f"RTU data fetch failed: {error_message}",
            'color': 'red',
            'autoClose': 7000,
            'icon': BootstrapIcon(icon="x-circle", width=20)
        }


class RtuUIResponseFormatter:
    """Formatter for RTU UI responses following SRP."""

    @staticmethod
    def format_lines_checklist(lines: List[Dict[str, str]]) -> List[dmc.Checkbox]:
        """Format lines data for UI checklist."""
        return [
            dmc.Checkbox(
                label=line['label'],
                value=line['value'],
                styles={
                    "input": {"border-radius": "4px"},
                    "body": {"align-items": "flex-start"},
                    "labelWrapper": {"margin-left": "8px"}
                }
            ) for line in lines
        ]

    @staticmethod
    def format_error_alert(error_message: str, error_type: str = "error") -> dmc.Alert:
        """Format error message as alert component."""
        if error_type == "warning":
            icon_name = "exclamation-triangle"
            color = "yellow"
        else:
            icon_name = "x-circle"
            color = "red"

        return dmc.Alert(
            children=[
                dmc.Group([
                    BootstrapIcon(icon=icon_name, width=16),
                    dmc.Text(error_message, size="sm")
                ], gap="xs")
            ],
            color=color,
            variant="light",
            className="mb-3"
        )

    @staticmethod
    def format_processing_status(is_processing: bool, message: str = "") -> dmc.Text:
        """Format processing status message."""
        if is_processing:
            return dmc.Text("Processing...", c="blue", size="sm")
        elif message:
            return dmc.Text(message, size="sm")
        else:
            return dmc.Text("", size="sm")


# Factory function for creating controller with dependencies
def create_fetch_rtu_data_controller(rtu_service: IFetchRtuDataService = None) -> FetchRtuDataPageController:
    """Create a pre-configured fetch RTU data controller."""
    from services.fetch_rtu_data_service import FetchRtuDataServiceV2
    from validation.rtu_validators import create_composite_rtu_validator
    
    if rtu_service is None:
        rtu_service = FetchRtuDataServiceV2()
    
    composite_validator = create_composite_rtu_validator()
    
    return FetchRtuDataPageController(rtu_service, composite_validator)