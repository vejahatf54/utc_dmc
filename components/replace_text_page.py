"""
Replace Text page component for DMC application.
Replaces text in files based on CSV substitution mappings with file extension filtering.
Simple and fast synchronous operation like the original C# version.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context, dcc, ALL, no_update
from dash.exceptions import PreventUpdate
from components.bootstrap_icon import BootstrapIcon
import base64
import io
import pandas as pd
import os
import logging
from typing import List, Dict, Any
from datetime import datetime
from components.directory_selector import create_directory_selector, create_directory_selector_callback
from services.replace_text_service import ReplaceTextService
import tempfile

# Set up logging
logger = logging.getLogger(__name__)

# Create directory selector component for target folder
target_directory_component, target_directory_ids = create_directory_selector(
    component_id='replace-text-folder',
    title="Target Folder (files to process)",
    placeholder="Select folder containing files to process...",
    browse_button_text="Browse Folder"
)


def create_replace_text_page():
    """Create the Replace Text page layout."""

    return dmc.Container([
        # Data stores
        dcc.Store(id='replace-text-csv-file-store', data={}),
        dcc.Store(id=target_directory_ids['store'], data={'path': ''}),
        
        # Notification container for this page
        html.Div(id='replace-text-notifications'),

        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("Replace Text in Files", order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="replace-text-help-modal-btn",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Replace strings in files based on CSV substitution mappings",
                             c="dimmed", ta="center", size="md")
                ], gap="xs")
            ]),

            # Help Modal
            dmc.Modal(
                title="Replace Text Help",
                id="replace-text-help-modal",
                children=[
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="info-circle", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Requirements", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem("CSV file with substitution mappings (old text, new text)"),
                                    dmc.ListItem("Target folder containing files to process"),
                                    dmc.ListItem("File extensions to filter (comma separated)"),
                                    dmc.ListItem("Read and write permissions to target folder"),
                                ], size="sm")
                            ])
                        ], span=6),
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="lightbulb", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("CSV File Format", fw=500)
                                ], gap="xs"),
                                dmc.Stack([
                                    dmc.Text("CSV format with two columns:", size="sm", fw=500),
                                    dmc.Text("• First column: Text to replace (old text)", size="xs", c="dimmed"),
                                    dmc.Text("• Second column: Replacement text (new text)", size="xs", c="dimmed"),
                                    dmc.Text("• No headers required", size="xs", c="dimmed"),
                                    dmc.Space(h="xs"),
                                    dmc.Text("Example:", size="sm", fw=500),
                                    dmc.Code("old_string1,new_string1\nold_string2,new_string2", block=True)
                                ])
                            ])
                        ], span=6)
                    ])
                ],
                opened=False,
                size="lg"
            ),

            dmc.Space(h="md"),

            # Main Content Layout
            dmc.Grid([
                # Left offset column (1 column)
                dmc.GridCol([], span=1),

                # Left side - File Selection and Configuration (5 columns)
                dmc.GridCol([
                    dmc.Stack([
                        # CSV Substitution File Upload Section
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="file-earmark-text", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("CSV Substitution File", fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # Upload area for CSV file
                                html.Div([
                                    dcc.Upload(
                                        id='replace-text-csv-upload',
                                        children=dmc.Stack([
                                            dmc.Center([
                                                BootstrapIcon(icon="file-earmark-text", width=36, height=36, color="var(--mantine-color-green-6)")
                                            ]),
                                            dmc.Text('Drop CSV File', size="sm", fw=500, ta="center"),
                                            dmc.Text('(Two columns: old text, new text)', size="xs", c="dimmed", ta="center")
                                        ], gap="xs", p="lg", align="center"),
                                        style={
                                            'width': '100%',
                                            'height': '120px',
                                            'borderWidth': '2px',
                                            'borderStyle': 'dashed',
                                            'borderRadius': '8px',
                                            'cursor': 'pointer',
                                            'display': 'flex',
                                            'alignItems': 'center',
                                            'justifyContent': 'center'
                                        },
                                        multiple=False,
                                        accept='.csv'
                                    )
                                ]),

                                # CSV file status
                                html.Div(
                                    id='replace-text-csv-status',
                                    style={'minHeight': '20px'}
                                ),

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                        # Target Folder Selection
                        target_directory_component,

                    ], gap="md")
                ], span=5),

                # Right side - Configuration and Actions (5 columns)
                dmc.GridCol([
                    dmc.Stack([
                        # File Extensions Configuration
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="funnel", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("File Extension Filter", fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                dmc.Stack([
                                    dmc.Text("File Extensions", size="sm", fw=500),
                                    dmc.TextInput(
                                        id="replace-text-extensions",
                                        placeholder="txt,py,js,html,css",
                                        description="Comma-separated list of file extensions (no dots or asterisks needed)",
                                        style={"width": "100%"},
                                        size="md"
                                    )
                                ], gap="xs"),

                                dmc.Space(h="sm"),

                                # Match case option (similar to C# MatchChkBox)
                                dmc.Checkbox(
                                    id="replace-text-match-case",
                                    label="Match case (case-sensitive replacement)",
                                    checked=True,
                                    size="sm"
                                )

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                        # Processing Controls
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="gear", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Processing Controls", fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # Action button - only Replace button, no Cancel
                                dmc.Button(
                                    [
                                        BootstrapIcon(icon="arrow-repeat", width=16),
                                        dmc.Space(w="xs"),
                                        "Replace Text"
                                    ],
                                    id='replace-text-start-btn',
                                    size="lg",
                                    variant="filled",
                                    disabled=False,
                                    fullWidth=True
                                )

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                    ], gap="md")
                ], span=5),

                # Right offset column (1 column)
                dmc.GridCol([], span=1)

            ], gutter="md", align="stretch")

        ], gap="lg", p="md")

    ], size="xl", p="md")


# Callback for help modal
@callback(
    Output('replace-text-help-modal', 'opened'),
    [Input('replace-text-help-modal-btn', 'n_clicks')],
    [State('replace-text-help-modal', 'opened')],
    prevent_initial_call=True
)
def toggle_help_modal(n_clicks, opened):
    """Toggle the help modal visibility."""
    if n_clicks:
        return not opened
    return opened


# Callback for CSV file upload
@callback(
    [Output('replace-text-csv-file-store', 'data'),
     Output('replace-text-csv-status', 'children')],
    [Input('replace-text-csv-upload', 'contents')],
    [State('replace-text-csv-upload', 'filename')],
    prevent_initial_call=True
)
def handle_csv_upload(contents, filename):
    """Handle CSV file upload and validation."""
    if contents is None:
        return {}, ""
    
    try:
        # Parse the file
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Validate it's a CSV
        if not filename.lower().endswith('.csv'):
            error_alert = dmc.Alert(
                "File must be a CSV file (.csv extension)",
                title="Invalid File Type",
                color="red",
                withCloseButton=False
            )
            return {}, error_alert
        
        # Try to read as CSV to validate format
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), header=None)
        
        if df.shape[1] < 2:
            error_alert = dmc.Alert(
                "CSV file must have at least 2 columns (old text, new text)",
                title="Invalid CSV Format",
                color="red",
                withCloseButton=False
            )
            return {}, error_alert
        
        file_info = dmc.Group([
            BootstrapIcon(icon="file-earmark-check", width=16, color="var(--mantine-color-green-6)"),
            dmc.Text(f"{filename} ({len(df)} substitutions)", size="sm")
        ], gap="xs")
        
        status_alert = dmc.Alert(
            file_info,
            title="CSV File Loaded Successfully",
            color="green",
            withCloseButton=False
        )
        
        csv_data = {
            'filename': filename,
            'content': content_string,
            'substitution_count': len(df)
        }
        
        return csv_data, status_alert
        
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        error_alert = dmc.Alert(
            f"Error reading CSV file: {str(e)}",
            title="File Processing Error",
            color="red",
            withCloseButton=False
        )
        return {}, error_alert


# Directory selector callback
create_directory_selector_callback(target_directory_ids)


# Main processing callback - Simple and fast like the C# version
@callback(
    [Output('replace-text-notifications', 'children')],
    [Input('replace-text-start-btn', 'n_clicks')],
    [State(target_directory_ids['store'], 'data'),
     State('replace-text-csv-file-store', 'data'),
     State('replace-text-extensions', 'value'),
     State('replace-text-match-case', 'checked')],
    prevent_initial_call=True
)
def start_replace_text_processing(n_clicks, folder_data, csv_data, extensions_value, match_case):
    """Start the text replacement process - synchronous and fast."""
    if not n_clicks:
        raise PreventUpdate
    
    # Validate inputs
    folder_path = folder_data.get('path', '')
    if not folder_path:
        notification = dmc.Notification(
            title="Missing Folder",
            message="Please select a target folder containing files to process",
            color="red",
            action="show"
        )
        return [notification]
    
    if not csv_data.get('content'):
        notification = dmc.Notification(
            title="Missing CSV File",
            message="Please upload a CSV file with substitution mappings",
            color="red",
            action="show"
        )
        return [notification]
    
    if not extensions_value or not extensions_value.strip():
        notification = dmc.Notification(
            title="Missing File Extensions",
            message="Please specify at least one file extension to process",
            color="red",
            action="show"
        )
        return [notification]
    
    temp_csv_path = None
    try:
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='', encoding='utf-8') as temp_csv:
            content = base64.b64decode(csv_data['content']).decode('utf-8')
            temp_csv.write(content)
            temp_csv_path = temp_csv.name
        
        # Parse file extensions - clean up any asterisks or dots
        file_extensions = []
        for ext in extensions_value.split(','):
            ext = ext.strip()
            # Remove any asterisks and dots that users might add
            ext = ext.lstrip('*').lstrip('.')
            if ext:
                file_extensions.append(ext)
        
        # Create and use ReplaceTextService - just like C# version
        service = ReplaceTextService()
        service.set_csv_file(temp_csv_path)
        service.set_folder_path(folder_path)
        service.replace_in_files(file_extensions, match_case=match_case)
        
        # Success notification
        success_notification = dmc.Notification(
            title="Completed",
            message="Text replacement completed successfully!",
            color="green",
            autoClose=5000,
            action="show"
        )
        
        return [success_notification]
            
    except Exception as e:
        logger.error(f"Text replacement error: {str(e)}", exc_info=True)
        error_notification = dmc.Notification(
            title="Processing Error",
            message=f"Error during text replacement: {str(e)}",
            color="red",
            autoClose=5000,
            action="show"
        )
        return [error_notification]
    
    finally:
        # Clean up temporary CSV file
        if temp_csv_path and os.path.exists(temp_csv_path):
            try:
                os.unlink(temp_csv_path)
            except:
                pass  # Ignore cleanup errors
