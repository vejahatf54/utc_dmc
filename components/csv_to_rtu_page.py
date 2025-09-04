"""
CSV to RTU Converter page component for DMC application.
Uses DMC components for file upload, directory selection, and conversion.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context, dcc, ALL, no_update
from components.bootstrap_icon import BootstrapIcon
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
                            BootstrapIcon(icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
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
                                    BootstrapIcon(icon="info-circle", width=20),
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
                                    BootstrapIcon(icon="lightbulb", width=20),
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
                                            BootstrapIcon(icon="cloud-upload", width=48, height=48, color="var(--mantine-color-blue-6)")
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
                                    BootstrapIcon(icon="arrow-repeat", width=20),
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
                                                BootstrapIcon(icon="download", width=20),
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


# Initialize the service
csv_rtu_service = CsvToRtuService()


# Helper function to create file display components
def create_file_components(file_list):
    """Create file display components with pattern-matching IDs for removal."""
    if not file_list:
        return [
            dmc.Alert([
                dmc.Group([
                    BootstrapIcon(icon="info-circle", width=20),
                    dmc.Text("No files selected. Upload CSV files to get started.", size="sm")
                ], gap="xs")
            ], color="blue", variant="light", radius="md")
        ]
    
    components = []
    for file_info in file_list:
        component = dmc.Paper([
            dmc.Group([
                BootstrapIcon(icon="file-earmark-spreadsheet", width=24, color="green"),
                dmc.Stack([
                    dmc.Text(file_info['name'], fw=500, size="sm"),
                    dmc.Group([
                        dmc.Badge(f"{file_info['rows']} rows", color="blue", variant="light", size="xs"),
                        dmc.Badge(f"{file_info['columns']} cols", color="cyan", variant="light", size="xs"),
                        dmc.Badge(f"{file_info['size']/1024:.1f} KB", color="gray", variant="light", size="xs"),
                    ], gap="xs")
                ], gap="xs", flex=1),
                dmc.ActionIcon(
                    BootstrapIcon(icon="x", width=16),
                    id={'type': 'remove-file-btn', 'index': file_info['name']},
                    color='red', variant="light", size="sm"
                )
            ], justify="space-between", align="center")
        ], p="md", radius="md", withBorder=True, className="mb-2")
        
        components.append(component)
    
    return components


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
    # If there's no new upload interaction, keep displaying already stored files
    if not contents:
        existing_files = stored_files or []
        existing_components = create_file_components(existing_files)
        return existing_files, existing_components, "", len(existing_files) == 0

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
        file_components = create_file_components(new_files)
        status_message = ""
    else:
        file_components = create_file_components([])
        status_message = ""

    return new_files, file_components, status_message, len(new_files) == 0


# Pattern-matching callback for file removal using proper Dash syntax
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
    """Remove a specific CSV file using pattern-matching callbacks."""
    
    print(f"DEBUG: remove_csv_file called with n_clicks={n_clicks}, stored_files count={len(stored_files) if stored_files else 0}")
    
    # Check if any button was actually clicked
    if not n_clicks or not any(n_clicks) or not stored_files:
        print("DEBUG: Early return - no clicks or no files")
        return no_update, no_update, no_update, no_update, no_update

    # Get callback context to identify which button was clicked
    ctx = callback_context
    if not ctx.triggered:
        print("DEBUG: No callback context triggered")
        return no_update, no_update, no_update, no_update, no_update

    print(f"DEBUG: ctx.triggered = {ctx.triggered}")
    
    # Parse the triggered component ID to get the filename
    triggered_prop_id = ctx.triggered[0]['prop_id']
    print(f"DEBUG: triggered_prop_id = {triggered_prop_id}")
    
    # Extract the component ID part (before the .n_clicks) - use rsplit to get the last .n_clicks
    component_id_str = triggered_prop_id.rsplit('.n_clicks', 1)[0]
    print(f"DEBUG: component_id_str = {component_id_str}")
    
    try:
        import json
        component_id = json.loads(component_id_str)
        filename_to_remove = component_id['index']
        print(f"DEBUG: filename_to_remove = {filename_to_remove}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"DEBUG: Error parsing component ID: {e}")
        return no_update, no_update, no_update, no_update, no_update

    # Filter out the file to remove
    updated_files = [f for f in stored_files if f.get('name') != filename_to_remove]
    print(f"DEBUG: updated_files count = {len(updated_files)}")
    
    # Create new file components
    file_components = create_file_components(updated_files)
    
    # Recreate upload component to allow re-uploading same filename
    new_upload = dcc.Upload(
        id='csv-upload',
        children=dmc.Stack([
            dmc.Center([BootstrapIcon(icon="cloud-upload", width=48, height=48, color="var(--mantine-color-blue-6)")]),
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
    
    print(f"DEBUG: Returning updated files and components")
    return updated_files, file_components, "", len(updated_files) == 0, new_upload


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
                return directory, "", {'path': directory}
            else:
                return "", "", {'path': ''}

        except Exception as e:
            status = dmc.Alert(
                title="Error",
                children=f"Error selecting directory: {str(e)}",
                icon=BootstrapIcon(icon="exclamation-circle"),
                color="red",
                withCloseButton=False
            )

            return "", status, {'path': ''}

    return "", "", {'path': ''}


# RTU conversion callback - matches LDUTC pattern
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
    """Convert CSV files to RTU format - mirrors LDUTC logic"""
    if not n_clicks or not csv_files:
        # Initial state - idle button
        idle_button = dmc.Button([
            BootstrapIcon(icon="download", width=20),
            "Write RTU Data"
        ], id='write-rtu-btn', size="lg", disabled=len(csv_files or []) == 0, className="px-4", variant="filled")
        
        return {'status': 'idle'}, "", idle_button, no_update

    # Get output directory with fallback
    output_dir = output_dir_data.get('path', '') if output_dir_data else ''
    if not output_dir or output_dir.strip() == '':
        output_dir = os.path.join(os.getcwd(), 'RTU_Output')

    # Ensure output directory exists
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        error_notification = [{
            "title": "Output Directory Error",
            "message": f"Could not create output directory '{output_dir}': {str(e)}. Please check the directory path and permissions.",
            "color": "red",
            "autoClose": 5000,
            "action": "show"
        }]
        
        # Error button state
        error_button = dmc.Button([
            BootstrapIcon(icon="download", width=20),
            "Write RTU Data"
        ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
        
        return {'status': 'error', 'message': str(e)}, "", error_button, error_notification

    # Initialize temp files list for cleanup
    temp_files = []
    
    try:
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
            error_notification = [{
                "title": "Error",
                "message": "No valid CSV files found to convert",
                "color": "red",
                "autoClose": 5000,
                "action": "show"
            }]
            
            # Error button state
            error_button = dmc.Button([
                BootstrapIcon(icon="download", width=20),
                "Write RTU Data"
            ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
            
            return {'status': 'error'}, "", error_button, error_notification
        
        # Convert files using the service
        result = csv_rtu_service.convert_to_rtu(csv_file_paths, output_dir)
        
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        if result['success']:
            success_notification = [{
                "title": "Conversion Complete",
                "message": f"Successfully converted {result['successful_conversions']} of {result['total_files']} files. Output directory: {output_dir}",
                "color": "green",
                "autoClose": 7000,
                "action": "show"
            }]
            
            # Success button state - reset to normal
            success_button = dmc.Button([
                BootstrapIcon(icon="download", width=20),
                "Write RTU Data"
            ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
            
            return {'status': 'completed', 'result': result}, "", success_button, success_notification
        else:
            error_notification = [{
                "title": "Conversion Failed",
                "message": result.get('error', 'An error occurred during conversion'),
                "color": "red",
                "autoClose": 5000,
                "action": "show"
            }]
            
            # Error button state
            error_button = dmc.Button([
                BootstrapIcon(icon="download", width=20),
                "Write RTU Data"
            ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
            
            return {'status': 'error', 'result': result}, "", error_button, error_notification

    except Exception as e:
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
                
        error_notification = [{
            "title": "Unexpected Error",
            "message": f"An unexpected error occurred: {str(e)}",
            "color": "red",
            "autoClose": 5000,
            "action": "show"
        }]
        
        # Error button state
        error_button = dmc.Button([
            BootstrapIcon(icon="download", width=20),
            "Write RTU Data"
        ], id='write-rtu-btn', size="lg", disabled=False, className="px-4", variant="filled")
        
        return {'status': 'error', 'error': str(e)}, "", error_button, error_notification
