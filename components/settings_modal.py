"""
Settings Modal Component for DMC Application
"""

import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, Input, Output, State, callback


def create_settings_modal():
    """Create the settings modal component."""
    
    return dmc.Box([
        # Settings trigger button
        dmc.ActionIcon(
            DashIconify(icon="tabler:settings", width=24),
            id="settings-modal-button",
            variant="light",
            size="xl",
            radius="xl",
        ),
        
        # Settings modal
        dmc.Modal(
            id="settings-modal",
            size="md",
            title=dmc.Group([
                DashIconify(icon="tabler:settings", width=24),
                dmc.Text("Settings", fw=600)
            ], gap="sm"),
            children=[
                dmc.Stack([
                    # Theme Settings Section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                DashIconify(icon="tabler:palette", width=20),
                                dmc.Text("Theme Settings", fw=500, size="md")
                            ], gap="sm"),
                            dmc.Divider(size="xs"),
                            dmc.Stack([
                                dmc.Text("Theme Controls", size="sm", fw=500),
                                dmc.Text("Use the theme toggle in the top-right corner to switch between light and dark modes, or access the theme customization panel.", 
                                       size="sm", c="dimmed"),
                                dmc.Group([
                                    DashIconify(icon="radix-icons:sun", width=16, color=dmc.DEFAULT_THEME["colors"]["yellow"][6]),
                                    dmc.Text("Light Mode", size="xs", c="dimmed"),
                                    dmc.Text("•", size="xs", c="dimmed"), 
                                    DashIconify(icon="radix-icons:moon", width=16, color=dmc.DEFAULT_THEME["colors"]["gray"][6]),
                                    dmc.Text("Dark Mode", size="xs", c="dimmed"),
                                    dmc.Text("•", size="xs", c="dimmed"),
                                    DashIconify(icon="emojione:artist-palette", width=16),
                                    dmc.Text("Customize", size="xs", c="dimmed")
                                ], gap="xs", mt="sm")
                            ], gap="xs")
                        ], gap="md")
                    ], p="lg", withBorder=True, radius="md"),
                    
                    # Application Settings Section  
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                DashIconify(icon="tabler:adjustments", width=20),
                                dmc.Text("Application Settings", fw=500, size="md")
                            ], gap="sm"),
                            dmc.Divider(size="xs"),
                            dmc.Stack([
                                dmc.Group([
                                    dmc.Stack([
                                        dmc.Text("Auto-save uploads", size="sm", fw=500),
                                        dmc.Text("Automatically save uploaded files to local storage", 
                                               size="xs", c="dimmed")
                                    ], gap="xs", flex=1),
                                    dmc.Switch(
                                        id="auto-save-switch",
                                        checked=False,
                                        size="md"
                                    )
                                ], justify="space-between", align="center"),
                                
                                dmc.Group([
                                    dmc.Stack([
                                        dmc.Text("Debug mode", size="sm", fw=500),
                                        dmc.Text("Show additional debug information", 
                                               size="xs", c="dimmed")
                                    ], gap="xs", flex=1),
                                    dmc.Switch(
                                        id="debug-mode-switch",
                                        checked=False,
                                        size="md"
                                    )
                                ], justify="space-between", align="center")
                            ], gap="lg")
                        ], gap="md")
                    ], p="lg", withBorder=True, radius="md"),
                    
                    # About Section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                DashIconify(icon="tabler:info-circle", width=20),
                                dmc.Text("About", fw=500, size="md")
                            ], gap="sm"),
                            dmc.Divider(size="xs"),
                            dmc.Stack([
                                dmc.Text("UTC Dashboard", size="lg", fw=700),
                                dmc.Text("A platform for leak detection and survey data analysis tools.", 
                                       size="sm", c="dimmed"),
                                dmc.Group([
                                    dmc.Badge("Version 1.0", color="blue", variant="light"),
                                    dmc.Badge("Python", color="green", variant="light"),
                                    dmc.Badge("Dash", color="purple", variant="light")
                                ], gap="xs"),
                                dmc.Text("Developed by: Frank Vejahati, PhD, P.Eng.", 
                                       size="xs", c="dimmed", mt="sm")
                            ], gap="xs")
                        ], gap="md")
                    ], p="lg", withBorder=True, radius="md")
                    
                ], gap="lg")
            ],
            zIndex=10000,
            centered=True,
            overlayProps={"backgroundOpacity": 0.3, "blur": 3},
        )
    ])


# Settings modal callbacks
@callback(
    Output("settings-modal", "opened"),
    Input("settings-modal-button", "n_clicks"),
    State("settings-modal", "opened"),
    prevent_initial_call=True,
)
def toggle_settings_modal(n, opened):
    """Toggle the settings modal."""
    return not opened
