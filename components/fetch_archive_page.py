"""
Fetch Archive Page for DMC Application.
Allows users to select dates, pipeline lines, and output directories to fetch historical data.
"""

import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from datetime import datetime, date
from typing import List, Dict, Any
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
                                    dbc.Checklist(
                                        id="lines-checklist-fetch",
                                        options=[],
                                        value=[],
                                        style={
                                            "columnCount": "2",
                                            "columnGap": "8px",
                                            "lineHeight": "1.2",
                                            "fontSize": "0.85rem"
                                        },
                                        inline=False,
                                        className="compact-checklist"
                                    )
                                ]
                            ),

                            # Select All section
                            dmc.Divider(size="xs"),
                            dmc.Center([
                                dbc.Checklist(
                                    id="select-all-lines-checkbox-fetch",
                                    options=[
                                        {"label": "Select All Lines",
                                            "value": "select_all"}
                                    ],
                                    # Default to selected
                                    value=["select_all"],
                                    className="fw-medium"
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

    ], gap="md"),

    # Notification container
    dmc.NotificationProvider()

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
     Output('lines-checklist-fetch', 'options'),
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
            return lines, lines, ""
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
    [Input('select-all-lines-checkbox-fetch', 'value'),
     # Also trigger when lines are loaded
     Input('available-lines-store-fetch', 'data')],
    [State('lines-checklist-fetch', 'value')],
    prevent_initial_call=False
)
def toggle_select_all_lines(select_all_value, available_lines, current_selection):
    """Toggle select all lines functionality and auto-select all on page load."""
    ctx = dash.callback_context

    # Check if this is triggered by the available lines being loaded (page load)
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'available-lines-store-fetch.data':
        if available_lines:
            # Auto-select all lines on page load
            return [line['value'] for line in available_lines]
        else:
            return []

    # Handle select all checkbox
    if select_all_value and 'select_all' in select_all_value:
        # Select all lines
        return [line['value'] for line in available_lines] if available_lines else []
    else:
        # Deselect all lines
        return []


# Callback to enable/disable fetch button based on form validation
@callback(
    Output('fetch-archive-btn', 'disabled'),
    [Input('archive-date-picker', 'value'),
     Input('lines-checklist-fetch', 'value'),
     Input(directory_ids['input'], 'value')]
)
def validate_fetch_form(selected_date, selected_lines, output_directory):
    """Enable fetch button only when all required fields are filled."""
    if not selected_date or not selected_lines or not output_directory:
        return True
    return False


# Callback for fetch archive data functionality with notifications
@callback(
    [Output('fetch-processing-status', 'children'),
     Output('fetch-status-store', 'data'),
     Output('notification-container', 'sendNotifications', allow_duplicate=True)],
    [Input('fetch-archive-btn', 'n_clicks')],
    [State('archive-date-picker', 'value'),
     State('lines-checklist-fetch', 'value'),
     State(directory_ids['input'], 'value')],
    prevent_initial_call=True
)
def fetch_archive_data(n_clicks, selected_date, selected_lines, output_directory):
    """Fetch archive data using FetchArchiveService with notifications."""
    if not n_clicks:
        return "", {'status': 'idle'}, no_update

    try:
        logger.info(
            f"Starting fetch for {len(selected_lines)} lines on {selected_date}")

        # Parse date - DatePicker returns a date object
        if isinstance(selected_date, str):
            archive_date = datetime.strptime(selected_date, '%Y-%m-%d')
        else:
            # selected_date is already a date object
            archive_date = datetime.combine(selected_date, datetime.min.time())

        # Call fetch service
        result = fetch_archive_service.fetch_archive_data(
            archive_date=archive_date,
            line_ids=selected_lines,
            output_directory=output_directory
        )

        if result['success']:
            files_count = len(result['files'])
            failed_count = len(result.get('failed_lines', []))

            if failed_count == 0:
                # Complete success
                notification = [{
                    "title": "Fetch Complete!",
                    "message": f"Successfully extracted {files_count} archive file(s) to {output_directory}",
                    "color": "green",
                    "autoClose": 7000,
                    "action": "show"
                }]

                status_content = dmc.Alert(
                    children=[
                        dmc.Group([
                            BootstrapIcon(icon="check-circle", width=16),
                            dmc.Text(
                                f"Success! Extracted {files_count} archive file(s)", size="sm")
                        ], gap="xs")
                    ],
                    color="green",
                    variant="light"
                )
            else:
                # Partial success
                notification = [{
                    "title": "Partial Success",
                    "message": f"Extracted {files_count} file(s), {failed_count} failed. Check logs for details.",
                    "color": "yellow",
                    "autoClose": 7000,
                    "action": "show"
                }]

                status_content = dmc.Alert(
                    children=[
                        dmc.Group([
                            BootstrapIcon(
                                icon="exclamation-triangle", width=16),
                            dmc.Text(
                                f"Partial Success: {files_count} files extracted, {failed_count} failed", size="sm")
                        ], gap="xs")
                    ],
                    color="yellow",
                    variant="light"
                )

            return status_content, {'status': 'completed'}, notification
        else:
            # Complete failure
            notification = [{
                "title": "Fetch Failed",
                "message": result['message'],
                "color": "red",
                "autoClose": 7000,
                "action": "show"
            }]

            status_content = dmc.Alert(
                children=[
                    dmc.Group([
                        BootstrapIcon(icon="x-circle", width=16),
                        dmc.Text(f"Error: {result['message']}", size="sm")
                    ], gap="xs")
                ],
                color="red",
                variant="light"
            )

            return status_content, {'status': 'error'}, notification

    except Exception as e:
        logger.error(f"Unexpected error during archive fetch: {e}")

        notification = [{
            "title": "Unexpected Error",
            "message": f"An unexpected error occurred: {str(e)}",
            "color": "red",
            "autoClose": 7000,
            "action": "show"
        }]

        status_content = dmc.Alert(
            children=[
                dmc.Group([
                    BootstrapIcon(icon="x-circle", width=16),
                    dmc.Text(f"Unexpected Error: {str(e)}", size="sm")
                ], gap="xs")
            ],
            color="red",
            variant="light"
        )

        return status_content, {'status': 'error'}, notification


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
