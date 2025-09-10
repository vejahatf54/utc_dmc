"""
Replay File Poke Extractor page component for DMC application.
Extracts poke statements from replay files and generates .inc files.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context, dcc, ALL, no_update
from dash.exceptions import PreventUpdate
from components.bootstrap_icon import BootstrapIcon
import base64
import io
import os
from typing import List, Dict, Any
from datetime import datetime
from components.directory_selector import create_directory_selector, create_directory_selector_callback
from services.replay_file_poke_service import UtcReplayFilePokeExtractorService
import tempfile
from logging_config import get_logger

# Set up logging
logger = get_logger(__name__)

# Create directory selector component for output folder
output_directory_component, output_directory_ids = create_directory_selector(
    component_id='replay-poke-output',
    title="Output Directory for .inc Files",
    placeholder="Select directory for output .inc files...",
    browse_button_text="Browse Folder"
)


def create_replay_file_poke_page():
    """Create the Replay File Poke Extractor page layout."""

    return dmc.Container([
        # Data stores
        dcc.Store(id='replay-files-store', data=[]),
    # Removed processing-store; we don't need to track status for simple re-runs
        dcc.Store(id=output_directory_ids['store'], data={'path': ''}),
        
        # Notification container for this page
        html.Div(id='replay-poke-notifications'),

        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("Replay File Poke Extractor", order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="replay-poke-help-modal-btn",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Extract poke statements from replay files and generate .inc files",
                             c="dimmed", ta="center", size="md")
                ], gap="xs")
            ]),

            # Help Modal
            dmc.Modal(
                title="Replay File Poke Extractor Help",
                id="replay-poke-help-modal",
                children=[
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="info-circle", width=20),
                                    dmc.Text("Requirements", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem("Replay files containing poke statements"),
                                    dmc.ListItem("Valid output directory selected"),
                                    dmc.ListItem("Write permissions to output folder"),
                                    dmc.ListItem("Files must contain POKE or SET commands with TIME format")
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
                                    dmc.ListItem("Upload one or more replay files"),
                                    dmc.ListItem("Select output directory for .inc files"),
                                    dmc.ListItem("Specify output filename"),
                                    dmc.ListItem("Click 'Extract Pokes' to process files"),
                                    dmc.ListItem("Unique pokes will be sorted by time and saved")
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
                                dmc.Text("Replay File Upload", fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            # Upload area
                            html.Div([
                                dcc.Upload(
                                    id='replay-file-upload',
                                    children=dmc.Stack([
                                        dmc.Center([
                                            BootstrapIcon(icon="cloud-upload", width=48, height=48, color="var(--mantine-color-blue-6)")
                                        ]),
                                        dmc.Text('Drag and Drop Replay Files', size="md", fw=500, ta="center"),
                                        dmc.Text('or click to browse', size="sm", c="dimmed", ta="center"),
                                        dmc.Text('Supported formats: .replay', size="xs", c="dimmed", ta="center")
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
                                    accept='.replay'
                                )
                            ], id='replay-upload-container'),

                            # File list display
                            html.Div(
                                id='replay-file-list',
                                style={'minHeight': '50px'}
                            ),

                            # Upload status
                            html.Div(id='replay-upload-status')

                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True)
                ], style={"flex": "1", "minWidth": "350px"}),

                # Output Configuration and Processing - Stacked in one column
                dmc.Stack([
                    # Output Directory Section
                    dmc.Paper([
                        dmc.Stack([
                            # Header with icon
                            dmc.Group([
                                BootstrapIcon(icon="folder-open", width=20),
                                dmc.Text("Output Configuration", fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            # Directory selector
                            output_directory_component,

                            # Output filename input
                            dmc.Stack([
                                dmc.Text("Output Filename", fw=500, size="sm"),
                                dmc.TextInput(
                                    id='output-filename-input',
                                    placeholder="Enter filename (without extension)",
                                    value="extracted_pokes",
                                    leftSection=BootstrapIcon(icon="file-earmark-text", width=16),
                                    description="File will be saved with .inc extension"
                                )
                            ], gap="xs")

                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True),

                    # Processing Section
                    dmc.Paper([
                        dmc.Stack([
                            # Header with icon
                            dmc.Group([
                                BootstrapIcon(icon="gear", width=20),
                                dmc.Text("Processing", fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            # (Removed processing status placeholder to avoid stale alerts)

                            # Extract button
                            dmc.Button(
                                "Extract Pokes",
                                id='extract-pokes-btn',
                                leftSection=BootstrapIcon(icon="play-circle", width=16),
                                size="md",
                                fullWidth=True,
                                disabled=True
                            ),

                            # Results display
                            html.Div(id='extraction-results')

                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True)

                ], style={"flex": "1", "minWidth": "300px"}, gap="md")

            ], gap="lg", align="flex-start", wrap="wrap")

        ], gap="md")
    ], size="xl", p="md")


# Register directory selector callbacks
create_directory_selector_callback(output_directory_ids)


# Callback for help modal
@callback(
    Output('replay-poke-help-modal', 'opened'),
    Input('replay-poke-help-modal-btn', 'n_clicks'),
    State('replay-poke-help-modal', 'opened'),
    prevent_initial_call=True
)
def toggle_help_modal(n_clicks, opened):
    return not opened


# Callback for file upload
@callback(
    [Output('replay-files-store', 'data'),
     Output('replay-file-list', 'children'),
     Output('replay-upload-status', 'children'),
     Output('extract-pokes-btn', 'disabled', allow_duplicate=True)],
    [Input('replay-file-upload', 'contents')],
    [State('replay-file-upload', 'filename'),
     State('replay-files-store', 'data'),
     State(output_directory_ids['store'], 'data'),
     State('output-filename-input', 'value')],
    prevent_initial_call=True
)
def handle_file_upload(contents, filenames, stored_files, output_dir_data, filename_value):
    if not contents:
        return stored_files, "", "", True

    try:
        # Store uploaded files with content for recreation
        uploaded_files = []
        for content, filename in zip(contents, filenames):
            # Decode file content
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)
            file_content = decoded.decode('utf-8')
            
            uploaded_files.append({
                'filename': filename,
                'content': file_content,  # Store actual content instead of temp path
                'size': len(decoded)
            })
        # Update stored files
        all_files = stored_files + uploaded_files
        # Create file list display
        file_list = dmc.Stack([
            dmc.Text("Uploaded Files:", fw=500, size="sm"),
            dmc.Stack([
                dmc.Group([
                    BootstrapIcon(icon="file-earmark-text", width=16),
                    dmc.Text(f"{file['filename']}", size="sm"),
                    dmc.Text(f"({file['size']:,} bytes)", size="xs", c="dimmed")
                ], gap="xs") for file in all_files
            ], gap="xs")
        ], gap="xs") if all_files else ""
        # Status message
        status = dmc.Alert(
            f"Successfully uploaded {len(uploaded_files)} file(s). Total: {len(all_files)} files ready for processing.",
            title="Upload Complete",
            icon=BootstrapIcon(icon="check-circle"),
            color="green"
        ) if uploaded_files else ""
        # Enable extract button only if all requirements are met
        has_files = len(all_files) > 0
        has_output_dir = bool(output_dir_data.get('path', '').strip())
        has_filename = bool(filename_value and filename_value.strip())
        button_disabled = not (has_files and has_output_dir and has_filename)
        return all_files, file_list, status, button_disabled
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        error_status = dmc.Alert(
            f"Error uploading files: {str(e)}",
            title="Upload Error",
            icon=BootstrapIcon(icon="exclamation-triangle"),
            color="red"
        )
        return stored_files, "", error_status, True


# Callback to check button state when output directory changes
@callback(
    Output('extract-pokes-btn', 'disabled', allow_duplicate=True),
    [Input(output_directory_ids['store'], 'data'),
     Input('output-filename-input', 'value')],
    [State('replay-files-store', 'data')],
    prevent_initial_call=True
)
def update_button_on_config_change(output_dir_data, filename_value, files_data):
    has_files = bool(files_data)
    has_output_dir = bool(output_dir_data.get('path', '').strip())
    has_filename = bool(filename_value and filename_value.strip())
    return not (has_files and has_output_dir and has_filename)


# Callback for extraction process
@callback(
    [Output('extraction-results', 'children'),
     Output('replay-poke-notifications', 'children'),
     Output('replay-files-store', 'data', allow_duplicate=True),
     Output('replay-file-list', 'children', allow_duplicate=True),
     Output('extract-pokes-btn', 'disabled', allow_duplicate=True)],
    [Input('extract-pokes-btn', 'n_clicks')],
    [State('replay-files-store', 'data'),
     State(output_directory_ids['store'], 'data'),
     State('output-filename-input', 'value')],
    prevent_initial_call=True
)
def extract_pokes(n_clicks, files_data, output_dir_data, filename):
    # Allow every click (n_clicks increments) to run extraction; block only if no click
    if not n_clicks:
        raise PreventUpdate

    try:
        # Validate inputs
        if not files_data:
            raise ValueError("No files uploaded")
        
        output_path = output_dir_data.get('path', '').strip()
        if not output_path:
            raise ValueError("Please select an output directory")
        
        if not filename or not filename.strip():
            raise ValueError("Please enter an output filename")

        # Create fresh temp files from stored content each time
        temp_file_paths = []
        for file_data in files_data:
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f"_{file_data['filename']}", encoding='utf-8')
            temp_file.write(file_data['content'])
            temp_file.close()
            temp_file_paths.append(temp_file.name)

        # Initialize service and process files
        service = UtcReplayFilePokeExtractorService()
        service.process_replay_files(temp_file_paths)
        
        # Save to output file
        output_filename = filename.strip()
        if not output_filename.endswith('.inc'):
            output_filename += '.inc'
        
        output_file_path = os.path.join(output_path, output_filename)
        service.save_to_file(output_file_path)
        
        # Get results
        poke_statements = service.get_poke_statements()
        
        # Create results display (no Alert to avoid persistent green block)
        results = dmc.Stack([
            dmc.Group([
                BootstrapIcon(icon="check-circle", width=16),
                dmc.Text(f"Extracted {len(poke_statements)} unique poke statements", fw=500, size="sm")
            ], gap="xs"),
            dmc.Group([
                dmc.Text("Output file:", fw=500, size="sm"),
                dmc.Code(output_file_path, block=False)
            ], gap="xs")
        ], gap="sm")

        # Success notification
        notification = dmc.Notification(
            title="Extraction Complete",
            message=f"Successfully extracted {len(poke_statements)} poke statements to {output_filename}",
            icon=BootstrapIcon(icon="check-circle"),
            color="green",
            autoClose=5000,
            action="show"
        )

        # Clean up the fresh temp files we just created
        for temp_path in temp_file_paths:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                # Silently ignore cleanup errors
                pass

        # After extraction, keep files and enable button for re-run
        # Recreate file list display
        file_list = dmc.Stack([
            dmc.Text("Uploaded Files:", fw=500, size="sm"),
            dmc.Stack([
                dmc.Group([
                    BootstrapIcon(icon="file-earmark-text", width=16),
                    dmc.Text(f"{file_data['filename']}", size="sm"),
                    dmc.Text(f"({file_data['size']:,} bytes)", size="xs", c="dimmed")
                ], gap="xs") for file_data in files_data
            ], gap="xs")
        ], gap="xs") if files_data else ""
        
        return (
            results,
            notification,
            files_data,  # keep the files for potential re-run
            file_list, # keep file list UI
            False # enable extract button for re-run
        )

    except Exception as e:
        logger.error(f"Error during poke extraction: {e}")
        error_notification = dmc.Notification(
            title="Extraction Error",
            message=str(e),
            icon=BootstrapIcon(icon="exclamation-triangle"),
            color="red",
            autoClose=8000,
            action="show"
        )
        return (
            dmc.Text(f"Error: {str(e)}", c="red", size="sm"),
            error_notification,
            files_data,  # keep files for retry
            "", # clear file list UI on error  
            False # enable extract button for retry
        )
