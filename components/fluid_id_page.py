"""
Fluid ID Converter page component for DMC application.
Uses pure DMC components with default theme styling.
"""

import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, Input, Output, callback, callback_context
from components.fluid_id_service import FluidIdConverterService


def create_fluid_id_page():
    """Create the Fluid ID Converter page layout."""
    return dmc.Container([
        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Title("Fluid ID Converter", order=1, ta="center"),
                    dmc.Text("Real-time bidirectional conversion between SCADA FID and Fluid Names",
                             c="dimmed", ta="center", size="lg")
                ], gap="xs")
            ]),

            dmc.Space(h="xl"),

            # Main Conversion Section
            dmc.Grid([
                # SCADA FID Card (Left)
                dmc.GridCol([
                    dmc.Paper([
                        dmc.Stack([
                            # Header with icon
                            dmc.Group([
                                DashIconify(icon="tabler:hash", width=24),
                                dmc.Text("SCADA FID", fw=500, size="lg")
                            ], justify="center", gap="xs"),

                            dmc.Divider(),

                            # Input section
                            dmc.Stack([
                                dmc.Text("Enter numeric FID (37-basis)",
                                         ta="center", c="dimmed", size="sm"),
                                dmc.TextInput(
                                    id="fid-input",
                                    placeholder="e.g. 16292",
                                    size="lg",
                                    styles={
                                        "input": {
                                            "textAlign": "center",
                                            "fontSize": "1.5rem",
                                            "fontWeight": 600
                                        }
                                    }
                                ),
                                dmc.Text("Base-37 numeric system",
                                         ta="center", c="dimmed", size="xs")
                            ], gap="md")
                        ], gap="lg", p="xl")
                    ], shadow="sm", radius="md", withBorder=True, style={"minHeight": "280px"})
                ], span=5),

                # Arrow Column (Center)
                dmc.GridCol([
                    dmc.Center([
                        dmc.Stack([
                            DashIconify(
                                icon="tabler:arrows-left-right",
                                width=50,
                                style={
                                    "filter": "drop-shadow(0 2px 4px rgba(0,0,0,0.1))"}
                            ),
                            dmc.Text("Bidirectional", size="xs",
                                     ta="center", c="dimmed")
                        ], gap="sm", align="center")
                    ], style={"minHeight": "280px"})
                ], span=2),

                # Fluid Name Card (Right)
                dmc.GridCol([
                    dmc.Paper([
                        dmc.Stack([
                            # Header with icon
                            dmc.Group([
                                DashIconify(
                                    icon="tabler:typography", width=24),
                                dmc.Text("Fluid Name", fw=500, size="lg")
                            ], justify="center", gap="xs"),

                            dmc.Divider(),

                            # Input section
                            dmc.Stack([
                                dmc.Text("Enter alphanumeric name",
                                         ta="center", c="dimmed", size="sm"),
                                dmc.TextInput(
                                    id="fluid-name-input",
                                    placeholder="e.g. AWB",
                                    size="lg",
                                    styles={
                                        "input": {
                                            "textAlign": "center",
                                            "fontSize": "1.5rem",
                                            "fontWeight": 600
                                        }
                                    }
                                ),
                                dmc.Text("Characters: 0-9, A-Z, space",
                                         ta="center", c="dimmed", size="xs")
                            ], gap="md")
                        ], gap="lg", p="xl")
                    ], shadow="sm", radius="md", withBorder=True, style={"minHeight": "280px"})
                ], span=5)
            ], justify="center", gutter="xl"),

            dmc.Space(h="xl"),

            # Status/Message Section
            dmc.Center([
                html.Div(id="conversion-message")
            ]),

            dmc.Space(h="xl"),

            # Information Section
            dmc.Paper([
                dmc.Stack([
                    dmc.Title("How It Works", order=3, ta="center"),
                    dmc.Divider(),
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    DashIconify(
                                        icon="tabler:info-circle", width=20),
                                    dmc.Text("Conversion Logic", fw=500)
                                ], gap="xs"),
                                dmc.Text([
                                    "The SCADA FID uses a base-37 numbering system where digits 0-9 and letters A-Z ",
                                    "represent values 0-36. The conversion process translates between this numeric ",
                                    "representation and human-readable fluid names."
                                ], size="sm", c="dimmed")
                            ])
                        ], span=6),
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    DashIconify(
                                        icon="tabler:lightbulb", width=20),
                                    dmc.Text("Usage Tips", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem(
                                        "Enter values in either field for automatic conversion"),
                                    dmc.ListItem(
                                        "FID values must be non-negative integers"),
                                    dmc.ListItem(
                                        "Fluid names support spaces and alphanumeric characters"),
                                    dmc.ListItem(
                                        "Names are automatically padded with spaces if needed")
                                ], size="sm")
                            ])
                        ], span=6)
                    ])
                ], gap="md", p="xl")
            ], shadow="xs", radius="md", withBorder=True)

        ], gap="xl")
    ], size="xl", p="xl")


# Initialize the fluid ID service
fluid_service = FluidIdConverterService()


# Callback for Fluid ID Converter
@callback(
    [Output("fluid-name-input", "value"),
     Output("fid-input", "value"),
     Output("conversion-message", "children")],
    [Input("fid-input", "value"),
     Input("fluid-name-input", "value")],
    prevent_initial_call=True
)
def handle_automatic_conversion(fid_value, fluid_name_value):
    """Handle automatic bidirectional conversion as user types"""

    # Determine which input triggered the callback
    ctx = callback_context
    if not ctx.triggered:
        return "", "", ""

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Handle FID to Fluid Name conversion
    if trigger_id == 'fid-input':
        if not fid_value or fid_value.strip() == "":
            return "", fid_value or "", ""

        result = fluid_service.convert_fid_to_fluid_name(fid_value.strip())

        if result["success"]:
            message = dmc.Alert(
                title="Conversion Successful",
                children=f"Converted: {fid_value} → {result['fluid_name']}",
                color="green",
                icon=DashIconify(icon="tabler:check")
            )
            return result["fluid_name"], fid_value, message
        else:
            message = dmc.Alert(
                title="Conversion Error",
                children=result['error'],
                color="red",
                icon=DashIconify(icon="tabler:alert-circle")
            )
            return "", fid_value, message

    # Handle Fluid Name to FID conversion
    elif trigger_id == 'fluid-name-input':
        if not fluid_name_value or fluid_name_value.strip() == "":
            return fluid_name_value or "", "", ""

        result = fluid_service.convert_fluid_name_to_fid(
            fluid_name_value.strip())

        if result["success"]:
            message = dmc.Alert(
                title="Conversion Successful",
                children=f"Converted: {fluid_name_value} → {result['fid']}",
                color="green",
                icon=DashIconify(icon="tabler:check")
            )
            return fluid_name_value, result["fid"], message
        else:
            message = dmc.Alert(
                title="Conversion Error",
                children=result['error'],
                color="red",
                icon=DashIconify(icon="tabler:alert-circle")
            )
            return fluid_name_value, "", message

    # Default case
    return "", "", ""
