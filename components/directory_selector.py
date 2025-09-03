"""
Directory Selector Component for DMC application.
Reusable directory selection component with browse and reset functionality.
"""

import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, Input, Output, callback, callback_context
import os


def create_directory_selector(
    component_id: str,
    title: str = "Output Directory",
    placeholder: str = "Select output directory...",
    browse_button_text: str = "Browse",
    reset_button_text: str = "Reset"
) -> tuple:
    """
    Create a directory selector component with browse and reset functionality.

    Args:
        component_id: Unique identifier for this component instance
        title: Title for the card header
        placeholder: Placeholder text for the input field
        browse_button_text: Text for the browse button
        reset_button_text: Text for the reset button

    Returns:
        tuple: (component, store_ids) where component is the UI element and store_ids contains the IDs
    """

    # Create unique IDs for this instance
    input_id = f'directory-input-{component_id}'
    browse_id = f'browse-btn-{component_id}'
    reset_id = f'reset-btn-{component_id}'
    status_id = f'directory-status-{component_id}'
    store_id = f'directory-store-{component_id}'

    # Directory selection card using DMC components
    component = dmc.Paper([
        dmc.Stack([
            # Header
            dmc.Group([
                DashIconify(icon="tabler:folder", width=20),
                dmc.Text(title, fw=500, size="lg")
            ], gap="xs"),

            dmc.Divider(),

            # Input field
            dmc.TextInput(
                id=input_id,
                placeholder=placeholder,
                value='',
                readOnly=True,
                leftSection=DashIconify(icon="tabler:folder-open", width=16),
                size="md"
            ),

            # Button row
            dmc.Group([
                dmc.Button([
                    DashIconify(icon="tabler:folder-search",
                                width=16, className="me-2"),
                    browse_button_text
                ],
                    id=browse_id,
                    color='green',
                    variant="outline",
                    size="sm",
                    flex=1
                ),
                dmc.Button([
                    DashIconify(icon="tabler:refresh",
                                width=16, className="me-2"),
                    reset_button_text
                ],
                    id=reset_id,
                    color='red',
                    variant="outline",
                    size="sm",
                    flex=1
                )
            ], grow=True),

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
        'reset': reset_id,
        'status': status_id,
        'store': store_id
    }

    return component, store_ids


def create_directory_selector_callback(store_ids: dict, dialog_title: str = "Select Directory"):
    """
    Create the callback function for handling directory selection.
    This needs to be called by the page that uses the directory selector.

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
        [Input(store_ids['browse'], 'n_clicks'),
         Input(store_ids['reset'], 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_directory_selection(browse_clicks, reset_clicks):
        """Handle directory selection and reset."""
        ctx = callback_context
        if not ctx.triggered:
            return "", "", {'path': ''}

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == store_ids['reset']:
            return "", "", {'path': ''}

        elif trigger_id == store_ids['browse']:
            try:
                import tkinter as tk
                from tkinter import filedialog

                root = tk.Tk()
                root.withdraw()  # Hide the main window
                root.lift()      # Bring to front
                root.attributes("-topmost", True)

                directory = filedialog.askdirectory(title=dialog_title)
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

    return handle_directory_selection


class DirectorySelector:
    """
    Utility class for creating directory selector components.
    This provides a similar API to the LDUTC DirectorySelector.
    """

    @staticmethod
    def create_directory_selector(
        component_id: str,
        title: str = "Output Directory",
        placeholder: str = "Select output directory...",
        browse_button_text: str = "Browse",
        reset_button_text: str = "Reset"
    ) -> tuple:
        """Create a directory selector component"""
        return create_directory_selector(
            component_id=component_id,
            title=title,
            placeholder=placeholder,
            browse_button_text=browse_button_text,
            reset_button_text=reset_button_text
        )

    @staticmethod
    def get_ids(component_id: str) -> dict:
        """Get the IDs for a directory selector component"""
        return {
            'input': f'directory-input-{component_id}',
            'browse': f'browse-btn-{component_id}',
            'reset': f'reset-btn-{component_id}',
            'status': f'directory-status-{component_id}',
            'store': f'directory-store-{component_id}'
        }

    @staticmethod
    def create_callback(store_ids: dict, dialog_title: str = "Select Directory"):
        """Create the callback for handling directory selection"""
        return create_directory_selector_callback(store_ids, dialog_title)
