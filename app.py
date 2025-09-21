import dash_mantine_components as dmc
import sys
from dash import Dash, Input, Output, State, callback, dcc, html
from components.sidebar import build_sidebar
from components.home_page import create_home_page
from components.fluid_id_page import create_fluid_id_page
from components.sps_time_converter_page import create_sps_time_converter_page
from components.csv_to_rtu_page import create_csv_to_rtu_page
from components.rtu_to_csv_page import create_rtu_to_csv_page
from components.rtu_resizer_page import create_rtu_resizer_page
from components.review_to_csv_page import create_review_to_csv_page
from components.replace_text_page import create_replace_text_page
from components.replay_file_poke_page import create_replay_file_poke_page
from components.fluid_properties_page import create_fluid_properties_page
from components.pymbsd_page import create_pymbsd_page
from components.flowmeter_acceptance_page import create_flowmeter_acceptance_page
import components.fetch_archive_page as fetch_archive_page
import components.fetch_rtu_data_page as fetch_rtu_data_page
import components.elevation_page as elevation_page
import components.linefill_page as linefill_page
from components.custom_theme import theme_controls, theme_name_mapping, size_name_mapping
from services.config_manager import initialize_config_manager
from logging_config import setup_logging

# Set up file-based logging before anything else
log_filepath = setup_logging()

# Add Mantine figure templates for Plotly
dmc.add_figure_templates()

# Initialize configuration manager on application startup
config_manager = initialize_config_manager()

# Initialize app with appropriate debug mode
# When packaged with PyInstaller, disable debug mode for production
debug_mode = not hasattr(sys, '_MEIPASS')

# Initialize Dash app - keep it simple for packaged version
if debug_mode:
    # Development mode - include dev tools if supported
    app = Dash(__name__, suppress_callback_exceptions=True)
else:
    # Production/packaged mode - minimal configuration
    app = Dash(__name__, suppress_callback_exceptions=True)

# Configure Flask server with secret key from config
app.server.secret_key = config_manager.get_app_secret_key()

sidebar = build_sidebar()

# Main content container; content will be swapped by callback
content = html.Div(id="page-content", className="page-content")

app.layout = dmc.MantineProvider(
    html.Div(
        id="app-shell",
        children=[
            dcc.Location(id="url"),
            dcc.Store(id="plotly-theme-store"),  # Store for Plotly theme state
            dmc.NotificationContainer(
                position="top-center", id="notification-container"),
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
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def render_page(pathname: str):
    if pathname in ("/", ""):
        return create_home_page()
    elif pathname == "/fluid-id-converter":
        return create_fluid_id_page()
    elif pathname == "/sps-time-converter":
        return create_sps_time_converter_page()
    elif pathname == "/csv-to-rtu":
        return create_csv_to_rtu_page()
    elif pathname == "/rtu-to-csv":
        return create_rtu_to_csv_page()
    elif pathname == "/rtu-resizer":
        return create_rtu_resizer_page()
    elif pathname == "/review-to-csv":
        return create_review_to_csv_page()
    elif pathname == "/replace-text":
        return create_replace_text_page()
    elif pathname == "/replay-poke-extractor":
        return create_replay_file_poke_page()
    elif pathname == "/fluid-properties":
        return create_fluid_properties_page()
    elif pathname == "/fetch-archive":
        return fetch_archive_page.layout
    elif pathname == "/fetch-rtu-data":
        return fetch_rtu_data_page.layout
    elif pathname == "/elevation":
        return elevation_page.create_elevation_page()
    elif pathname == "/linefill":
        return linefill_page.create_linefill_page()
    elif pathname == "/pymbsd-services":
        return create_pymbsd_page()
    elif pathname == "/flowmeter-acceptance":
        return create_flowmeter_acceptance_page()
    elif pathname == "/settings":
        # Redirect settings to home page since we use a modal now
        return create_home_page()
    return dmc.Container([
        dmc.Title("404 - Page Not Found", order=2),
        dmc.Text(f"The page '{pathname}' could not be found.", c="dimmed"),
    ], size="xl")


if __name__ == "__main__":
    # Use debug mode and port from config, but override debug=False when packaged
    debug_from_config = config_manager.get_app_debug() and debug_mode
    port_from_config = config_manager.get_app_port()

    app.run(debug=debug_from_config, host="127.0.0.1", port=port_from_config)
