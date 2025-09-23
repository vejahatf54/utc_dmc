"""
Refactored Fluid ID Converter page component following clean architecture.
Separates UI logic from business logic using dependency injection.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context
from components.bootstrap_icon import BootstrapIcon
from controllers.fluid_id_controller import FluidIdPageController, FluidIdUIResponseFormatter
from core.dependency_injection import get_container
from core.interfaces import IFluidIdConverter


def create_fluid_id_page():
    """Create the refactored Fluid ID Converter page layout."""
    return dmc.Container([
        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("Fluid ID Converter", order=1, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(
                                icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="fluid-help-modal-btn-v2",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Real-time bidirectional conversion between SCADA FID and Fluid Names",
                             c="dimmed", ta="center", size="lg")
                ], gap="xs")
            ]),

            # Help Modal
            dmc.Modal(
                title="How It Works",
                id="fluid-help-modal-v2",
                children=[
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(
                                        icon="info-circle", width=20),
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
                                    BootstrapIcon(icon="lightbulb", width=20),
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
                ],
                opened=False,
                size="lg"
            ),

            dmc.Space(h="lg"),

            # Main Conversion Section
            dmc.Grid([
                # SCADA FID Card (Left)
                dmc.GridCol([
                    dmc.Paper([
                        dmc.Stack([
                            # Header with icon
                            dmc.Group([
                                BootstrapIcon(icon="hash", width=24),
                                dmc.Text("SCADA FID", fw=500, size="lg")
                            ], justify="center", gap="xs"),

                            dmc.Divider(),

                            # Input section
                            dmc.Stack([
                                dmc.Text("Enter numeric FID (37-basis)",
                                         ta="center", c="dimmed", size="sm"),
                                dmc.TextInput(
                                    id="fid-input-v2",
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
                        ], gap="lg", p="lg")
                    ], shadow="sm", radius="md", withBorder=True, style={"minHeight": "280px"})
                ], span=5),

                # Arrow Column (Center)
                dmc.GridCol([
                    dmc.Center([
                        dmc.Stack([
                            BootstrapIcon(
                                icon="arrow-left-right",
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
                                BootstrapIcon(icon="type", width=24),
                                dmc.Text("Fluid Name", fw=500, size="lg")
                            ], justify="center", gap="xs"),

                            dmc.Divider(),

                            # Input section
                            dmc.Stack([
                                dmc.Text("Enter alphanumeric name",
                                         ta="center", c="dimmed", size="sm"),
                                dmc.TextInput(
                                    id="fluid-name-input-v2",
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
                        ], gap="lg", p="lg")
                    ], shadow="sm", radius="md", withBorder=True, style={"minHeight": "280px"})
                ], span=5)
            ], justify="center", gutter="lg"),

            dmc.Space(h="xl"),

            # Status/Message Section
            dmc.Center([
                html.Div(id="conversion-message-v2")
            ])

        ], gap="lg")
    ], size="lg", p="md")


# Callback for bidirectional conversion using the new architecture
@callback(
    [Output("fluid-name-input-v2", "value"),
     Output("fid-input-v2", "value"),
     Output("conversion-message-v2", "children")],
    [Input("fid-input-v2", "value"),
     Input("fluid-name-input-v2", "value")],
    prevent_initial_call=True
)
def handle_conversion_v2(fid_value, fluid_name_value):
    """Handle bidirectional conversion using the new controller architecture."""
    try:
        # Get the controller from DI container
        container = get_container()
        if not container.is_registered(IFluidIdConverter):
            # Fallback if not registered yet
            from services.fluid_id_service import FluidIdConverterService
            converter = FluidIdConverterService()
        else:
            converter = container.resolve(IFluidIdConverter)

        controller = FluidIdPageController(converter)

        # Determine which input triggered the callback
        trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == 'fid-input-v2':
            if not fid_value or fid_value.strip() == "":
                return "", "", ""

            result = controller.handle_input_change('fid-input', fid_value)
            return FluidIdUIResponseFormatter.format_conversion_response(result)

        elif trigger_id == 'fluid-name-input-v2':
            if not fluid_name_value or fluid_name_value.strip() == "":
                return "", "", ""

            result = controller.handle_input_change(
                'fluid-name-input', fluid_name_value)
            return FluidIdUIResponseFormatter.format_conversion_response(result)

        # Default case
        return "", "", ""

    except Exception as e:
        error_message = dmc.Alert(
            title="System Error",
            children=f"An unexpected error occurred: {str(e)}",
            color="red",
            icon=BootstrapIcon(icon="exclamation-triangle")
        )
        return "", "", error_message


# Callback for help modal
@callback(
    Output("fluid-help-modal-v2", "opened"),
    Input("fluid-help-modal-btn-v2", "n_clicks"),
    State("fluid-help-modal-v2", "opened"),
    prevent_initial_call=True,
)
def toggle_help_modal_v2(n_clicks, opened):
    """Toggle the help modal using controller."""
    try:
        # Get the controller from DI container
        container = get_container()
        if not container.is_registered(IFluidIdConverter):
            from services.fluid_id_service import FluidIdConverterService
            converter = FluidIdConverterService()
        else:
            converter = container.resolve(IFluidIdConverter)

        controller = FluidIdPageController(converter)
        return controller.handle_modal_toggle(n_clicks, opened)

    except Exception:
        # Fallback behavior
        return not opened if n_clicks else opened
