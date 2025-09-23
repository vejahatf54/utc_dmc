"""
RTU Resizer Page for DMC Application (v2 - Controller Integration).
Allows users to select RTU data files (.dt) and resize them by specifying date ranges.
Uses SOLID principles with dependency injection and controller pattern.
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
from core.dependency_injection import configure_services
from controllers.rtu_resizer_controller import RtuResizerPageController

logger = get_logger(__name__)

# Initialize dependency injection container
container = configure_services()

# Initialize controller with dependency injection
_resizer_controller = container.resolve(RtuResizerPageController)

# Global variable to track current RTU file helper (matching C# pattern)
current_rtu_helper = None
current_file_path = None
current_file_info = {}

# Global variable to store background resize result
_resize_result = None


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
    Load an RTU file and return its first and last timestamps using the optimized controller.
    """
    global current_rtu_helper, current_file_path, current_file_info

    try:
        # Clear any previously loaded file
        _clear_current_rtu_file()

        # Use the controller for optimized file loading
        result = _resizer_controller.handle_file_selection(file_path)

        if not result.success:
            raise ValueError(f"Failed to load RTU file: {result.error}")

        file_info = result.data['file_info']

        # Store current file path for compatibility
        current_file_path = file_path
        current_rtu_helper = _resizer_controller  # Store controller for later use

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

        logger.info(f"Loaded RTU file using optimized controller: {file_path}")
        logger.info(
            f"File contains {file_info['total_points']} points and {file_info['tags_count']} tags")
        return first_ts, last_ts

    except Exception as ex:
        logger.error(f"Failed to load RTU file {file_path}: {ex}")
        _clear_current_rtu_file()
        raise


def _get_current_file_info() -> dict:
    """Get information about the currently loaded RTU file."""
    return current_file_info.copy()


def _resize_current_rtu_file(start_date: datetime, end_date: datetime,
                             tag_mapping_content: Optional[str] = None) -> str:
    """
    Resize the currently loaded RTU file using the new RTU service.
    Optionally applies tag remapping if tag_mapping_content is provided.
    """
    if current_rtu_helper is None or current_file_path is None:
        raise ValueError("No RTU file is currently loaded.")

    try:
        # Generate output file name
        input_path = Path(current_file_path)
        base_name = input_path.stem

        # Add suffix based on whether retag is enabled
        if tag_mapping_content:
            output_file = input_path.parent / \
                f"{base_name}_resized_retagged.dt"
        else:
            output_file = input_path.parent / f"{base_name}_resized.dt"

        # Format datetime strings for the service
        start_time_str = start_date.strftime('%y/%m/%d %H:%M:%S')
        end_time_str = end_date.strftime('%y/%m/%d %H:%M:%S')

        # Create temporary tag mapping file if needed
        tag_mapping_file = None
        if tag_mapping_content:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(tag_mapping_content)
                tag_mapping_file = f.name
            logger.info(
                f"Created temporary tag mapping file: {tag_mapping_file}")

        try:
            # Use the optimized controller to resize the file
            resize_result = _resizer_controller.handle_resize_request(
                input_file_path=current_file_path,
                output_file_path=str(output_file),
                start_time=start_time_str,
                end_time=end_time_str,
                tag_mapping_file=tag_mapping_file
            )

            if not resize_result.success:
                raise RuntimeError(f"Resize failed: {resize_result.error}")

            result_data = resize_result.data
            points_written = result_data.get('output_points', 0)

            if tag_mapping_content:
                logger.info(
                    f"Resized and retagged RTU file: {points_written} points written to {output_file}")
            else:
                logger.info(
                    f"Resized RTU file: {points_written} points written to {output_file}")

            return str(output_file)

        finally:
            # Clean up temporary tag mapping file
            if tag_mapping_file and os.path.exists(tag_mapping_file):
                try:
                    os.unlink(tag_mapping_file)
                    logger.debug(
                        f"Cleaned up temporary tag mapping file: {tag_mapping_file}")
                except Exception as cleanup_ex:
                    logger.warning(
                        f"Failed to clean up temporary file {tag_mapping_file}: {cleanup_ex}")

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
        dcc.Store(id=rtu_directory_ids['store'], data={'path': ''}),
        dcc.Store(id='rtu-resizer-processing-store', data={'status': 'idle'}),
        dcc.Store(id='tag-mapping-file-store',
                  data={'filename': '', 'content': '', 'uploaded': False}),

        # Interval for processing status updates
        dcc.Interval(id='rtu-resizer-processing-interval',
                     interval=1000, disabled=True),

        # Notification container
        html.Div(id='rtu-resizer-notifications'),

        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("RTU Retagger | Resizer",
                                  order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(
                                icon="question-circle", width=20, color="var(--mantine-primary-color-6)"),
                            id="rtu-resizer-help-modal-btn",
                            variant="light",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Resize RTU data files and optionally retag them using mapping files",
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

            # Two-column layout similar to RTU to CSV page
            dmc.Grid([
                # Left Column - File Selection and Date Range
                dmc.GridCol([
                    dmc.Stack([
                        # File Selection Section
                        dmc.Card([
                            dmc.CardSection([
                                dmc.Group([
                                    BootstrapIcon(icon="folder", width=20,
                                                  color="var(--mantine-primary-color-6)"),
                                    dmc.Text("File Selection",
                                             fw=500, size="lg")
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
                        ], withBorder=True, shadow="sm", radius="md", mb="lg")
                    ], gap="lg")
                ], span=6),

                # Right Column - Operation Options and Action Button
                dmc.GridCol([
                    dmc.Stack([
                        # Operation Selection Section
                        dmc.Card([
                            dmc.CardSection([
                                dmc.Group([
                                    BootstrapIcon(icon="gear", width=20,
                                                  color="var(--mantine-primary-color-6)"),
                                    dmc.Text("Operation Options",
                                             fw=500, size="lg")
                                ], gap="sm")
                            ], withBorder=True, inheritPadding=True, py="xs"),

                            dmc.CardSection([
                                dmc.Stack([
                                    # Add more spacing above radio buttons
                                    dmc.Space(h="lg"),

                                    # Proper RadioGroup for mutually exclusive selection
                                    dmc.RadioGroup(
                                        children=[
                                            dmc.Group([
                                                dmc.Radio(
                                                    label="Resize Only",
                                                    value="resize_only",
                                                    size="sm"
                                                ),
                                                dmc.Radio(
                                                    label="Resize & Retag",
                                                    value="resize_retag",
                                                    size="sm"
                                                )
                                            ], gap="xl")  # Increased gap between radio buttons
                                        ],
                                        id="operation-radio-group",
                                        value="resize_only",
                                        mb="lg"  # Add margin bottom for spacing
                                    ),

                                    # Tag mapping file upload (initially hidden)
                                    html.Div([
                                        dmc.Divider(label="Tag Mapping File",
                                                    labelPosition="center", my="lg"),
                                        dmc.Text("Upload a CSV file with tag mappings (old_tag,new_tag format):",
                                                 size="sm", c="dimmed", mb="sm"),
                                        dcc.Upload(
                                            id='tag-mapping-upload',
                                            children=html.Div([
                                                dmc.Paper([
                                                    dmc.Center([
                                                        dmc.Stack([
                                                            BootstrapIcon(
                                                                icon="cloud-upload", width=48, color="var(--mantine-primary-color-6)"),
                                                            dmc.Text("Drag and drop or click to select tag mapping file",
                                                                     ta="center", c="dimmed", size="sm"),
                                                            dmc.Text("Accepted format: CSV (old_tag,new_tag)",
                                                                     ta="center", c="dimmed", size="xs")
                                                        ], align="center", gap="sm")
                                                    ])
                                                ], p="xl", withBorder=True, radius="md",
                                                    style={'borderStyle': 'dashed', 'borderColor': 'var(--mantine-primary-color-4)'})
                                            ]),
                                            style={
                                                'width': '100%',
                                                'borderRadius': '8px'
                                            },
                                            multiple=False
                                        ),
                                        # Upload status
                                        html.Div(id='tag-mapping-upload-status',
                                                 style={'marginTop': '10px'})
                                    ], id="tag-mapping-upload-container", style={"display": "none"})
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

                                # Loading indicator for datetime pickers
                                html.Div([
                                    dmc.Center([
                                        dmc.Stack([
                                            dmc.Loader(
                                                size="lg", color="blue"),
                                            dmc.Text("Loading file timestamps...",
                                                     size="sm", c="dimmed")
                                        ], gap="sm", align="center")
                                    ])
                                ], id="date-range-loader", style={"display": "none", "padding": "2rem"}),

                                # Datetime pickers container
                                html.Div([
                                    dmc.Grid([
                                        dmc.GridCol([
                                            dmc.Stack([
                                                dmc.Text("Pick Start Date",
                                                         size="md", fw=500),
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
                                                dmc.Text("Pick End Date",
                                                         size="md", fw=500),
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
                                    ], gutter="lg")
                                ], id="date-pickers-container"),

                                dmc.Space(h="lg")

                            ], inheritPadding=True)
                        ], withBorder=True, shadow="sm", radius="md", mb="lg"),

                        # Action Section
                        dmc.Center([
                            dmc.Stack([
                                dmc.Button(
                                    [
                                        BootstrapIcon(
                                            icon="arrow-clockwise", width=16),
                                        dmc.Space(w="sm"),
                                        html.Span("Resize RTU File",
                                                  id="resize-btn-text")
                                    ],
                                    id="resize-rtu-btn",
                                    size="lg",
                                    disabled=True,
                                    loading=False
                                ),

                                # Processing alert underneath button (similar to CSV to RTU page)
                                html.Div(
                                    id="resize-processing-alert",
                                    style={"minHeight": "20px",
                                           "marginTop": "1rem"}
                                )
                            ], gap="md", align="center")
                        ])
                    ], gap="lg")
                ], span=6)
            ], gutter="xl")
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


# Callback to load selected RTU file and populate date pickers (direct, no interval)
@callback(
    [Output('rtu-resizer-store', 'data'),
     Output('start-datetime-picker', 'value'),
     Output('end-datetime-picker', 'value'),
     Output('start-datetime-picker', 'disabled'),
     Output('end-datetime-picker', 'disabled'),
     Output('rtu-file-loaded-indicator', 'style'),
     Output('resize-rtu-btn', 'disabled'),
     Output('date-range-loader', 'style'),
     Output('date-pickers-container', 'style'),
     Output('rtu-resizer-notifications', 'children', allow_duplicate=True)],
    [Input('rtu-file-select', 'value')],
    [State(rtu_directory_ids['store'], 'data'),
     State('rtu-resizer-store', 'data')],
    # This allows duplicate outputs with initial call
    prevent_initial_call='initial_duplicate'
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
                    "visibility": "hidden"}, True, {"display": "none"}, {"display": "block"}, no_update
            )

        if not directory_data or not directory_data.get('path'):
            # Directory not available - this shouldn't happen if file dropdown is populated
            logger.warning("Directory data not available but file is selected")
            return (
                {'selected_file': '', 'original_first_timestamp': '',
                    'original_last_timestamp': '', 'file_loaded': False},
                None, None, True, True, {
                    "visibility": "hidden"}, True, {"display": "none"}, {"display": "block"}, no_update
            )

        file_path = os.path.join(directory_data['path'], selected_file)
        logger.debug(f"Constructed file path: {file_path}")

        # Validate file exists and has proper extension (matching C# filter validation)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"RTU file not found: {file_path}")

        if not file_path.lower().endswith('.dt'):
            raise ValueError(
                f"Invalid file type. Expected .dt file, got: {selected_file}")

        # Show loading for date range extraction
        logger.info(f"Loading RTU file: {file_path}")

        # Clear any previously loaded file first
        _clear_current_rtu_file()

        # Load the RTU file using new RTU service
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
            {"display": "none"},  # Hide loading indicator
            {"display": "block"},  # Show datetime pickers
            dmc.Notification(
                title="RTU File Loaded",
                message=f"File loaded successfully with {file_info['total_points']:,} points and {file_info['tags_count']} tags",
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
            None, None, True, True, {"visibility": "hidden"}, True, {
                "display": "none"}, {"display": "block"},
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
            None, None, True, True, {"visibility": "hidden"}, True, {
                "display": "none"}, {"display": "block"},
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
            None, None, True, True, {"visibility": "hidden"}, True, {
                "display": "none"}, {"display": "block"},
            dmc.Notification(
                title="Error Loading File",
                message=f"Failed to load RTU file: {str(ex)}",
                color="red",
                action="show"
            )
        )


# Clientside callback to immediately show loading when file selection changes
@callback(
    [Output('date-range-loader', 'style', allow_duplicate=True),
     Output('date-pickers-container', 'style', allow_duplicate=True),
     Output('resize-rtu-btn', 'disabled', allow_duplicate=True),
     Output('rtu-file-loaded-indicator', 'style', allow_duplicate=True)],
    [Input('rtu-file-select', 'value')],
    prevent_initial_call=True
)
def show_file_loading_immediately(selected_file):
    """Immediately show loading state when file selection changes."""
    if selected_file:
        # Show loading, hide datetime pickers
        return ({"display": "block"}, {"display": "none"}, True, {"visibility": "hidden"})
    else:
        # Hide loading, show datetime pickers (but keep them disabled)
        return ({"display": "none"}, {"display": "block"}, True, {"visibility": "hidden"})


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


# Callback to handle RTU file resizing with processing alert
@callback(
    [Output('resize-rtu-btn', 'disabled', allow_duplicate=True),
     Output('resize-processing-alert', 'children', allow_duplicate=True),
     Output('rtu-resizer-processing-interval',
            'disabled', allow_duplicate=True),
     Output('rtu-resizer-notifications', 'children', allow_duplicate=True)],
    [Input('resize-rtu-btn', 'n_clicks')],
    [State('start-datetime-picker', 'value'),
     State('end-datetime-picker', 'value'),
     State('rtu-resizer-store', 'data'),
     State('operation-radio-group', 'value'),
     State('tag-mapping-file-store', 'data')],
    prevent_initial_call=True
)
def resize_rtu_file_direct(n_clicks, start_date, end_date, store_data, operation, tag_mapping_data):
    """Process RTU file resizing operation with processing alert."""
    global _resize_result

    if not n_clicks or not store_data.get('file_loaded'):
        return no_update, no_update, no_update, no_update

    try:
        if not start_date or not end_date:
            return False, "", True, dmc.Notification(
                title="Invalid Date Range",
                message="Please select both start and end dates",
                color="red",
                action="show"
            )

        # Check if retag operation is selected and validate tag mapping file
        is_retag_operation = operation == "resize_retag"
        tag_mapping_content = None

        if is_retag_operation:
            if not tag_mapping_data.get('uploaded') or not tag_mapping_data.get('content'):
                return False, "", True, dmc.Notification(
                    title="Tag Mapping Required",
                    message="Please upload a tag mapping CSV file for resize & retag operation",
                    color="red",
                    action="show"
                )
            tag_mapping_content = tag_mapping_data['content']

        # Show processing alert immediately (similar to CSV to RTU page)
        operation_text = "RTU file resizing and retagging" if is_retag_operation else "RTU file resizing"
        processing_alert = dmc.Alert([
            dmc.Group([
                BootstrapIcon(icon="clock", width=16),
                dmc.Text(f"{operation_text} started. Processing...", size="sm")
            ], gap="xs"),
            dmc.Space(h="xs"),
            dmc.Progress(value=100, animated=True, color="blue", size="sm")
        ], color="blue", variant="light")

        # Show processing notification immediately
        processing_notification = dmc.Notification(
            title="Processing Started",
            message=f"{operation_text} started. Processing...",
            color="blue",
            autoClose=False,
            action="show"
        )

        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Validate date range
        if start_dt >= end_dt:
            return False, "", True, dmc.Notification(
                title="Invalid Date Range",
                message="Start date must be before end date",
                color="red",
                action="show"
            )

        # Check if dates are same as original - only for resize-only operations
        # For retag operations, allow same date range since user might want to retag entire file
        original_first = datetime.fromisoformat(
            store_data['original_first_timestamp'])
        original_last = datetime.fromisoformat(
            store_data['original_last_timestamp'])

        if start_dt == original_first and end_dt == original_last and not is_retag_operation:
            return False, "", True, dmc.Notification(
                title="Invalid Date Range",
                message="Start and End dates are the same as existing RTU file dates. Please modify one of them and try again!",
                color="red",
                action="show"
            )

        logger.info(f"Starting RTU file resize from {start_dt} to {end_dt}")

        # Store processing parameters for background processing
        processing_params = {
            'status': 'processing',
            'start_dt': start_dt.isoformat(),
            'end_dt': end_dt.isoformat(),
            'start_time': datetime.now().isoformat()
        }

        # Update the processing store with new parameters
        import threading

        def background_resize():
            global _resize_result
            try:
                output_path = _resize_current_rtu_file(
                    start_dt, end_dt, tag_mapping_content)
                operation_action = "resized and retagged" if is_retag_operation else "resized"
                logger.info(
                    f"RTU file {operation_action} successfully: {output_path}")
                # Store result for the interval callback to pick up
                _resize_result = {
                    'status': 'completed',
                    'output_path': output_path,
                    'is_retag_operation': is_retag_operation
                }
            except Exception as ex:
                logger.error(f"Error during background resize: {ex}")
                _resize_result = {'status': 'error', 'error': str(ex)}

        # Clear any previous result
        _resize_result = None

        # Start background processing
        thread = threading.Thread(target=background_resize)
        thread.start()

        # Return processing alert immediately so user can see it
        # Enable button disabled, show processing alert, enable interval, show notification
        return True, processing_alert, False, processing_notification

    except Exception as ex:
        logger.error(f"Error resizing RTU file: {ex}")
        return False, "", True, dmc.Notification(
            title="Resize Failed",
            message=f"Failed to resize RTU file: {str(ex)}",
            color="red",
            action="show"
        )


# Callback to monitor background processing and update UI when complete
@callback(
    [Output('resize-rtu-btn', 'disabled', allow_duplicate=True),
     Output('resize-processing-alert', 'children', allow_duplicate=True),
     Output('rtu-resizer-processing-interval',
            'disabled', allow_duplicate=True),
     Output('rtu-resizer-notifications', 'children', allow_duplicate=True)],
    [Input('rtu-resizer-processing-interval', 'n_intervals')],
    prevent_initial_call=True
)
def monitor_background_resize(n_intervals):
    """Monitor background resize processing and update UI when complete."""
    global _resize_result

    if _resize_result is None:
        return no_update, no_update, no_update, no_update

    result = _resize_result
    _resize_result = None  # Clear the result

    if result['status'] == 'completed':
        is_retag = result.get('is_retag_operation', False)
        title = "RTU File Resized & Retagged Successfully" if is_retag else "RTU File Resized Successfully"
        action_text = "Resized and retagged" if is_retag else "Resized"

        success_notification = dmc.Notification(
            title=title,
            message=f"{action_text} file created: {os.path.basename(result['output_path'])}",
            color="green",
            action="show"
        )
        # Re-enable button, clear alert, disable interval, show success
        return False, "", True, success_notification

    elif result['status'] == 'error':
        error_notification = dmc.Notification(
            title="Resize Failed",
            message=f"Failed to resize RTU file: {result['error']}",
            color="red",
            action="show"
        )
        # Re-enable button, clear alert, disable interval, show error
        return False, "", True, error_notification

    return no_update, no_update, no_update, no_update


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


# Operation selection callback - show/hide tag mapping upload based on selection
@callback(
    Output("tag-mapping-upload-container", "style"),
    Input("operation-radio-group", "value")
)
def handle_operation_selection(operation_value):
    """Handle operation selection and show/hide tag mapping upload."""
    if operation_value == "resize_retag":
        return {"display": "block"}
    else:
        return {"display": "none"}


# Update button text based on operation
@callback(
    Output("resize-btn-text", "children"),
    Input("operation-radio-group", "value")
)
def update_button_text(operation):
    """Update button text based on selected operation."""
    if operation == "resize_retag":
        return "Resize & Retag RTU File"
    return "Resize RTU File"


# Tag mapping file upload callback
@callback(
    [Output('tag-mapping-file-store', 'data'),
     Output('tag-mapping-upload-status', 'children')],
    [Input('tag-mapping-upload', 'contents')],
    [State('tag-mapping-upload', 'filename')],
    prevent_initial_call=True
)
def handle_tag_mapping_upload(contents, filename):
    """Handle tag mapping file upload."""
    if contents is None:
        return {'filename': '', 'content': '', 'uploaded': False}, ""

    try:
        import base64
        import io

        # Decode the file content
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        # Validate file type
        if not filename.lower().endswith('.csv'):
            error_alert = dmc.Alert(
                children="Please upload a CSV file (.csv extension required)",
                title="Invalid File Type",
                color="red",
                withCloseButton=True
            )
            return {'filename': '', 'content': '', 'uploaded': False}, error_alert

        # Read and validate CSV content
        try:
            csv_content = decoded.decode('utf-8')
            lines = csv_content.strip().split('\n')

            if len(lines) < 1:
                raise ValueError("File appears to be empty")

            # Basic validation - check if it looks like CSV with at least 2 columns
            import csv as csv_module
            csv_reader = csv_module.reader(io.StringIO(csv_content))
            first_row = next(csv_reader, None)

            if not first_row or len(first_row) < 2:
                raise ValueError(
                    "CSV must have at least 2 columns (old_tag,new_tag)")

            success_alert = dmc.Alert(
                children=f"Successfully uploaded: {filename} ({len(lines)} rows)",
                title="Upload Successful",
                color="green",
                withCloseButton=True
            )

            return {
                'filename': filename,
                'content': csv_content,
                'uploaded': True
            }, success_alert

        except Exception as e:
            error_alert = dmc.Alert(
                children=f"Error reading CSV file: {str(e)}",
                title="File Format Error",
                color="red",
                withCloseButton=True
            )
            return {'filename': '', 'content': '', 'uploaded': False}, error_alert

    except Exception as e:
        error_alert = dmc.Alert(
            children=f"Error processing uploaded file: {str(e)}",
            title="Upload Error",
            color="red",
            withCloseButton=True
        )
        return {'filename': '', 'content': '', 'uploaded': False}, error_alert
