"""
Replace Text page component for DMC application (Refactored Version).
Follows SOLID principles with proper separation of concerns and dependency injection.
Maintains the exact same UI layout and design as the original.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context, dcc, ALL, no_update
from dash.exceptions import PreventUpdate
from components.bootstrap_icon import BootstrapIcon
from typing import List, Dict, Any
from datetime import datetime
from components.directory_selector import create_directory_selector, create_directory_selector_callback
from core.dependency_injection import DIContainer
from controllers.text_replacement_controller import TextReplacementUIResponseFormatter
from logging_config import get_logger

# Set up logging
logger = get_logger(__name__)

# Get DI container instance
container = DIContainer.get_instance()

# Create directory selector component for target folder
target_directory_component, target_directory_ids = create_directory_selector(
    component_id='replace-text-folder-v2',
    title="Target Folder (files to process)",
    placeholder="Select folder containing files to process...",
    browse_button_text="Browse Folder"
)


def create_replace_text_page():
    """Create the Replace Text page layout (V2 - SOLID principles version)."""

    return dmc.Container([
        # Data stores
        dcc.Store(id='replace-text-csv-file-store-v2', data={}),
        dcc.Store(id=target_directory_ids['store'], data={'path': ''}),

        # Notification container for this page
        html.Div(id='replace-text-notifications-v2'),

        # Header Section - EXACT SAME as original
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("Replace Text in Files",
                                  order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(
                                icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="replace-text-help-modal-btn-v2",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Replace strings in files based on CSV substitution mappings",
                             c="dimmed", ta="center", size="md")
                ], gap="xs")
            ]),

            # Help Modal - EXACT SAME as original
            dmc.Modal(
                title="Replace Text Help",
                id="replace-text-help-modal-v2",
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
                                        "CSV file with substitution mappings (old text, new text)"),
                                    dmc.ListItem(
                                        "Target folder containing files to process"),
                                    dmc.ListItem(
                                        "File extensions to filter (comma separated)"),
                                    dmc.ListItem(
                                        "Read and write permissions to target folder"),
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
                                    dmc.Text(
                                        "CSV format with two columns:", size="sm", fw=500),
                                    dmc.Text(
                                        "• First column: Text to replace (old text)", size="xs", c="dimmed"),
                                    dmc.Text(
                                        "• Second column: Replacement text (new text)", size="xs", c="dimmed"),
                                    dmc.Text("• No headers required",
                                             size="xs", c="dimmed"),
                                    dmc.Space(h="xs"),
                                    dmc.Text("Example:", size="sm", fw=500),
                                    dmc.Code(
                                        "old_string1,new_string1\nold_string2,new_string2", block=True)
                                ])
                            ])
                        ], span=6)
                    ])
                ],
                opened=False,
                size="lg"
            ),

            dmc.Space(h="md"),

            # Main Content Layout - EXACT SAME as original
            dmc.Grid([
                # Left offset column (1 column)
                dmc.GridCol([], span=1),

                # Left side - File Selection and Configuration (5 columns)
                dmc.GridCol([
                    dmc.Stack([
                        # CSV Substitution File Upload Section - EXACT SAME as original
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(
                                        icon="file-earmark-text", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("CSV Substitution File",
                                             fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # Upload area for CSV file
                                html.Div([
                                    dcc.Upload(
                                        id='replace-text-csv-upload-v2',
                                        children=dmc.Stack([
                                            dmc.Center([
                                                BootstrapIcon(
                                                    icon="file-earmark-text", width=36, height=36, color="var(--mantine-color-green-6)")
                                            ]),
                                            dmc.Text(
                                                'Drop CSV File', size="sm", fw=500, ta="center"),
                                            dmc.Text(
                                                '(Two columns: old text, new text)', size="xs", c="dimmed", ta="center")
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
                                    id='replace-text-csv-status-v2',
                                    style={'minHeight': '20px'}
                                ),

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                        # Target Folder Selection - EXACT SAME as original
                        target_directory_component,

                    ], gap="md")
                ], span=5),

                # Right side - Configuration and Actions (5 columns) - EXACT SAME as original
                dmc.GridCol([
                    dmc.Stack([
                        # File Extensions Configuration
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="funnel", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("File Extension Filter",
                                             fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                dmc.Stack([
                                    dmc.Text("File Extensions",
                                             size="sm", fw=500),
                                    dmc.TextInput(
                                        id="replace-text-extensions-v2",
                                        placeholder="txt,py,js,html,css",
                                        description="Comma-separated list of file extensions (no dots or asterisks needed)",
                                        style={"width": "100%"},
                                        size="md"
                                    )
                                ], gap="xs"),

                                dmc.Space(h="sm"),

                                # Match case option (similar to C# MatchChkBox)
                                dmc.Checkbox(
                                    id="replace-text-match-case-v2",
                                    label="Match case (case-sensitive replacement)",
                                    checked=True,
                                    size="sm"
                                )

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                        # Processing Controls - EXACT SAME as original
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="gear", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Processing Controls",
                                             fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # Action button - only Replace button, no Cancel
                                dmc.Button(
                                    [
                                        BootstrapIcon(
                                            icon="arrow-repeat", width=16),
                                        dmc.Space(w="xs"),
                                        "Replace Text"
                                    ],
                                    id='replace-text-start-btn-v2',
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


# Callback for help modal - EXACT SAME as original
@callback(
    Output('replace-text-help-modal-v2', 'opened'),
    [Input('replace-text-help-modal-btn-v2', 'n_clicks')],
    [State('replace-text-help-modal-v2', 'opened')],
    prevent_initial_call=True
)
def toggle_help_modal_v2(n_clicks, opened):
    """Toggle the help modal visibility."""
    if n_clicks:
        return not opened
    return opened


# Callback for CSV file upload - Refactored to use controller
@callback(
    [Output('replace-text-csv-file-store-v2', 'data'),
     Output('replace-text-csv-status-v2', 'children')],
    [Input('replace-text-csv-upload-v2', 'contents')],
    [State('replace-text-csv-upload-v2', 'filename')],
    prevent_initial_call=True
)
def handle_csv_upload_v2(contents, filename):
    """Handle CSV file upload and validation using controller."""
    if contents is None:
        return {}, ""

    try:
        # Get controller from DI container
        controller = container.resolve("text_replacement_controller")

        # Use controller to handle upload
        result = controller.handle_csv_upload(contents, filename)

        # Format response for UI
        csv_data, status_component = TextReplacementUIResponseFormatter.format_csv_upload_response(
            result)

        # Create UI components based on result
        if status_component['type'] == 'success':
            ui_component = dmc.Alert(
                dmc.Group([
                    BootstrapIcon(icon="file-earmark-check", width=16,
                                  color="var(--mantine-color-green-6)"),
                    dmc.Text(
                        f"{status_component['filename']} ({status_component['substitution_count']} substitutions)", size="sm")
                ], gap="xs"),
                title=status_component['title'],
                color="green",
                withCloseButton=False
            )
        else:
            ui_component = dmc.Alert(
                status_component['message'],
                title=status_component['title'],
                color="red",
                withCloseButton=False
            )

        return csv_data, ui_component

    except Exception as e:
        logger.error(f"Error in CSV upload callback: {str(e)}")
        error_alert = dmc.Alert(
            f"Unexpected error: {str(e)}",
            title="System Error",
            color="red",
            withCloseButton=False
        )
        return {}, error_alert


# Directory selector callback - EXACT SAME as original
create_directory_selector_callback(target_directory_ids)


# Main processing callback - Refactored to use controller and service
@callback(
    [Output('replace-text-notifications-v2', 'children')],
    [Input('replace-text-start-btn-v2', 'n_clicks')],
    [State(target_directory_ids['store'], 'data'),
     State('replace-text-csv-file-store-v2', 'data'),
     State('replace-text-extensions-v2', 'value'),
     State('replace-text-match-case-v2', 'checked')],
    prevent_initial_call=True
)
def start_replace_text_processing_v2(n_clicks, folder_data, csv_data, extensions_value, match_case):
    """Start the text replacement process using controller and service."""
    if not n_clicks:
        raise PreventUpdate

    try:
        # Get controller from DI container
        controller = container.resolve("text_replacement_controller")

        # Extract data
        directory = folder_data.get('path', '')
        extensions = extensions_value or ''

        # Use controller to handle the request
        result = controller.handle_text_replacement(
            directory, csv_data, extensions, match_case)

        # Format response for UI
        notification_data = TextReplacementUIResponseFormatter.format_replacement_response(
            result)

        # Create notification component
        if notification_data['type'] == 'success':
            notification = dmc.Notification(
                title=notification_data['title'],
                message=notification_data['message'],
                color="green",
                autoClose=5000,
                action="show"
            )
        elif notification_data['type'] == 'warning':
            notification = dmc.Notification(
                title=notification_data['title'],
                message=notification_data['message'],
                color="yellow",
                autoClose=7000,
                action="show"
            )
        else:
            notification = dmc.Notification(
                title=notification_data['title'],
                message=notification_data['message'],
                color="red",
                autoClose=5000,
                action="show"
            )

        return [notification]

    except Exception as e:
        logger.error(
            f"Error in text replacement callback: {str(e)}", exc_info=True)
        error_notification = dmc.Notification(
            title="System Error",
            message=f"Unexpected error: {str(e)}",
            color="red",
            autoClose=5000,
            action="show"
        )
        return [error_notification]
