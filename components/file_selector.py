"""
File Selector Component for DMC application.
Reusable file selection component with browse functionality.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, callback, callback_context
from components.bootstrap_icon import BootstrapIcon
import os
from logging_config import get_logger

logger = get_logger(__name__)


def create_file_selector(
    component_id: str,
    title: str = "Select File",
    placeholder: str = "Select file...",
    browse_button_text: str = "Browse",
    file_types: str = "All Files (*.*)"
) -> tuple:
    """
    Create a file selector component with browse functionality.

    Args:
        component_id: Unique identifier for this component instance
        title: Title for the card header
        placeholder: Placeholder text for the input field
        browse_button_text: Text for the browse button (used for accessibility)
        file_types: File types filter for the dialog

    Returns:
        tuple: (component, store_ids) where component is the UI element and store_ids contains the IDs
    """

    # Create unique IDs for this instance
    input_id = f'file-input-{component_id}'
    browse_id = f'browse-btn-{component_id}'
    status_id = f'file-status-{component_id}'
    store_id = f'file-store-{component_id}'

    # File selection card using DMC components
    component = dmc.Paper([
        dmc.Stack([
            # Header
            dmc.Group([
                BootstrapIcon(icon="file-earmark", width=20),
                dmc.Text(title, fw=500, size="md")
            ], gap="xs"),

            # Input field with browse button in one row
            dmc.Group([
                dmc.TextInput(
                    id=input_id,
                    placeholder=placeholder,
                    value='',
                    readOnly=True,
                    leftSection=BootstrapIcon(
                        icon="file-earmark-text", width=16),
                    size="md",
                    style={"flex": 1}
                ),
                dmc.Button(
                    BootstrapIcon(icon="search", width=16),
                    id=browse_id,
                    variant="outline",
                    size="md"
                )
            ], gap="xs", style={"alignItems": "end"}),

            # Status display
            html.Div(
                id=status_id,
                style={'minHeight': '20px'}
            )
        ], gap="md", p="md")
    ], shadow="sm", radius="md", withBorder=True)

    # Return the component and the store IDs for external callback creation
    store_ids = {
        'input': input_id,
        'browse': browse_id,
        'status': status_id,
        'store': store_id,
        'file_types': file_types
    }

    return component, store_ids


def create_file_selector_callback(store_ids: dict, dialog_title: str = "Select File"):
    """
    Create the callback function for handling file selection.
    This needs to be called by the page that uses the file selector.

    Args:
        store_ids: Dictionary containing the component IDs
        dialog_title: Title for the file dialog

    Returns:
        The callback function
    """

    @callback(
        [Output(store_ids['input'], 'value'),
         Output(store_ids['status'], 'children'),
         Output(store_ids['store'], 'data')],
        [Input(store_ids['browse'], 'n_clicks')],
        prevent_initial_call=True,
        allow_duplicate=True
    )
    def handle_file_selection(browse_clicks):
        """Handle file selection."""
        ctx = callback_context
        if not ctx.triggered:
            return "", "", {'path': ''}

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == store_ids['browse']:
            try:
                import tkinter as tk
                from tkinter import filedialog

                root = tk.Tk()
                root.withdraw()  # Hide the main window
                root.lift()      # Bring to front
                root.attributes("-topmost", True)

                # Use file dialog instead of directory dialog
                # Parse file types - handle formats like "RTU Files (*.dt)"
                file_types_str = store_ids['file_types']
                if '(' in file_types_str and ')' in file_types_str:
                    description = file_types_str.split('(')[0].strip()
                    pattern = file_types_str.split(
                        '(')[1].replace(')', '').strip()
                    filetypes = [(description, pattern)]
                else:
                    filetypes = [("All Files", "*.*")]

                file_path = filedialog.askopenfilename(
                    title=dialog_title,
                    filetypes=filetypes
                )
                root.destroy()

                if file_path:
                    # Show just the filename in status
                    filename = os.path.basename(file_path)
                    status = dmc.Text(
                        f"Selected: {filename}", size="sm", c="green")
                    return file_path, status, {'path': file_path}
                else:
                    return "", "", {'path': ''}

            except Exception as e:
                logger.error(f"Error selecting file: {str(e)}")
                error_status = dmc.Text(f"Error: {str(e)}", size="sm", c="red")
                return "", error_status, {'path': ''}

        return "", "", {'path': ''}

    return handle_file_selection
