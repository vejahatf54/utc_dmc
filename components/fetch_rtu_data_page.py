"""
Fetch RTU Data Page for DMC Application.
Allows users to select date ranges or single dates, pipeline lines, and output directories to fetch RTU data.
"""

import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import dash_mantine_components as dmc
from datetime import datetime, date
import logging
import os

from components.bootstrap_icon import BootstrapIcon
from components.directory_selector import create_directory_selector, create_directory_selector_callback
from services.fetch_rtu_data_service import FetchRtuDataService
from services.config_manager import get_config_manager

logger = logging.getLogger(__name__)

# Initialize services
fetch_rtu_service = FetchRtuDataService()

# Create directory selector component
directory_component, directory_ids = create_directory_selector(
    component_id='fetch-rtu-output',
    title="Output Directory for RTU Data Files",
    placeholder="Select directory for RTU data files...",
    browse_button_text="Browse"
)

# Layout
layout = dmc.Container([
    # Data stores
    dcc.Store(id='available-lines-store-rtu', data=[]),
    dcc.Store(id='fetch-rtu-status-store', data={'status': 'idle'}),
    dcc.Store(id=directory_ids['store'], data={'path': ''}),
    dcc.Store(id='rtu-date-mode-store', data={'mode': 'single'}),  # 'single' or 'range'

    # Header Section
    dmc.Stack([
        dmc.Center([
            dmc.Stack([
                dmc.Group([
                    dmc.Title("Fetch RTU Data", order=2, ta="center"),
                    dmc.ActionIcon(
                        BootstrapIcon(icon="question-circle", width=20,
                                      color="var(--mantine-color-blue-6)"),
                        id="help-modal-btn-rtu",
                        variant="light",
                        color="blue",
                        size="lg"
                    )
                ], justify="center", align="center", gap="md"),
                dmc.Text("Download RTU data files from backup repositories for analysis",
                         c="dimmed", ta="center", size="md")
            ], gap="xs")
        ]),

        # Help Modal
        dmc.Modal(
            title="How Fetch RTU Data Works",
            id="help-modal-rtu",
            children=[
                dmc.Grid([
                    dmc.GridCol([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="info-circle", width=20),
                                dmc.Text("RTU Data Structure", fw=500)
                            ], gap="xs"),
                            dmc.List([
                                dmc.ListItem(
                                    f"UNC Path: {get_config_manager().get_rtudata_base_path()}"),
                                dmc.ListItem(
                                    "Date folders in YYYYMMDD format (e.g., 20231226)"),
                                dmc.ListItem(
                                    "RTU data files organized by line and date"),
                                dmc.ListItem(
                                    "Files copied to organized output directories")
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
                                    "Select single date or date range"),
                                dmc.ListItem(
                                    "Choose pipeline lines to process"),
                                dmc.ListItem("Select output directory"),
                                dmc.ListItem(
                                    "Click 'Fetch RTU Data' to copy files")
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
            # Left Column: Date Selection and Output Directory
            dmc.Box([
                dmc.Stack([
                    # Date Selection Section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="calendar3", width=20),
                                dmc.Text("Date Selection",
                                         fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            # Date mode selection
                            dmc.RadioGroup(
                                children=dmc.Group([
                                    dmc.Radio("Single Date", value="single"),
                                    dmc.Radio("Date Range", value="range")
                                ], gap="xl", justify="center"),
                                id="date-mode-radio-rtu",
                                value="single",
                                size="sm"
                            ),

                            dmc.Space(h="xs"),

                            # Single date mode - Start Date to Current Date (always visible)
                            html.Div([
                                dmc.Grid([
                                    # Start Date Column
                                    dmc.GridCol([
                                        dmc.Stack([
                                            dmc.Text("Start Date:", size="sm", fw=500, ta="center"),
                                            dmc.DatePicker(
                                                id="single-date-picker-rtu",
                                                value=date.today().isoformat(),
                                                defaultDate=date.today(),
                                                maxDate=date(2030, 12, 31),
                                                minDate=date(2000, 1, 1),
                                                size="md",
                                                allowDeselect=False
                                            )
                                        ], gap="xs", align="center")
                                    ], span=6),
                                    # End Date Column (locked for single mode)
                                    dmc.GridCol([
                                        dmc.Stack([
                                            dmc.Text("End Date (Current):", size="sm", fw=500, ta="center"),
                                            dmc.DatePicker(
                                                id="single-end-date-picker-rtu",
                                                value=date.today().isoformat(),
                                                defaultDate=date.today(),
                                                maxDate=date.today(),
                                                minDate=date.today(),
                                                size="md",
                                                allowDeselect=False
                                            )
                                        ], gap="xs", align="center")
                                    ], span=6)
                                ], gutter="xxl", justify="center")
                            ], id="single-date-container-rtu", style={"display": "block"}),

                            # Date range picker (initially hidden)
                            html.Div([
                                dmc.Grid([
                                    # Start Date Column
                                    dmc.GridCol([
                                        dmc.Stack([
                                            dmc.Text("Start Date:", size="sm", fw=500, ta="center"),
                                            dmc.DatePicker(
                                                id="start-date-picker-rtu",
                                                value=date.today().isoformat(),
                                                defaultDate=date.today(),
                                                maxDate=date(2030, 12, 31),
                                                minDate=date(2000, 1, 1),
                                                size="md",
                                                allowDeselect=False
                                            )
                                        ], gap="xs", align="center")
                                    ], span=6),
                                    # End Date Column
                                    dmc.GridCol([
                                        dmc.Stack([
                                            dmc.Text("End Date:", size="sm", fw=500, ta="center"),
                                            dmc.DatePicker(
                                                id="end-date-picker-rtu",
                                                value=date.today().isoformat(),
                                                defaultDate=date.today(),
                                                maxDate=date(2030, 12, 31),
                                                minDate=date(2000, 1, 1),
                                                size="md",
                                                allowDeselect=False
                                            )
                                        ], gap="xs", align="center")
                                    ], span=6)
                                ], gutter="xxl", justify="center")
                            ], id="date-range-container-rtu", style={"display": "none"}),

                            html.Div(
                                id='date-status-rtu',
                                style={'fontSize': '0.9rem',
                                       'minHeight': '20px'}
                            )

                        ], gap="sm", p="md")
                    ], shadow="sm", radius="md", withBorder=True),

                    # Directory Selection Section
                    directory_component

                ], gap="md")
            ], style={"flex": "1", "minWidth": "750px", "maxWidth": "1000px"}),

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
                            html.Div(id="lines-error-message-rtu"),

                            # Lines checklist with loading
                            dcc.Loading(
                                id="lines-loading-rtu",
                                type="default",
                                children=[
                                    dmc.CheckboxGroup(
                                        id="lines-checklist-rtu",
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
                                    id="select-all-lines-checkbox-rtu",
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

                    # Server Filter Section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="funnel", width=20),
                                dmc.Text("Server Filter", fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            dmc.Stack([
                                dmc.Text("Filter by server (optional):", size="sm", fw=500),
                                dmc.TextInput(
                                    id="server-filter-input-rtu",
                                    placeholder="e.g., LPP02WVSPSS15, LPP02WV*, LPP02*SPSS*",
                                    description="Optional filter with wildcard support (* = any characters). Case-insensitive.",
                                    size="md"
                                )
                            ], gap="xs")

                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True),

                    # Fetch Button Section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="cloud-download", width=20),
                                dmc.Text("RTU Data Fetch",
                                         fw=500, size="md")
                            ], gap="xs", justify="center"),

                            dmc.Divider(size="xs"),

                            # Fetch button and status
                            dmc.Stack([
                                dcc.Loading(
                                    id='fetch-rtu-loading',
                                    type='default',
                                    children=html.Div([
                                        dmc.Button([
                                            BootstrapIcon(
                                                icon="cloud-download", width=20),
                                            "Fetch RTU Data"
                                        ], id='fetch-rtu-btn', size="lg", disabled=True, className="px-4", variant="filled")
                                    ], id='fetch-rtu-content')
                                ),

                                html.Div(
                                    id='fetch-rtu-processing-status',
                                    style={'minHeight': '20px',
                                           'textAlign': 'center'}
                                )
                            ], align="center", gap="sm")

                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True)

                ], gap="md")
            ], style={"flex": "1", "minWidth": "350px"})

        ], grow=True, gap="lg", align="stretch", wrap="nowrap", style={"minWidth": "1500px"})

    ], gap="md")

], fluid=True, p="sm")


# Callback to set initial directory path
@callback(
    [Output(directory_ids['input'], 'value'),
     Output(directory_ids['browse'], 'disabled')],
    Input(directory_ids['input'], 'id'),
    prevent_initial_call=False
)
def set_initial_directory(_):
    """Set initial directory to default RTU data path if it exists."""
    default_path = get_config_manager().get_rtudata_default_output_path()
    
    # Check if default path exists
    if os.path.exists(default_path) and os.path.isdir(default_path):
        logger.info(f"Using default RTU output path: {default_path}")
        return default_path, True  # Disable browse button
    else:
        logger.info(f"Default RTU output path not found: {default_path}")
        return "", False  # Enable browse button


# Callback to toggle date mode
@callback(
    [Output('single-date-container-rtu', 'style'),
     Output('date-range-container-rtu', 'style'),
     Output('rtu-date-mode-store', 'data')],
    Input('date-mode-radio-rtu', 'value')
)
def toggle_date_mode(mode):
    """Toggle between single date and date range modes."""
    if mode == 'single':
        return {"display": "block"}, {"display": "none"}, {'mode': 'single'}
    else:
        return {"display": "none"}, {"display": "block"}, {'mode': 'range'}


# Help modal callback
@callback(
    Output("help-modal-rtu", "opened"),
    Input("help-modal-btn-rtu", "n_clicks"),
    State("help-modal-rtu", "opened"),
    prevent_initial_call=True,
)
def toggle_help_modal(n, opened):
    """Toggle the help modal."""
    return not opened


# Callback to load available lines on page startup
@callback(
    [Output('available-lines-store-rtu', 'data'),
     Output('lines-checklist-rtu', 'children'),
     Output('lines-error-message-rtu', 'children')],
    [Input('available-lines-store-rtu', 'id')]  # Triggers on page load
)
def load_available_lines(_):
    """Load available pipeline lines from FetchRtuDataService."""
    try:
        # Fetch available lines
        result = fetch_rtu_service.get_available_lines()

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
    Output('lines-checklist-rtu', 'value'),
    [Input('select-all-lines-checkbox-rtu', 'value')],
    [State('available-lines-store-rtu', 'data'),
     State('lines-checklist-rtu', 'value')],
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
    Output('fetch-rtu-btn', 'disabled'),
    [Input('single-date-picker-rtu', 'value'),
     Input('start-date-picker-rtu', 'value'),
     Input('end-date-picker-rtu', 'value'),
     Input('lines-checklist-rtu', 'value'),
     Input(directory_ids['input'], 'value'),
     Input('fetch-rtu-status-store', 'data'),
     Input('rtu-date-mode-store', 'data')]
)
def validate_fetch_form(single_date, start_date, end_date, selected_lines, output_directory, fetch_status, date_mode):
    """Enable fetch button only when all required fields are filled and not processing."""
    # Disable if currently processing
    if fetch_status and fetch_status.get('status') == 'processing':
        return True
    
    # Check if required fields are filled based on date mode
    mode = date_mode.get('mode', 'single') if date_mode else 'single'
    
    # Validate date inputs based on mode
    date_valid = False
    if mode == 'single':
        date_valid = bool(single_date)
    else:  # range mode
        date_valid = bool(start_date and end_date)
    
    # Disable if any required field is missing
    if not date_valid or not selected_lines or not output_directory:
        return True
    
    return False


# Callback for fetch RTU data functionality with notifications
@callback(
    [Output('fetch-rtu-processing-status', 'children'),
     Output('fetch-rtu-status-store', 'data'),
     Output('fetch-rtu-btn', 'disabled', allow_duplicate=True),
     Output('notification-container', 'sendNotifications', allow_duplicate=True)],
    [Input('fetch-rtu-btn', 'n_clicks')],
    [State('single-date-picker-rtu', 'value'),
     State('start-date-picker-rtu', 'value'),
     State('end-date-picker-rtu', 'value'),
     State('lines-checklist-rtu', 'value'),
     State(directory_ids['input'], 'value'),
     State('server-filter-input-rtu', 'value'),
     State('fetch-rtu-status-store', 'data'),
     State('rtu-date-mode-store', 'data')],
    prevent_initial_call=True
)
def fetch_rtu_data(n_clicks, single_date, start_date, end_date, selected_lines, output_directory, server_filter, current_status, date_mode):
    """Fetch RTU data using FetchRtuDataService with notifications."""
    if not n_clicks:
        return "", {'status': 'idle'}, False, no_update

    # Prevent multiple simultaneous requests
    if current_status and current_status.get('status') == 'processing':
        return dmc.Text("Processing...", c="blue"), current_status, True, no_update

    try:
        # Set processing status
        processing_status = dmc.Text("Processing...", c="blue")
        status_data = {'status': 'processing'}

        # Determine date parameters based on mode
        mode = date_mode.get('mode', 'single') if date_mode else 'single'
        
        if mode == 'single':
            fetch_result = fetch_rtu_service.fetch_rtu_data(
                line_ids=selected_lines,
                output_directory=output_directory,
                single_date=single_date,
                server_filter=server_filter
            )
        else:  # range mode
            fetch_result = fetch_rtu_service.fetch_rtu_data(
                line_ids=selected_lines,
                output_directory=output_directory,
                start_date=start_date,
                end_date=end_date,
                server_filter=server_filter
            )

        if fetch_result['success']:
            summary = fetch_result['summary']
            success_status = dmc.Text(f"✓ Success! {summary['total_files_extracted']} files extracted", c="green")
            
            # Success notification
            notification = {
                'id': f'rtu-fetch-success-{datetime.now().timestamp()}',
                'message': f"RTU data fetch completed successfully! {summary['total_files_extracted']} files extracted for {summary['lines_processed']} lines.",
                'color': 'green',
                'autoClose': 5000,
                'icon': BootstrapIcon(icon="check-circle", width=20)
            }
            
            return success_status, {'status': 'idle'}, False, [notification]
        else:
            error_status = dmc.Text(f"✗ Error: {fetch_result['message']}", c="red")
            
            # Error notification
            notification = {
                'id': f'rtu-fetch-error-{datetime.now().timestamp()}',
                'message': f"RTU data fetch failed: {fetch_result['message']}",
                'color': 'red',
                'autoClose': 7000,
                'icon': BootstrapIcon(icon="x-circle", width=20)
            }
            
            return error_status, {'status': 'idle'}, False, [notification]

    except Exception as e:
        logger.error(f"Error in RTU data fetch callback: {e}")
        error_status = dmc.Text(f"✗ Unexpected error: {str(e)}", c="red")
        
        # Error notification
        notification = {
            'id': f'rtu-fetch-exception-{datetime.now().timestamp()}',
            'message': f"Unexpected error during RTU data fetch: {str(e)}",
            'color': 'red',
            'autoClose': 7000,
            'icon': BootstrapIcon(icon="exclamation-triangle", width=20)
        }
        
        return error_status, {'status': 'idle'}, False, [notification]


# Callback to handle directory selection browse button
@callback(
    [Output(directory_ids['input'], 'value', allow_duplicate=True),
     Output(directory_ids['status'], 'children'),
     Output(directory_ids['store'], 'data')],
    [Input(directory_ids['browse'], 'n_clicks')],
    prevent_initial_call=True
)
def handle_directory_browse(browse_clicks):
    """Handle directory selection via browse button."""
    if not browse_clicks:
        return no_update, no_update, no_update

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.lift()      # Bring to front
        root.attributes("-topmost", True)

        directory = filedialog.askdirectory(title="Select Output Directory for RTU Data")
        root.destroy()

        if directory:
            return directory, "", {'path': directory}
        else:
            return no_update, no_update, no_update

    except Exception as e:
        logger.error(f"Error selecting directory: {str(e)}")
        return no_update, dmc.Text(f"Error: {str(e)}", c="red"), no_update
