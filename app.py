import json
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import Dash, Input, Output, State, callback, dcc, html, clientside_callback
from components.sidebar import build_sidebar
from components.home_page import create_home_page
from components.custom_theme import theme_controls, color_picker_value_mapping, theme_name_mapping, size_name_mapping

app = Dash(__name__)

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


if __name__ == "__main__":
    app.run(debug=True)
