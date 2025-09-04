"""
Fetch Archive Page for DMC Application.
Allows users to select dates, pipeline lines, and output directories to fetch historical data.
"""

import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import dash_mantine_components as dmc
from datetime import datetime, date
import logging

from components.bootstrap_icon import BootstrapIcon
from components.directory_selector import create_directory_selector, create_directory_selector_callback
from services.fetch_archive_service import FetchArchiveService
from services.config_manager import get_config_manager

logger = logging.getLogger(__name__)

# Initialize services
fetch_archive_service = FetchArchiveService()

# Create directory selector component
directory_component, directory_ids = create_directory_selector(
    component_id='fetch-archive-output',
    title="Output Directory for Archive Files",
    placeholder="Select directory for extracted archive files...",
    browse_button_text="Browse",
    reset_button_text="Reset"
)

# Layout
layout = dmc.Container([
    # Data stores
    dcc.Store(id='available-lines-store-fetch', data=[]),
    dcc.Store(id='fetch-status-store', data={'status': 'idle'}),
    dcc.Store(id=directory_ids['store'], data={'path': ''}),

    # Header Section
    dmc.Stack([
        dmc.Center([
            dmc.Stack([
                dmc.Group([
                    dmc.Title("Fetch Archive Data", order=2, ta="center"),
                    dmc.ActionIcon(
                        BootstrapIcon(icon="question-circle", width=20,
                                      color="var(--mantine-color-blue-6)"),
                        id="help-modal-btn-fetch",
                        variant="light",
                        color="blue",
                        size="lg"
                    )
                ], justify="center", align="center", gap="md"),
                dmc.Text("Download and extract historical pipeline data from archive repositories",
                         c="dimmed", ta="center", size="md")
            ], gap="xs")
        ]),

        # Help Modal
        dmc.Modal(
            title="How Fetch Archive Works",
            id="help-modal-fetch",
            children=[
                dmc.Grid([
                    dmc.GridCol([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="info-circle", width=20),
                                dmc.Text("Archive Structure", fw=500)
                            ], gap="xs"),
                            dmc.List([
                                dmc.ListItem(
                                    f"UNC Path: {get_config_manager().get_archive_base_path()}"),
                                dmc.ListItem(
                                    "Date folders in YYYYMMDD format (e.g., 20231226)"),
                                dmc.ListItem(
                                    "ZIP files containing historical data"),
                                dmc.ListItem(
                                    "Files extracted to organized output directories")
                            ], size="sm")
                        ])
                    ], span=6),
                    dmc.GridCol([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="lightbulb", width=20),
                                dmc.Text("Process", fw=500)
                            ], gap="xs"),
                            dmc.List([
                                dmc.ListItem(
                                    "Select archive date using calendar"),
                                dmc.ListItem(
                                    "Choose pipeline lines to process"),
                                dmc.ListItem("Select output directory"),
                                dmc.ListItem(
                                    "Click 'Fetch Archive Data' to extract files")
                            ], size="sm")
                        ])
                    ], span=6)
                ])
            ],
            opened=False,
            size="lg"
        ),

        dmc.Space(h="md"),

        # Main Content - Two Column Layout
        dmc.Group([
            # Left Column: Calendar and Output Directory
            dmc.Box([
                dmc.Stack([
                    # Calendar Selection Section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="calendar3", width=20),
                                dmc.Text("Archive Date Selection",
                                         fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            dmc.Center([
                                dmc.DatePicker(
                                    id="archive-date-picker",
                                    value=date.today().isoformat(),  # Use ISO format
                                    defaultDate=date.today(),  # Controls calendar view
                                    maxDate=date(2030, 12, 31),
                                    minDate=date(2000, 1, 1),
                                    size="lg",
                                    allowDeselect=False
                                )
                            ]),

                            html.Div(
                                id='archive-date-status',
                                style={'fontSize': '0.9rem',
                                       'minHeight': '20px'}
                            )

                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True),

                    # Directory Selection Section
                    directory_component

                ], gap="md")
            ], style={"flex": "1", "minWidth": "350px"}),

            # Right Column: Line Selection and Fetch Button
            dmc.Box([
                dmc.Stack([
                    # Pipeline Lines Selection
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="diagram-3", width=20),
                                dmc.Text("Pipeline Lines Selection",
                                         fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            # Error message placeholder
                            html.Div(id="lines-error-message-fetch"),

                            # Lines checklist with loading
                            dcc.Loading(
                                id="lines-loading-fetch",
                                type="default",
                                children=[
                                    dmc.CheckboxGroup(
                                        id="lines-checklist-fetch",
                                        value=[],
                                        children=[],
                                        style={
                                            "columnCount": "2",
                                            "columnGap": "16px",
                                            "lineHeight": "1.6",
                                            "fontSize": "0.85rem"
                                        },
                                        styles={
                                            "root": {"gap": "8px"}
                                        }
                                    )
                                ]
                            ),

                            # Select All section
                            dmc.Divider(size="xs"),
                            dmc.Center([
                                dmc.CheckboxGroup(
                                    id="select-all-lines-checkbox-fetch",
                                    value=[],  # Start unchecked
                                    children=[
                                        dmc.Checkbox(
                                            label="Select All Lines",
                                            value="select_all",
                                            styles={
                                                "input": {"border-radius": "4px"},
                                                "body": {"align-items": "flex-start"},
                                                "labelWrapper": {"margin-left": "8px"}
                                            }
                                        )
                                    ]
                                )
                            ])

                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True),

                    # Fetch Button Section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="cloud-download", width=20),
                                dmc.Text("Archive Extraction",
                                         fw=500, size="md")
                            ], gap="xs", justify="center"),

                            dmc.Divider(size="xs"),

                            # Fetch button and status
                            dmc.Stack([
                                dcc.Loading(
                                    id='fetch-archive-loading',
                                    type='default',
                                    children=html.Div([
                                        dmc.Button([
                                            BootstrapIcon(
                                                icon="cloud-download", width=20),
                                            "Fetch Archive Data"
                                        ], id='fetch-archive-btn', size="lg", disabled=True, className="px-4", variant="filled")
                                    ], id='fetch-archive-content')
                                ),

                                html.Div(
                                    id='fetch-processing-status',
                                    style={'minHeight': '20px',
                                           'textAlign': 'center'}
                                )
                            ], align="center", gap="sm")

                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True)

                ], gap="md")
            ], style={"flex": "1", "minWidth": "350px"})

        ], grow=True, gap="lg", align="stretch", wrap="wrap")

    ], gap="md")

], size="lg", p="sm")


# Callback to set today's date when page loads with delay
@callback(
    Output('archive-date-picker', 'value'),
    Input('archive-date-picker', 'id'),
    prevent_initial_call=False
)
def set_todays_date(_):
    """Set today's date when the component loads."""
    import time
    time.sleep(0.1)  # Small delay to ensure component is ready
    today = date.today()
    logger.info(f"Setting calendar date to: {today}")
    return today


# Help modal callback
@callback(
    Output("help-modal-fetch", "opened"),
    Input("help-modal-btn-fetch", "n_clicks"),
    State("help-modal-fetch", "opened"),
    prevent_initial_call=True,
)
def toggle_help_modal(n, opened):
    """Toggle the help modal."""
    return not opened


# Callback to load available lines on page startup
@callback(
    [Output('available-lines-store-fetch', 'data'),
     Output('lines-checklist-fetch', 'children'),
     Output('lines-error-message-fetch', 'children')],
    [Input('available-lines-store-fetch', 'id')]  # Triggers on page load
)
def load_available_lines(_):
    """Load available pipeline lines from FetchArchiveService."""
    try:
        # Fetch available lines
        result = fetch_archive_service.get_available_lines()

        if result['success']:
            lines = result['lines']
            checkbox_children = [
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
            return lines, checkbox_children, ""
        else:
            # Return empty options with error message
            error_msg = dmc.Alert(
                children=[
                    dmc.Group([
                        BootstrapIcon(icon="exclamation-triangle", width=16),
                        dmc.Text(
                            f"UNC path not accessible: {result['message']}", size="sm")
                    ], gap="xs")
                ],
                color="yellow",
                variant="light",
                className="mb-3"
            )
            return [], [], error_msg

    except Exception as e:
        logger.error(f"Error loading pipeline lines: {e}")
        error_msg = dmc.Alert(
            children=[
                dmc.Group([
                    BootstrapIcon(icon="x-circle", width=16),
                    dmc.Text(
                        f"Error loading pipeline lines: {str(e)}", size="sm")
                ], gap="xs")
            ],
            color="red",
            variant="light",
            className="mb-3"
        )
        return [], [], error_msg


# Callback for select all functionality
@callback(
    Output('lines-checklist-fetch', 'value'),
    [Input('select-all-lines-checkbox-fetch', 'value')],
    [State('available-lines-store-fetch', 'data'),
     State('lines-checklist-fetch', 'value')],
    prevent_initial_call=True
)
def toggle_select_all_lines(select_all_value, available_lines, current_selection):
    """Toggle select all lines functionality - only responds to user clicks."""
    # Handle select all checkbox
    if select_all_value and 'select_all' in select_all_value:
        # Select all lines - extract values from line objects
        return [line['value'] for line in available_lines] if available_lines else []
    else:
        # Deselect all lines
        return []


# Callback to enable/disable fetch button based on form validation
@callback(
    Output('fetch-archive-btn', 'disabled'),
    [Input('archive-date-picker', 'value'),
     Input('lines-checklist-fetch', 'value'),
     Input(directory_ids['input'], 'value'),
     Input('fetch-status-store', 'data')]
)
def validate_fetch_form(selected_date, selected_lines, output_directory, fetch_status):
    """Enable fetch button only when all required fields are filled and not processing."""
    # Disable if currently processing
    if fetch_status and fetch_status.get('status') == 'processing':
        return True
    
    # Disable if any required field is missing
    if not selected_date or not selected_lines or not output_directory:
        return True
    
    return False


# Callback for fetch archive data functionality with notifications
@callback(
    [Output('fetch-processing-status', 'children'),
     Output('fetch-status-store', 'data'),
     Output('fetch-archive-btn', 'disabled', allow_duplicate=True),
     Output('notification-container', 'sendNotifications', allow_duplicate=True)],
    [Input('fetch-archive-btn', 'n_clicks')],
    [State('archive-date-picker', 'value'),
     State('lines-checklist-fetch', 'value'),
     State(directory_ids['input'], 'value'),
     State('fetch-status-store', 'data')],
    prevent_initial_call=True
)
def fetch_archive_data(n_clicks, selected_date, selected_lines, output_directory, current_status):
    """Fetch archive data using FetchArchiveService with notifications."""
    if not n_clicks:
        return "", {'status': 'idle'}, False, no_update

    # Prevent re-running if already processing
    if current_status.get('status') == 'processing':
        return no_update, no_update, no_update, no_update

    try:
        logger.info(
            f"Starting fetch for {len(selected_lines)} lines on {selected_date}")

        # Show simple processing message
        processing_status = "Processing archive data..."

        # Parse date - DatePicker returns a date object
        if isinstance(selected_date, str):
            archive_date = datetime.strptime(selected_date, '%Y-%m-%d')
        else:
            # selected_date is already a date object
            archive_date = datetime.combine(selected_date, datetime.min.time())

        # Call fetch service (this runs in background)
        result = fetch_archive_service.fetch_archive_data(
            archive_date=archive_date,
            line_ids=selected_lines,
            output_directory=output_directory
        )

        if result['success']:
            files_count = len(result['files'])
            failed_count = len(result.get('failed_lines', []))
            processed_lines = len(selected_lines) - failed_count

            if failed_count == 0:
                # Complete success - focus on lines processed
                if processed_lines == 1:
                    notification = [{
                        "title": "Fetch Complete!",
                        "message": f"Successfully processed 1 line ({files_count} file(s) extracted) to {output_directory}",
                        "color": "green",
                        "autoClose": 7000,
                        "action": "show"
                    }]
                else:
                    notification = [{
                        "title": "Fetch Complete!",
                        "message": f"Successfully processed {processed_lines} lines ({files_count} file(s) extracted) to {output_directory}",
                        "color": "green",
                        "autoClose": 7000,
                        "action": "show"
                    }]
            else:
                # Partial success
                notification = [{
                    "title": "Partial Success",
                    "message": f"Processed {processed_lines} line(s), {failed_count} failed ({files_count} file(s) extracted). Check logs for details.",
                    "color": "yellow",
                    "autoClose": 7000,
                    "action": "show"
                }]

            return "", {'status': 'completed'}, False, notification
        else:
            # Complete failure
            notification = [{
                "title": "Fetch Failed",
                "message": result['message'],
                "color": "red",
                "autoClose": 7000,
                "action": "show"
            }]

            return "", {'status': 'error'}, False, notification

    except Exception as e:
        logger.error(f"Unexpected error during archive fetch: {e}")

        notification = [{
            "title": "Unexpected Error",
            "message": f"An unexpected error occurred: {str(e)}",
            "color": "red",
            "autoClose": 7000,
            "action": "show"
        }]

        return "", {'status': 'error'}, False, notification


# Callback to show date selection feedback
@callback(
    Output('archive-date-status', 'children'),
    [Input('archive-date-picker', 'value')]
)
def update_date_status(selected_date):
    """Show feedback for selected date."""
    if not selected_date:
        return ""

    try:
        if isinstance(selected_date, str):
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        else:
            date_obj = selected_date

        formatted_date = date_obj.strftime('%B %d, %Y')
        date_folder = date_obj.strftime('%Y%m%d')

        return dmc.Alert(
            children=[
                dmc.Group([
                    BootstrapIcon(icon="calendar-check", width=16),
                    dmc.Text(
                        f"Selected: {formatted_date} (Folder: {date_folder})", size="sm")
                ], gap="xs")
            ],
            color="blue",
            variant="light"
        )

    except Exception:
        return dmc.Alert(
            children=[
                dmc.Group([
                    BootstrapIcon(icon="exclamation-triangle", width=16),
                    dmc.Text("Invalid date selected", size="sm")
                ], gap="xs")
            ],
            color="yellow",
            variant="light"
        )


# Create directory selector callback
create_directory_selector_callback(
    directory_ids, "Select Output Directory for Archive Files")
