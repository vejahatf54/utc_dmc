"""
RTU Resizer Page for DMC Application.
Allows users to select RTU data files (.dt) and resize them by specifying date ranges.
Ported from C# UTC application UcRtuResizer user control.
"""

import dash
from dash import html, dcc, Input, Output, State, callback, no_update, callback_context
import dash_mantine_components as dmc
from datetime import datetime, date, timedelta
import os
from pathlib import Path
from typing import Optional, Tuple

from components.bootstrap_icon import BootstrapIcon
from components.directory_selector import create_directory_selector, create_directory_selector_callback
from logging_config import get_logger

logger = get_logger(__name__)

# Global variable to track current RTU file helper (matching C# pattern)
current_rtu_helper = None
current_file_path = None
current_file_info = {}


def _clear_current_rtu_file():
    """Clear the currently loaded RTU file."""
    global current_rtu_helper, current_file_path, current_file_info
    
    # No need to dispose the new RTU service as it's stateless
    current_rtu_helper = None
    current_file_path = None
    current_file_info = {}
    logger.debug("Cleared current RTU file")


def _load_rtu_file_helper(file_path: str) -> Tuple[datetime, datetime]:
    """
    Load an RTU file and return its first and last timestamps using the new RTU service.
    """
    global current_rtu_helper, current_file_path, current_file_info
    
    try:
        # Clear any previously loaded file
        _clear_current_rtu_file()
        
        # Use the new RTU service to get file info
        from services.rtu_service import RTUService
        rtu_service = RTUService()
        
        # Get file information
        file_info = rtu_service.get_file_info(file_path)
        
        # Store current file path and create dummy helper for compatibility
        current_file_path = file_path
        current_rtu_helper = rtu_service  # Store service for later use
        
        first_ts = file_info['first_timestamp']
        last_ts = file_info['last_timestamp']
        
        if first_ts is None or last_ts is None:
            raise ValueError("No valid timestamps found in the RTU file")
        
        # Store file info
        current_file_info = {
            'file_path': file_path,
            'first_timestamp': first_ts,
            'last_timestamp': last_ts,
            'duration_hours': (last_ts - first_ts).total_seconds() / 3600,
            'total_points': file_info['total_points'],
            'tags_count': file_info['tags_count']
        }
        
        logger.info(f"Loaded RTU file using new service: {file_path}")
        logger.info(f"File contains {file_info['total_points']} points and {file_info['tags_count']} tags")
        return first_ts, last_ts
        
    except Exception as ex:
        logger.error(f"Failed to load RTU file {file_path}: {ex}")
        _clear_current_rtu_file()
        raise


def _get_current_file_info() -> dict:
    """Get information about the currently loaded RTU file."""
    return current_file_info.copy()


def _resize_current_rtu_file(start_date: datetime, end_date: datetime, 
                            map_dictionary: Optional[dict] = None) -> str:
    """
    Resize the currently loaded RTU file using the new RTU service.
    """
    if current_rtu_helper is None or current_file_path is None:
        raise ValueError("No RTU file is currently loaded.")
    
    try:
        # Generate output file name
        input_path = Path(current_file_path)
        base_name = input_path.stem
        output_file = input_path.parent / f"{base_name}_resized.dt"
        
        # Format datetime strings for the service
        start_time_str = start_date.strftime('%y/%m/%d %H:%M:%S')
        end_time_str = end_date.strftime('%y/%m/%d %H:%M:%S')
        
        # Use the new RTU service to resize the file
        points_written = current_rtu_helper.resize_rtu(
            input_file=current_file_path,
            output_file=str(output_file),
            start_time=start_time_str,
            end_time=end_time_str
        )
        
        logger.info(f"Resized RTU file: {points_written} points written to {output_file}")
        return str(output_file)
        
    except Exception as ex:
        logger.error(f"Failed to resize RTU file {current_file_path}: {ex}")
        raise

# Create directory selector component for RTU files
rtu_directory_component, rtu_directory_ids = create_directory_selector(
    component_id='rtu-resizer-files-folder',
    title="RTU Files Folder (.dt files)",
    placeholder="Select folder containing .dt files...",
    browse_button_text="Browse Folder"
)


def create_rtu_resizer_page():
    """Create the RTU Resizer page layout matching UcRtuResizer.Designer.cs design."""

    return dmc.Container([
        # Data stores
        dcc.Store(id='rtu-resizer-store', data={
            'selected_file': '',
            'original_first_timestamp': '',
            'original_last_timestamp': '',
            'file_loaded': False
        }),
        dcc.Store(id='rtu-resizer-status-store', data={'status': 'idle'}),
        dcc.Store(id=rtu_directory_ids['store'], data={'path': ''}),
        
        # Interval for checking background process status
        dcc.Interval(id='rtu-resize-interval', interval=1000, n_intervals=0, disabled=True),

        # Notification container
        html.Div(id='rtu-resizer-notifications'),

        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("RTU Data File Resizer",
                                  order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(
                                icon="question-circle", width=20, color="var(--mantine-primary-color-6)"),
                            id="rtu-resizer-help-modal-btn",
                            variant="light",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Resize RTU data files by extracting data within specified date ranges",
                             c="dimmed", ta="center", size="md")
                ], gap="xs")
            ]),

            # Help Modal
            dmc.Modal(
                title="RTU Data File Resizer Help",
                id="rtu-resizer-help-modal",
                children=[
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(
                                        icon="info-circle", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Requirements", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem(
                                        "RTU data file with .dt extension"),
                                    dmc.ListItem(
                                        "Read permissions to RTU file"),
                                    dmc.ListItem(
                                        "Write permissions to output directory"),
                                    dmc.ListItem(
                                        "Valid date range within file data range")
                                ], size="sm")
                            ])
                        ], span=6),
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="lightbulb", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Process", fw=500)
                                ], gap="xs"),
                                dmc.Stack([
                                    dmc.Text(
                                        "1. Select a folder containing .dt files", size="sm"),
                                    dmc.Text(
                                        "2. Choose specific RTU data file", size="sm"),
                                    dmc.Text(
                                        "3. Adjust start and end dates as needed", size="sm"),
                                    dmc.Text(
                                        "4. Click 'Resize RTU File' to create resized version", size="sm"),
                                    dmc.Space(h="xs"),
                                    dmc.Text("Note: Start and end dates must be different from original file dates",
                                             size="xs", c="dimmed", style={"fontStyle": "italic"})
                                ])
                            ])
                        ], span=6)
                    ])
                ],
                opened=False,
                size="lg"
            ),

            dmc.Divider(variant="dashed"),

            # File Selection Section (Group Box 1 equivalent)
            dmc.Card([
                dmc.CardSection([
                    dmc.Group([
                        BootstrapIcon(icon="folder", width=20,
                                      color="var(--mantine-primary-color-6)"),
                        dmc.Text("File Selection", fw=500, size="lg")
                    ], gap="sm")
                ], withBorder=True, inheritPadding=True, py="xs"),

                dmc.CardSection([
                    dmc.Stack([
                        # Directory selector
                        rtu_directory_component,

                        # File selection dropdown
                        dmc.Group([
                            dmc.Text("Select RTU Data File:",
                                     size="sm", fw=500),
                            dmc.Select(
                                id="rtu-file-select",
                                placeholder="Choose a .dt file...",
                                data=[],
                                disabled=True,
                                w=300,
                                clearable=False,
                                rightSection=BootstrapIcon(
                                    icon="file-earmark-binary", width=16)
                            ),
                            dmc.ActionIcon(
                                BootstrapIcon(icon="check-circle",
                                              width=16, color="var(--mantine-primary-color-6)"),
                                id="rtu-file-loaded-indicator",
                                variant="light",
                                size="sm",
                                style={"visibility": "hidden"}
                            )
                        ], align="center", gap="md"),
                        dmc.Space(h="lg")
                    ], gap="md")
                ], inheritPadding=True)
            ], withBorder=True, shadow="sm", radius="md", mb="lg"),

            # Date Range Section (Group Box 2 equivalent)
            dmc.Card([
                dmc.CardSection([
                    dmc.Group([
                        BootstrapIcon(icon="calendar-range", width=20,
                                      color="var(--mantine-primary-color-6)"),
                        dmc.Text("Date Range", fw=500, size="lg")
                    ], gap="sm")
                ], withBorder=True, inheritPadding=True, py="xs"),

                dmc.CardSection([
                    dmc.Space(h="lg"),
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Text("Pick Start Date", size="md", fw=500),
                                dmc.DateTimePicker(
                                    id="start-datetime-picker",
                                    placeholder="Select start date and time",
                                    w="100%",
                                    disabled=True,
                                    withSeconds=True,
                                    valueFormat="YYYY/MM/DD HH:mm:ss",
                                    size="md"
                                )
                            ], gap="md")
                        ], span=6),

                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Text("Pick End Date", size="md", fw=500),
                                dmc.DateTimePicker(
                                    id="end-datetime-picker",
                                    placeholder="Select end date and time",
                                    w="100%",
                                    disabled=True,
                                    withSeconds=True,
                                    valueFormat="YYYY/MM/DD HH:mm:ss",
                                    size="md"
                                )
                            ], gap="md")
                        ], span=6)
                    ], gutter="lg"),

                    dmc.Space(h="lg")

                ], inheritPadding=True)
            ], withBorder=True, shadow="sm", radius="md", mb="lg"),

            # Action Section
            dmc.Center([
                dmc.Button(
                    [
                        BootstrapIcon(icon="arrow-clockwise", width=16),
                        dmc.Space(w="sm"),
                        "Resize RTU File"
                    ],
                    id="resize-rtu-btn",
                    size="lg",
                    disabled=True,
                    loading=False
                )
            ])
        ], gap="lg")
    ], size="xl", px="xl")


# Callback to populate file dropdown when directory is selected
@callback(
    [Output('rtu-file-select', 'data'),
     Output('rtu-file-select', 'disabled'),
     Output('rtu-file-select', 'value'),
     Output('rtu-resizer-notifications', 'children', allow_duplicate=True)],
    [Input(rtu_directory_ids['store'], 'data')],
    prevent_initial_call=True
)
def update_rtu_file_list(directory_data):
    """Update the RTU file dropdown when directory is selected."""
    try:
        if not directory_data or not directory_data.get('path'):
            return [], True, None, no_update

        directory_path = directory_data['path']

        if not os.path.exists(directory_path):
            return [], True, None, dmc.Notification(
                title="Directory Error",
                message="Selected directory does not exist",
                color="red",
                action="show"
            )

        # Find .dt files in the directory
        dt_files = []
        try:
            path_obj = Path(directory_path)
            dt_files = [f.name for f in path_obj.glob("*.dt") if f.is_file()]
        except Exception as ex:
            logger.error(f"Error scanning directory {directory_path}: {ex}")

        if not dt_files:
            return [], True, None, dmc.Notification(
                title="No RTU Files Found",
                message="No .dt files found in the selected directory",
                color="yellow",
                action="show"
            )

        # Sort files by name
        dt_files.sort()

        # Create dropdown options
        file_options = [{"value": file, "label": file} for file in dt_files]

        logger.info(f"Found {len(dt_files)} RTU file(s) in {directory_path}")

        # Show appropriate notification based on number of files
        if len(dt_files) == 1:
            notification = dmc.Notification(
                title="RTU File Found",
                message=f"Ready to process: {dt_files[0]}",
                color="green",
                action="show"
            )
        else:
            notification = dmc.Notification(
                title="Multiple RTU Files Found",
                message=f"Found {len(dt_files)} .dt files. First file '{dt_files[0]}' selected by default.",
                color="blue",
                action="show"
            )

        # Auto-select the first file
        auto_selected_file = dt_files[0]
        logger.debug(f"Auto-selecting first RTU file: {auto_selected_file}")

        return file_options, False, auto_selected_file, notification

    except Exception as ex:
        logger.error(f"Error updating RTU file list: {ex}")
        return [], True, None, dmc.Notification(
            title="Error",
            message=f"Failed to scan directory: {str(ex)}",
            color="red",
            action="show"
        )


# Callback to automatically select file when only one is found (matching C# behavior)
# Auto-selection is now handled in the directory callback above


# Callback to load selected RTU file and populate date pickers
@callback(
    [Output('rtu-resizer-store', 'data'),
     Output('start-datetime-picker', 'value'),
     Output('end-datetime-picker', 'value'),
     Output('start-datetime-picker', 'disabled'),
     Output('end-datetime-picker', 'disabled'),
     Output('rtu-file-loaded-indicator', 'style'),
     Output('resize-rtu-btn', 'disabled'),
     Output('rtu-resizer-notifications', 'children', allow_duplicate=True)],
    [Input('rtu-file-select', 'value')],
    [State(rtu_directory_ids['store'], 'data'),
     State('rtu-resizer-store', 'data')],
    prevent_initial_call='initial_duplicate'  # This allows duplicate outputs with initial call
)
def load_rtu_file(selected_file, directory_data, current_store):
    """Load the selected RTU file and populate date pickers with file timestamps."""
    try:
        if not selected_file:
            # Reset state when no file is selected
            logger.debug("Resetting state - no file selected")
            return (
                {'selected_file': '', 'original_first_timestamp': '',
                    'original_last_timestamp': '', 'file_loaded': False},
                None, None, True, True, {
                    "visibility": "hidden"}, True, no_update
            )
            
        if not directory_data or not directory_data.get('path'):
            # Directory not available - this shouldn't happen if file dropdown is populated
            logger.warning("Directory data not available but file is selected")
            return (
                {'selected_file': '', 'original_first_timestamp': '',
                    'original_last_timestamp': '', 'file_loaded': False},
                None, None, True, True, {
                    "visibility": "hidden"}, True, no_update
            )

        file_path = os.path.join(directory_data['path'], selected_file)
        logger.debug(f"Constructed file path: {file_path}")

        # Validate file exists and has proper extension (matching C# filter validation)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"RTU file not found: {file_path}")

        if not file_path.lower().endswith('.dt'):
            raise ValueError(
                f"Invalid file type. Expected .dt file, got: {selected_file}")

        logger.info(f"Loading RTU file: {file_path}")
        
        # Clear any previously loaded file first
        _clear_current_rtu_file()

        # Load the RTU file (equivalent to C# rtuHelper creation and timestamp fetching)
        first_timestamp, last_timestamp = _load_rtu_file_helper(file_path)

        # Update store data
        new_store = {
            'selected_file': file_path,
            'original_first_timestamp': first_timestamp.isoformat(),
            'original_last_timestamp': last_timestamp.isoformat(),
            'file_loaded': True
        }

        # Get file info for display
        file_info = _get_current_file_info()

        logger.info(
            f"RTU file loaded successfully. Range: {first_timestamp} to {last_timestamp}")

        return (
            new_store,
            first_timestamp.isoformat(),
            last_timestamp.isoformat(),
            False,  # Enable start picker
            False,  # Enable end picker
            {"visibility": "visible"},  # Show loaded indicator
            False,  # Enable resize button
            dmc.Notification(
                title="RTU File Loaded",
                message=f"File loaded successfully with {file_info['record_count']:,} records" if isinstance(
                    file_info['record_count'], int) else f"File loaded successfully with {file_info['record_count']} records",
                color="green",
                action="show"
            )
        )

    except PermissionError as ex:
        # Handle security/permission errors (equivalent to C# SecurityException)
        logger.error(
            f"Permission error loading RTU file {selected_file}: {ex}")
        _clear_current_rtu_file()

        return (
            {'selected_file': '', 'original_first_timestamp': '',
                'original_last_timestamp': '', 'file_loaded': False},
            None, None, True, True, {"visibility": "hidden"}, True,
            dmc.Notification(
                title="Security Error",
                message="Security error. Please contact your administrator for details.",
                color="red",
                action="show"
            )
        )
    except (FileNotFoundError, ValueError) as ex:
        # Handle file validation errors
        logger.error(f"File validation error for {selected_file}: {ex}")
        _clear_current_rtu_file()

        return (
            {'selected_file': '', 'original_first_timestamp': '',
                'original_last_timestamp': '', 'file_loaded': False},
            None, None, True, True, {"visibility": "hidden"}, True,
            dmc.Notification(
                title="File Error",
                message=str(ex),
                color="red",
                action="show"
            )
        )
    except Exception as ex:
        # Handle any other errors
        logger.error(
            f"Unexpected error loading RTU file {selected_file}: {ex}")
        _clear_current_rtu_file()

        return (
            {'selected_file': '', 'original_first_timestamp': '',
                'original_last_timestamp': '', 'file_loaded': False},
            None, None, True, True, {"visibility": "hidden"}, True,
            dmc.Notification(
                title="Error Loading File",
                message=f"Failed to load RTU file: {str(ex)}",
                color="red",
                action="show"
            )
        )


# Callback to update end date minimum when start date changes
@callback(
    Output('end-datetime-picker', 'minDate'),
    [Input('start-datetime-picker', 'value')],
    prevent_initial_call=True
)
def update_end_date_minimum(start_date):
    """Update minimum end date to be 15 minutes after start date (matching C# logic)."""
    if not start_date:
        return no_update

    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        min_end_dt = start_dt + timedelta(minutes=15)
        return min_end_dt.isoformat()
    except:
        return no_update


# Callback to handle RTU file resizing
@callback(
    [Output('resize-rtu-btn', 'loading'),
     Output('rtu-resizer-status-store', 'data'),
     Output('rtu-resize-interval', 'disabled'),
     Output('rtu-resizer-notifications', 'children', allow_duplicate=True)],
    [Input('resize-rtu-btn', 'n_clicks')],
    [State('start-datetime-picker', 'value'),
     State('end-datetime-picker', 'value'),
     State('rtu-resizer-store', 'data')],
    prevent_initial_call=True
)
def start_resize_rtu_file(n_clicks, start_date, end_date, store_data):
    """Start RTU file resizing operation."""
    if not n_clicks or not store_data.get('file_loaded'):
        return no_update, no_update, no_update, no_update

    try:
        if not start_date or not end_date:
            return False, {'status': 'error'}, True, dmc.Notification(
                title="Invalid Date Range",
                message="Please select both start and end dates",
                color="red",
                action="show"
            )

        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Validate date range
        if start_dt >= end_dt:
            return False, {'status': 'error'}, True, dmc.Notification(
                title="Invalid Date Range",
                message="Start date must be before end date",
                color="red",
                action="show"
            )

        # Check if dates are same as original (matching C# validation)
        original_first = datetime.fromisoformat(
            store_data['original_first_timestamp'])
        original_last = datetime.fromisoformat(
            store_data['original_last_timestamp'])

        if start_dt == original_first and end_dt == original_last:
            return False, {'status': 'error'}, True, dmc.Notification(
                title="Invalid Date Range",
                message="Start and End dates are the same as existing RTU file dates. Please modify one of them and try again!",
                color="red",
                action="show"
            )

        logger.info(f"Starting RTU file resize from {start_dt} to {end_dt}")

        # Start the background process - set status to processing
        return True, {
            'status': 'processing',
            'start_date': start_dt.isoformat(),
            'end_date': end_dt.isoformat(),
            'start_time': datetime.now().isoformat()
        }, False, dmc.Notification(
            title="Processing Started",
            message="RTU file resize operation started...",
            color="blue",
            action="show"
        )

    except Exception as ex:
        logger.error(f"Error starting RTU file resize: {ex}")
        return False, {'status': 'error'}, True, dmc.Notification(
            title="Start Failed",
            message=f"Failed to start resize operation: {str(ex)}",
            color="red",
            action="show"
        )


@callback(
    [Output('resize-rtu-btn', 'loading', allow_duplicate=True),
     Output('rtu-resizer-status-store', 'data', allow_duplicate=True),
     Output('rtu-resize-interval', 'disabled', allow_duplicate=True),
     Output('rtu-resizer-notifications', 'children', allow_duplicate=True)],
    [Input('rtu-resize-interval', 'n_intervals')],
    [State('rtu-resizer-status-store', 'data')],
    prevent_initial_call=True
)
def process_resize_rtu_file(n_intervals, status_data):
    """Process RTU file resizing operation in background."""
    if not status_data or status_data.get('status') != 'processing':
        return no_update, no_update, no_update, no_update

    try:
        # Parse dates from status data
        start_dt = datetime.fromisoformat(status_data['start_date'])
        end_dt = datetime.fromisoformat(status_data['end_date'])

        logger.info(f"Processing RTU file resize from {start_dt} to {end_dt}")

        # Perform the resize operation (matching C# rtuHelper.ProcessFile call)
        output_path = _resize_current_rtu_file(start_dt, end_dt)

        logger.info(f"RTU file resized successfully: {output_path}")

        return False, {
            'status': 'completed', 
            'output_path': output_path,
            'completion_time': datetime.now().isoformat()
        }, True, dmc.Notification(
            title="RTU File Resized Successfully",
            message=f"Resized file created: {os.path.basename(output_path)}",
            color="green",
            action="show"
        )

    except Exception as ex:
        logger.error(f"Error processing RTU file resize: {ex}")
        return False, {
            'status': 'error',
            'error_message': str(ex),
            'error_time': datetime.now().isoformat()
        }, True, dmc.Notification(
            title="Resize Failed",
            message=f"Failed to resize RTU file: {str(ex)}",
            color="red",
            action="show"
        )


# Help modal callback
@callback(
    Output("rtu-resizer-help-modal", "opened"),
    [Input("rtu-resizer-help-modal-btn", "n_clicks")],
    [State("rtu-resizer-help-modal", "opened")],
    prevent_initial_call=True
)
def toggle_help_modal(n_clicks, opened):
    """Toggle help modal visibility."""
    return not opened


# Register directory selector callback
try:
    create_directory_selector_callback(rtu_directory_ids)
    logger.debug(
        "RTU resizer directory selector callback registered successfully")
except Exception as ex:
    logger.warning(
        f"Directory selector callback registration failed (may already exist): {ex}")
