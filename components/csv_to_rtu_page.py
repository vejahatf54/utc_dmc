"""
CSV to RTU Converter page component - Refactored Implementation

This component follows clean architecture principles while maintaining
the exact same UI layout and design as the original implementation.
Uses controller pattern and dependency injection.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context, dcc, ALL, no_update
from components.bootstrap_icon import BootstrapIcon
from components.directory_selector import create_directory_selector

# Import the controller and services through dependency injection
from core.dependency_injection import DIContainer
from controllers.csv_to_rtu_controller import CsvToRtuPageController, CsvToRtuUIResponseFormatter


def create_csv_to_rtu_page():
    """Create the CSV to RTU Converter page layout - Refactored Version."""

    # Create directory selector component
    directory_component, directory_ids = create_directory_selector(
        component_id='csv-rtu-output',
        title="Output Directory for RTU Files",
        placeholder="Select directory for RTU output files...",
        browse_button_text="Browse Folder"
    )

    return dmc.Container([
        # Data stores
        dcc.Store(id='csv-files-store', data=[]),
        dcc.Store(id='csv-processing-store', data={'status': 'idle'}),
        dcc.Store(id=directory_ids['store'], data={'path': ''}),

        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("CSV to RTU Converter",
                                  order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(
                                icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="help-modal-btn",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Convert CSV files to RTU data format using sps_api",
                             c="dimmed", ta="center", size="md")
                ], gap="xs")
            ]),

            # Help Modal
            dmc.Modal(
                title="CSV to RTU Converter - Complete Guide",
                id="help-modal",
                children=[
                    dmc.Stack([
                        # Main Instructions
                        dmc.Alert(
                            children=[
                                dmc.Text([
                                    "• Select the directory containing all the CSV files exported from PI.",
                                    html.Br(),
                                    "• PI data shall be exported into the following CSV file format"
                                ])
                            ],
                            icon=BootstrapIcon(icon="info-circle", width=20),
                            title="Overview",
                            color="blue",
                            variant="outline"
                        ),

                        dmc.Space(h="sm"),

                        # CSV Format Example
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Text("Required CSV Format:",
                                         fw=600, size="md"),
                                dmc.Code(
                                    """Time_Stamp,    TAG1,    TAG2,    TAG3,    ...
9/1/2021 0:00:00, VALUE1, VALUE2, VALUE3, ...
...""",
                                    block=True,
                                )
                            ], gap="sm")
                        ], withBorder=True, p="lg"),

                        dmc.Space(h="md"),

                        # Format Specifications with better spacing
                        dmc.Grid([
                            dmc.GridCol([
                                dmc.Paper([
                                    dmc.Stack([
                                        dmc.Group([
                                            BootstrapIcon(
                                                icon="calendar", width=20, color="var(--mantine-color-blue-6)"),
                                            dmc.Text(
                                                "Column Specifications", fw=600, size="md")
                                        ], gap="sm"),
                                        dmc.Divider(size="xs"),
                                        dmc.List([
                                            dmc.ListItem([
                                                dmc.Text("Time_stamp",
                                                         fw=600, c="blue"),
                                                dmc.Text(
                                                    " - is a valid date time format associated with point", size="sm")
                                            ]),
                                            dmc.ListItem([
                                                dmc.Text(
                                                    "TAG1...3", fw=600, c="blue"),
                                                dmc.Text(
                                                    " - are the MBS tags defined in the lxx_scada.inc", size="sm")
                                            ]),
                                            dmc.ListItem([
                                                dmc.Text("VALUE1...3",
                                                         fw=600, c="blue"),
                                                dmc.Text(
                                                    " - are measured float values associated with each tags", size="sm")
                                            ])
                                        ], spacing="sm")
                                    ], gap="sm")
                                ], withBorder=True, p="md")
                            ], span=6),
                            dmc.GridCol([
                                dmc.Paper([
                                    dmc.Stack([
                                        dmc.Group([
                                            BootstrapIcon(
                                                icon="gear", width=20, color="var(--mantine-color-green-6)"),
                                            dmc.Text("Process Steps",
                                                     fw=600, size="md")
                                        ], gap="sm"),
                                        dmc.Divider(size="xs"),
                                        dmc.List([
                                            dmc.ListItem([
                                                dmc.Text(
                                                    "1. Upload CSV files", fw=500),
                                                dmc.Text(
                                                    " with the correct format", size="sm")
                                            ]),
                                            dmc.ListItem([
                                                dmc.Text(
                                                    "2. Select output directory", fw=500),
                                                dmc.Text(
                                                    " for RTU files", size="sm")
                                            ]),
                                            dmc.ListItem([
                                                dmc.Text(
                                                    "3. Click ", size="sm"),
                                                dmc.Text(
                                                    "Write RtuFile", fw=600, c="green", span=True),
                                                dmc.Text(
                                                    " to convert files", size="sm")
                                            ]),
                                            dmc.ListItem([
                                                dmc.Text(
                                                    "4. RTU files saved", fw=500),
                                                dmc.Text(
                                                    " with same name in same directory", size="sm")
                                            ])
                                        ], spacing="sm")
                                    ], gap="sm")
                                ], withBorder=True, p="md")
                            ], span=6)
                        ], gutter="lg"),

                        dmc.Space(h="md"),

                        # Warning Section
                        dmc.Alert(
                            children=[
                                dmc.Text([
                                    "If ",
                                    dmc.Text("VALUE1...3", fw=700,
                                             c="orange", span=True),
                                    " cannot be parsed into a float number value, the value by default will be set to ",
                                    dmc.Text("ZERO", fw=700,
                                             c="red", span=True),
                                    " and the quality of the point will be set to ",
                                    dmc.Text("BAD", fw=700,
                                             c="red", span=True),
                                    " in the RTU data file."
                                ])
                            ],
                            icon=BootstrapIcon(
                                icon="exclamation-triangle", width=20),
                            title="Important Warning",
                            color="orange",
                            variant="outline"
                        ),

                        dmc.Space(h="sm"),

                        # Requirements Section
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(
                                        icon="check-circle", width=20, color="var(--mantine-color-teal-6)"),
                                    dmc.Text("System Requirements",
                                             fw=600, size="md")
                                ], gap="sm"),
                                dmc.Divider(size="xs"),
                                dmc.List([
                                    dmc.ListItem(
                                        "sps_api library installed (pip install sps_api)"),
                                    dmc.ListItem(
                                        "Valid output directory selected"),
                                    dmc.ListItem(
                                        "Write permissions to output folder"),
                                    dmc.ListItem(
                                        "CSV files must have timestamp as first column"),
                                    dmc.ListItem(
                                        "Date/time format must be parseable (e.g., M/d/yyyy H:mm:ss)")
                                ], spacing="xs")
                            ], gap="sm")
                        ], withBorder=True, p="md")
                    ], gap="md")
                ],
                opened=False,
                size="xl"
            ),

            dmc.Space(h="md"),

            # Main Content - Flexible Side by Side Layout
            dmc.Group([
                # File Upload Section
                dmc.Box([
                    dmc.Paper([
                        dmc.Stack([
                            # Header with icon
                            dmc.Group([
                                BootstrapIcon(icon="upload", width=20),
                                dmc.Text("CSV File Upload", fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            # Upload area
                            html.Div([
                                dcc.Upload(
                                    id='csv-upload',
                                    children=dmc.Stack([
                                        dmc.Center([
                                            BootstrapIcon(
                                                icon="cloud-upload", width=48, height=48, color="var(--mantine-color-blue-6)")
                                        ]),
                                        dmc.Text('Drag and Drop CSV Files',
                                                 size="md", fw=500, ta="center"),
                                        dmc.Text(
                                            'or click to browse', size="sm", c="dimmed", ta="center")
                                    ], gap="sm", p="md", align="center"),
                                    style={
                                        'width': '100%',
                                        'height': '150px',
                                        'borderWidth': '2px',
                                        'borderStyle': 'dashed',
                                        'borderRadius': '8px',
                                        'cursor': 'pointer',
                                        'display': 'flex',
                                        'alignItems': 'center',
                                        'justifyContent': 'center'
                                    },
                                    multiple=True,
                                    accept='.csv'
                                )
                            ], id='csv-upload-container'),

                            # File list display
                            html.Div(
                                id='csv-file-list',
                                style={'minHeight': '50px'}
                            ),

                            # Upload status
                            html.Div(id='csv-upload-status')

                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True)
                ], style={"flex": "1", "minWidth": "350px"}),

                # Output Directory and RTU Conversion - Stacked in one column
                dmc.Box([
                    dmc.Stack([
                        # Directory Selection Section
                        directory_component,

                        # RTU Conversion Section
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(
                                        icon="arrow-repeat", width=20),
                                    dmc.Text("RTU Conversion",
                                             fw=500, size="md")
                                ], gap="xs", justify="center"),

                                dmc.Divider(size="xs"),

                                # Conversion button and status
                                dmc.Stack([
                                    dcc.Loading(
                                        id='write-rtu-loading',
                                        type='default',
                                        children=html.Div([
                                            dmc.Button([
                                                BootstrapIcon(
                                                    icon="download", width=20),
                                                "Write RTU Data"
                                            ], id='write-rtu-btn', size="lg", disabled=True, className="px-4", variant="filled")
                                        ], id='write-rtu-content')
                                    ),

                                    html.Div(
                                        id='rtu-processing-status',
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


# Initialize controller through dependency injection
def _get_controller() -> CsvToRtuPageController:
    """Get CSV to RTU controller from dependency injection container."""
    container = DIContainer.get_instance()
    return container.resolve('csv_to_rtu_controller')


# File upload callback
@callback(
    [
        Output('csv-files-store', 'data'),
        Output('csv-file-list', 'children'),
        Output('csv-upload-status', 'children'),
        Output('write-rtu-btn', 'disabled')
    ],
    Input('csv-upload', 'contents'),
    [State('csv-upload', 'filename'), State('csv-files-store', 'data')]
)
def handle_csv_upload(contents, filenames, stored_files):
    """Handle CSV file upload using controller."""
    controller = _get_controller()
    result = controller.handle_csv_upload(contents, filenames, stored_files)
    return CsvToRtuUIResponseFormatter.format_upload_response(result)


# Pattern-matching callback for file removal
@callback(
    [
        Output('csv-files-store', 'data', allow_duplicate=True),
        Output('csv-file-list', 'children', allow_duplicate=True),
        Output('csv-upload-status', 'children', allow_duplicate=True),
        Output('write-rtu-btn', 'disabled', allow_duplicate=True),
        Output('csv-upload-container', 'children', allow_duplicate=True)
    ],
    Input({'type': 'remove-file-btn', 'index': ALL}, 'n_clicks'),
    State('csv-files-store', 'data'),
    prevent_initial_call=True
)
def remove_csv_file(n_clicks, stored_files):
    """Remove a specific CSV file using controller."""
    # Check if any button was actually clicked
    if not n_clicks or not any(n_clicks) or not stored_files:
        return no_update, no_update, no_update, no_update, no_update

    # Get callback context to identify which button was clicked
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update

    # Parse the triggered component ID to get the filename
    triggered_prop_id = ctx.triggered[0]['prop_id']
    component_id_str = triggered_prop_id.rsplit('.n_clicks', 1)[0]

    try:
        import json
        component_id = json.loads(component_id_str)
        filename_to_remove = component_id['index']
    except (json.JSONDecodeError, KeyError):
        return no_update, no_update, no_update, no_update, no_update

    # Use controller to handle file removal
    controller = _get_controller()
    result = controller.handle_file_removal(filename_to_remove, stored_files)

    # Format response
    files, file_components, status_message, upload_disabled = CsvToRtuUIResponseFormatter.format_file_removal_response(
        result)

    # Recreate upload component to allow re-uploading same filename
    new_upload = dcc.Upload(
        id='csv-upload-v2',
        children=dmc.Stack([
            dmc.Center([BootstrapIcon(icon="cloud-upload", width=48,
                       height=48, color="var(--mantine-color-blue-6)")]),
            dmc.Text('Drag and Drop CSV Files',
                     size="md", fw=500, ta="center"),
            dmc.Text('or click to browse', size="sm", c="dimmed", ta="center")
        ], gap="sm", p="md", align="center"),
        style={
            'width': '100%',
            'height': '150px',
            'borderWidth': '2px',
            'borderStyle': 'dashed',
            'borderRadius': '8px',
            'cursor': 'pointer',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center'
        },
        multiple=True,
        accept='.csv'
    )

    return files, file_components, status_message, upload_disabled, new_upload


# Help modal callback
@callback(
    Output('help-modal', 'opened'),
    Input('help-modal-btn', 'n_clicks'),
    State('help-modal', 'opened'),
    prevent_initial_call=True
)
def toggle_help_modal(n_clicks, opened):
    """Toggle help modal visibility."""
    return not opened


# Directory selector callback
@callback(
    [Output('directory-input-csv-rtu-output', 'value'),
     Output('directory-status-csv-rtu-output', 'children'),
     Output('directory-store-csv-rtu-output', 'data')],
    Input('browse-btn-csv-rtu-output', 'n_clicks'),
    prevent_initial_call=True
)
def handle_directory_selection(browse_clicks):
    """Handle directory selection using controller."""
    ctx = callback_context
    if not ctx.triggered:
        return "", "", {'path': ''}

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'browse-btn-csv-rtu-output':
        controller = _get_controller()
        result = controller.handle_directory_selection()
        return CsvToRtuUIResponseFormatter.format_directory_selection_response(result)

    return "", "", {'path': ''}


# RTU conversion callback
@callback(
    [Output('csv-processing-store', 'data'),
     Output('rtu-processing-status', 'children'),
     Output('write-rtu-content', 'children'),
     Output('notification-container', 'sendNotifications', allow_duplicate=True)],
    Input('write-rtu-btn', 'n_clicks'),
    [State('csv-files-store', 'data'),
     State('directory-store-csv-rtu-output', 'data')],
    prevent_initial_call=True
)
def write_rtu_data(n_clicks, csv_files, output_dir_data):
    """Handle RTU conversion using controller."""
    if not n_clicks or not csv_files:
        # Initial state - idle button
        idle_button = dmc.Button([
            BootstrapIcon(icon="download", width=20),
            "Write RTU Data"
        ], id='write-rtu-btn', size="lg", disabled=len(csv_files or []) == 0, className="px-4", variant="filled")

        return {'status': 'idle'}, "", idle_button, no_update

    # Use controller to handle conversion
    controller = _get_controller()
    result = controller.handle_rtu_conversion(csv_files, output_dir_data)

    return CsvToRtuUIResponseFormatter.format_conversion_response(result)
