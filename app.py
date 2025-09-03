import json
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import Dash, Input, Output, State, callback, dcc, html, clientside_callback, callback_context
from components.sidebar import build_sidebar
from components.home_page import create_home_page
from components.fluid_id_page import create_fluid_id_page
from components.fluid_id_service import FluidIdConverterService
from components.custom_theme import theme_controls, color_picker_value_mapping, theme_name_mapping, size_name_mapping

app = Dash(__name__, suppress_callback_exceptions=True)

sidebar = build_sidebar()

# Main content container; content will be swapped by callback
content = html.Div(id="page-content", className="page-content")

app.layout = dmc.MantineProvider(
    html.Div(
        id="app-shell",
        children=[
            dcc.Location(id="url"),
            sidebar,
            html.Div(
                [
                    html.Div(theme_controls,
                             className="theme-controls-topright"),
                    content
                ],
                className="main-content-shell"
            )
        ],
        className="app-shell",
    ),
    theme={
        "primaryColor": "green",
        "defaultRadius": "sm",
        "components": {"Card": {"defaultProps": {"shadow": "sm"}}},
    },
    forceColorScheme="light",
    id="mantine-provider",
)

# Callbacks for theme customization


@callback(
    Output("mantine-provider", "theme"),
    Input("color-picker", "value"),
    Input("radius", "value"),
    Input("shadow", "value"),
    State("mantine-provider", "theme"),
)
def update_theme(color, radius, shadow, theme):
    """Update the theme based on user selections."""
    theme["primaryColor"] = theme_name_mapping[color]
    theme["defaultRadius"] = size_name_mapping[radius]
    theme["components"]["Card"]["defaultProps"]["shadow"] = size_name_mapping[shadow]
    return theme


@callback(
    Output("modal-customize", "opened"),
    Input("modal-demo-button", "n_clicks"),
    State("modal-customize", "opened"),
    prevent_initial_call=True,
)
def toggle_customize_modal(n, opened):
    """Toggle the customize theme modal."""
    return not opened


# Server side callback for routing


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page(pathname: str):
    if pathname in ("/", ""):
        return create_home_page()
    elif pathname == "/fluid-id-converter":
        return create_fluid_id_page()
    elif pathname == "/settings":
        return dmc.Container([
            dmc.Title("Settings", order=2, mb="md"),
            dmc.Text("Adjust your preferences here.", mb="lg"),
            dmc.Card([
                dmc.Title("Theme Settings", order=4),
                dmc.Text("Customize your dashboard preferences",
                         c="dimmed", mb="md"),
                dmc.Switch(
                    label="Dark Mode",
                    description="Toggle between light and dark themes"
                )
            ], withBorder=True, shadow="sm", radius="md", p="lg")
        ], size="xl")
    return dmc.Container([
        dmc.Title("404 - Page Not Found", order=2),
        dmc.Text(f"The page '{pathname}' could not be found.", c="dimmed"),
    ], size="xl")


# Initialize the fluid ID service
fluid_service = FluidIdConverterService()


# Callback for Fluid ID Converter
@app.callback(
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


if __name__ == "__main__":
    app.run(debug=True)
