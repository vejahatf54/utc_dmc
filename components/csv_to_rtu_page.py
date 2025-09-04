"""
CSV to RTU Converter page component for DMC application.
Uses DMC components for file upload, directory selection, and conversion.
"""

import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, Input, Output, State, callback, callback_context, dcc, ALL, no_update
import base64
import io
import pandas as pd
import os
from typing import List, Dict, Any
from components.directory_selector import create_directory_selector, create_directory_selector_callback
from services.csv_to_rtu_service import CsvToRtuService


def create_csv_to_rtu_page():
    """Create the CSV to RTU Converter page layout."""

    # Create directory selector component
    directory_component, directory_ids = create_directory_selector(
        component_id='csv-rtu-output',
        title="Output Directory for RTU Files",
        placeholder="Select directory for RTU output files...",
        browse_button_text="Browse Folder",
        reset_button_text="Clear"
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
                        dmc.Title("CSV to RTU Converter", order=2, ta="center"),
                        dmc.ActionIcon(
                            DashIconify(icon="tabler:help", width=20, color="var(--mantine-color-blue-6)"),
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
                title="How It Works",
                id="help-modal",
                children=[
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    DashIconify(icon="tabler:info-circle", width=20),
                                    dmc.Text("Requirements", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem("CSV files with timestamp as first column"),
                                    dmc.ListItem("sps_api library installed (pip install sps_api)"),
                                    dmc.ListItem("Valid output directory selected"),
                                    dmc.ListItem("Write permissions to output folder")
                                ], size="sm")
                            ])
                        ], span=6),
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    DashIconify(icon="tabler:lightbulb", width=20),
                                    dmc.Text("Process", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem("Upload one or more CSV files"),
                                    dmc.ListItem("Select output directory for RTU files"),
                                    dmc.ListItem("Click 'Write RTU Data' to process files"),
                                    dmc.ListItem("RTU files will be saved with .dt extension")
                                ], size="sm")
                            ])
                        ], span=6)
                    ])
                ],
                opened=False,
                size="lg"
            ),

            dmc.Space(h="md"),

            # Main Content Grid
            dmc.SimpleGrid([
                # File Upload Section
                dmc.Paper([
                    dmc.Stack([
                        # Header with icon
                        dmc.Group([
                            DashIconify(icon="tabler:file-upload", width=20),
                            dmc.Text("CSV File Upload", fw=500, size="md")
                        ], gap="xs"),

                        dmc.Divider(size="xs"),

                        # Upload area
                        html.Div([
                            dcc.Upload(
                                id='csv-upload',
                                children=dmc.Stack([
                                    dmc.Center([
                                        DashIconify(icon="tabler:cloud-upload", width=48, height=48, color="var(--mantine-color-blue-6)")
                                    ]),
                                    dmc.Text('Drag and Drop CSV Files', size="md", fw=500, ta="center"),
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
                        ], id='csv-upload-container'),

                        # File list display
                        html.Div(
                            id='csv-file-list',
                            style={'minHeight': '50px'}
                        ),

                        # Upload status
                        html.Div(id='csv-upload-status')

                    ], gap="sm", p="sm")
                ], shadow="sm", radius="md", withBorder=True),

                # Directory Selection Section
                directory_component

            ], cols=1, spacing="md"),

            dmc.Space(h="md"),

            # Conversion Section
            dmc.Center([
                dmc.Paper([
                    dmc.Stack([
                        dmc.Group([
                            DashIconify(icon="tabler:transform", width=20),
                            dmc.Text("RTU Conversion", fw=500, size="md")
                        ], gap="xs", justify="center"),

                        dmc.Divider(size="xs"),

                        # Conversion button and status
                        dmc.Stack([
                            dcc.Loading(
                                id='write-rtu-loading',
                                type='default',
                                children=html.Div([
                                    dmc.Button([
                                        DashIconify(icon="tabler:file-export", width=20),
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
                ], shadow="sm", radius="md", withBorder=True, style={"width": "400px"})
            ])

        ], gap="md")
    ], size="lg", p="sm")


# Initialize the service
csv_rtu_service = CsvToRtuService()


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
    """Mirror LDUTC: load CSVs, build list, success alert."""
    if not contents:
        return stored_files or [], [], "", True

    if not isinstance(contents, list):
        contents = [contents]
        filenames = [filenames] if filenames else []

    new_files = stored_files or []

    for content, filename in zip(contents, filenames or []):
        if filename and filename.lower().endswith('.csv'):
            try:
                content_type, content_string = content.split(',')
                decoded = base64.b64decode(content_string)
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                file_info = {
                    'name': filename,
                    'content': content,
                    'rows': len(df),
                    'columns': len(df.columns),
                    'size': len(decoded)
                }
                if not any(f['name'] == filename for f in new_files):
                    new_files.append(file_info)
            except Exception:
                continue

    if new_files:
        file_components = [
            dmc.Paper([
                dmc.Group([
                    DashIconify(icon="tabler:file-spreadsheet", width=24, color="green"),
                    dmc.Stack([
                        dmc.Text(file_info['name'], fw=500, size="sm"),
                        dmc.Group([
                            dmc.Badge(f"{file_info['rows']} rows", color="blue", variant="light", size="xs"),
                            dmc.Badge(f"{file_info['columns']} cols", color="cyan", variant="light", size="xs"),
                            dmc.Badge(f"{file_info['size']/1024:.1f} KB", color="gray", variant="light", size="xs"),
                        ], gap="xs")
                    ], gap="xs", flex=1),
                    dmc.ActionIcon(
                        DashIconify(icon="tabler:x", width=16),
                        id={'type': 'remove-file-btn', 'index': file_info['name']},
                        color='red', variant="light", size="sm"
                    )
                ], justify="space-between", align="center")
            ], p="md", radius="md", withBorder=True, className="mb-2")
            for file_info in new_files
        ]
        status_message = dmc.Alert(
            title="Files Ready",
            children=f"Successfully loaded {len(new_files)} CSV file{'s' if len(new_files) != 1 else ''}",
            icon=DashIconify(icon="tabler:check"),
            color="green"
        )
    else:
        file_components = []
        status_message = ""

    return new_files, file_components, status_message, len(new_files) == 0


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
    if not n_clicks or not any(n_clicks) or not stored_files:
        return stored_files or [], no_update, no_update, no_update, no_update

    ctx = callback_context
    if not ctx.triggered:
        return stored_files or [], no_update, no_update, no_update, no_update

    triggered_id = ctx.triggered[0]['prop_id']
    filename_to_remove = None
    try:
        import json
        comp_id_str = triggered_id.rsplit('.', 1)[0]
        comp_id = json.loads(comp_id_str)
        filename_to_remove = comp_id.get('index')
    except Exception:
        return stored_files or [], no_update, no_update, no_update, no_update

    if not filename_to_remove:
        return stored_files or [], no_update, no_update, no_update, no_update

    updated_files = [f for f in stored_files if f['name'] != filename_to_remove]

    if updated_files:
        file_components = [
            dmc.Paper([
                dmc.Group([
                    DashIconify(icon="tabler:file-spreadsheet", width=24, color="green"),
                    dmc.Stack([
                        dmc.Text(file_info['name'], fw=500, size="sm"),
                        dmc.Group([
                            dmc.Badge(f"{file_info['rows']} rows", color="blue", variant="light", size="xs"),
                            dmc.Badge(f"{file_info['columns']} cols", color="cyan", variant="light", size="xs"),
                            dmc.Badge(f"{file_info['size']/1024:.1f} KB", color="gray", variant="light", size="xs")
                        ], gap="xs")
                    ], gap="xs", flex=1),
                    dmc.ActionIcon(
                        DashIconify(icon="tabler:x", width=16),
                        id={'type': 'remove-file-btn', 'index': file_info['name']},
                        color='red', variant="light", size="sm"
                    )
                ], justify="space-between", align="center")
            ], p="md", radius="md", withBorder=True, className="mb-2")
            for file_info in updated_files
        ]
        status = dmc.Alert(
            title="Files Ready",
            children=f"Successfully loaded {len(updated_files)} CSV file{'s' if len(updated_files) != 1 else ''}",
            icon=DashIconify(icon="tabler:check"),
            color="green"
        )
    else:
        file_components = []
        status = ""

    # Recreate upload to allow re-upload same filename
    new_upload = dcc.Upload(
        id='csv-upload',
        children=dmc.Stack([
            dmc.Center([DashIconify(icon="tabler:cloud-upload", width=48, height=48, color="var(--mantine-color-blue-6)")]),
            dmc.Text('Drag and Drop CSV Files', size="md", fw=500, ta="center"),
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

    return updated_files, file_components, status, len(updated_files) == 0, new_upload


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
    Input('reset-btn-csv-rtu-output', 'n_clicks'),
    prevent_initial_call=True
)
def handle_directory_selection(browse_clicks, reset_clicks):
    """Handle directory selection and reset for CSV to RTU output directory."""
    ctx = callback_context
    if not ctx.triggered:
        return "", "", {'path': ''}

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'reset-btn-csv-rtu-output':
        return "", "", {'path': ''}

    elif trigger_id == 'browse-btn-csv-rtu-output':
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()  # Hide the main window
            root.lift()      # Bring to front
            root.attributes("-topmost", True)

            directory = filedialog.askdirectory(
                title="Select Output Directory for RTU Files")
            root.destroy()

            if directory:
                status = dmc.Alert(
                    title="Success",
                    children=f"Directory selected: {os.path.basename(directory)}",
                    icon=DashIconify(icon="tabler:check"),
                    color="green",
                    withCloseButton=False
                )

                return directory, status, {'path': directory}
            else:
                return "", "", {'path': ''}

        except Exception as e:
            status = dmc.Alert(
                title="Error",
                children=f"Error selecting directory: {str(e)}",
                icon=DashIconify(icon="tabler:alert-circle"),
                color="red",
                withCloseButton=False
            )

            return "", status, {'path': ''}

    return "", "", {'path': ''}


# RTU conversion callback - matches LDUTC pattern
@callback(
    [Output('csv-processing-store', 'data'),
     Output('rtu-processing-status', 'children'),
     Output('write-rtu-content', 'children')],
    Input('write-rtu-btn', 'n_clicks'),
    [State('csv-files-store', 'data'),
     State('directory-store-csv-rtu-output', 'data')],
    prevent_initial_call=True
)
def write_rtu_data(n_clicks, csv_files, output_dir_data):
    """Convert CSV files to RTU format - mirrors LDUTC logic"""
    if not n_clicks or not csv_files:
        # Initial state - idle button
        idle_button = dmc.Button([
            DashIconify(icon="tabler:file-export", width=20),
            "Write RTU Data"
        ], id='write-rtu-btn', size="lg", disabled=len(csv_files or []) == 0, className="px-4", variant="filled")
        
        return {'status': 'idle'}, "", idle_button

    # Get output directory with fallback
    output_dir = output_dir_data.get('path', '') if output_dir_data else ''
    if not output_dir or output_dir.strip() == '':
        output_dir = os.path.join(os.getcwd(), 'RTU_Output')

    # Ensure output directory exists
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        error_status = dmc.Alert(
            title="Output Directory Error",
            children=[
                f"Could not create output directory '{output_dir}': {str(e)}",
                html.Br(),
                "Please check the directory path and permissions."
            ],
            icon=DashIconify(icon="tabler:alert-circle"),
            color="red"
        )
        
        # Error button state
        error_button = dmc.Button([
            DashIconify(icon="tabler:file-export", width=20),
            "Write RTU Data"
        ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
        
        return {'status': 'error', 'message': str(e)}, error_status, error_button

    # Show processing status with loading button
    processing_status = dmc.Alert(
        title="Processing",
        children=f"Converting {len(csv_files)} CSV files to RTU format...",
        icon=DashIconify(icon="tabler:loader"),
        color="blue"
    )
    
    # Processing button state
    processing_button = dmc.Button([
        DashIconify(icon="tabler:loader", width=20),
        "Processing..."
    ], id='write-rtu-btn', size="lg", disabled=True, className="px-4", loading=True, variant="filled")

    # First return processing state immediately
    # Note: This approach shows loading but doesn't actually process yet
    # We need to use a different pattern for true async processing
    
    # Initialize temp files list for cleanup
    temp_files = []
    
    try:
        # Brief delay to show processing state
        import time
        time.sleep(0.1)  # Small delay to ensure UI updates
        
        # Create temp directory for uploaded files
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp(prefix="csv_upload_")
        csv_file_paths = []
        
        # Save uploaded files to temporary location
        for file_info in csv_files:
            try:
                # Decode file content
                content_type, content_string = file_info['content'].split(',')
                decoded = base64.b64decode(content_string)
                csv_content = decoded.decode('utf-8')
                
                # Save to temp file
                temp_file_path = os.path.join(temp_dir, file_info['name'])
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(csv_content)
                
                csv_file_paths.append(temp_file_path)
                temp_files.append(temp_file_path)
                
            except Exception as e:
                continue  # Skip problematic files
        
        if not csv_file_paths:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            error_status = dmc.Alert(
                title="Error",
                children="No valid CSV files found to convert",
                icon=DashIconify(icon="tabler:alert-circle"),
                color="red"
            )
            
            # Error button state
            error_button = dmc.Button([
                DashIconify(icon="tabler:file-export", width=20),
                "Write RTU Data"
            ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
            
            return {'status': 'error'}, error_status, error_button
        
        # Convert files using the service
        result = csv_rtu_service.convert_to_rtu(csv_file_paths, output_dir)
        
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        if result['success']:
            success_status = dmc.Alert(
                title="Conversion Complete",
                children=[
                    f"Successfully converted {result['successful_conversions']} of {result['total_files']} files",
                    html.Br(),
                    f"Output directory: {output_dir}"
                ],
                icon=DashIconify(icon="tabler:check"),
                color="green"
            )
            
            # Success button state - reset to normal
            success_button = dmc.Button([
                DashIconify(icon="tabler:file-export", width=20),
                "Write RTU Data"
            ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
            
            return {'status': 'completed', 'result': result}, success_status, success_button
        else:
            error_status = dmc.Alert(
                title="Conversion Failed",
                children=result.get('error', 'An error occurred during conversion'),
                icon=DashIconify(icon="tabler:alert-circle"),
                color="red"
            )
            
            # Error button state
            error_button = dmc.Button([
                DashIconify(icon="tabler:file-export", width=20),
                "Write RTU Data"
            ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
            
            return {'status': 'error', 'result': result}, error_status, error_button

    except Exception as e:
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
                
        error_status = dmc.Alert(
            title="Unexpected Error",
            children=f"An unexpected error occurred: {str(e)}",
            icon=DashIconify(icon="tabler:alert-circle"),
            color="red"
        )
        
        # Error button state
        error_button = dmc.Button([
            DashIconify(icon="tabler:file-export", width=20),
            "Write RTU Data"
        ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
        
        return {'status': 'error', 'error': str(e)}, error_status, error_button
