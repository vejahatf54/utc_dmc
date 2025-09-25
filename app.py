from core.dependency_injection import configure_services
import dash_mantine_components as dmc
import sys
from datetime import timedelta
from dash import Dash, Input, Output, State, callback, dcc, html
from components.sidebar import build_sidebar
from components.home_page import create_home_page
from components.license_modal import create_license_modal, get_license_modal_content
import components.login_page as login_page
from components.password_change_page import create_password_change_page, create_forced_password_change_page
from services.auth_middleware import get_protected_content, get_admin_protected_content, get_user_protected_content, check_authentication_status
from services.auth_service import auth_service
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
from components.user_menu import user_menu
from services.config_manager import initialize_config_manager
from services.license_service import license_service
from services.license_middleware import get_license_banner
from logging_config import setup_logging

# Set up file-based logging before anything else
log_filepath = setup_logging()

# Add Mantine figure templates for Plotly
# dmc.add_figure_templates()  # Commented out due to compatibility issues

# Initialize configuration manager on application startup
config_manager = initialize_config_manager()

# Initialize license service and check license
license_info = license_service.load_license()
if not license_info:
    print("ERROR: No valid license found. The application cannot start without a license.")
    print("Please contact your administrator or use the License Manager to obtain a valid license.")
    exit(1)

# Initialize dependency injection container
container = configure_services()

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

# Configure session settings for authentication
app.server.permanent_session_lifetime = timedelta(hours=8)

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
            create_license_modal(),  # Add the license modal
            sidebar,
            html.Div(
                [
                    html.Div([
                        theme_controls,
                        user_menu
                    ], className="theme-controls-topright"),
                    html.Div(id="license-banner"),
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


# Callback for license banner
@app.callback(
    Output("license-banner", "children"),
    Input("url", "pathname")
)
def update_license_banner(pathname):
    """Update the license banner based on current license status"""
    return get_license_banner()


# Server side callback for routing with authentication
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def render_page(pathname: str):
    # Public routes (no authentication required)
    if pathname == "/login":
        # If already authenticated, redirect to home
        if auth_service.is_authenticated():
            return get_protected_content(pathname, create_home_page)
        return login_page.create_login_page()

    # User routes (authenticated users only)
    elif pathname == "/change-password":
        return get_user_protected_content(pathname, create_password_change_page)

    # Admin-only routes
    elif pathname == "/admin/users":
        return get_admin_protected_content(pathname, login_page.create_user_management_page)

    # Protected routes (authentication required)
    elif pathname in ("/", ""):
        return get_protected_content(pathname, create_home_page)

    elif pathname == "/fluid-id-converter":
        return get_protected_content(pathname, create_fluid_id_page)
    elif pathname == "/sps-time-converter":
        return get_protected_content(pathname, create_sps_time_converter_page)
    elif pathname == "/csv-to-rtu":
        return get_protected_content(pathname, create_csv_to_rtu_page)
    elif pathname == "/rtu-to-csv":
        return get_protected_content(pathname, create_rtu_to_csv_page)
    elif pathname == "/rtu-resizer":
        return get_protected_content(pathname, create_rtu_resizer_page)
    elif pathname == "/review-to-csv":
        return get_protected_content(pathname, create_review_to_csv_page)
    elif pathname == "/replace-text":
        return get_protected_content(pathname, create_replace_text_page)
    elif pathname == "/replay-poke-extractor":
        return get_protected_content(pathname, create_replay_file_poke_page)
    elif pathname == "/fluid-properties":
        return get_protected_content(pathname, create_fluid_properties_page)
    elif pathname == "/fetch-archive":
        return get_protected_content(pathname, lambda: fetch_archive_page.layout)
    elif pathname == "/fetch-rtu-data":
        return get_protected_content(pathname, lambda: fetch_rtu_data_page.layout)
    elif pathname == "/elevation":
        return get_protected_content(pathname, elevation_page.create_elevation_page)
    elif pathname == "/linefill":
        return get_protected_content(pathname, linefill_page.create_linefill_page)
    elif pathname == "/pymbsd-services":
        return get_protected_content(pathname, create_pymbsd_page)
    elif pathname == "/flowmeter-acceptance":
        return get_protected_content(pathname, create_flowmeter_acceptance_page)
    elif pathname == "/settings":
        # Redirect settings to home page since we use a modal now
        return get_protected_content(pathname, create_home_page)

    # 404 page
    return dmc.Container([
        dmc.Title("404 - Page Not Found", order=2),
        dmc.Text(f"The page '{pathname}' could not be found.", c="dimmed"),
    ], size="xl")


# Logout callback
@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Input({"type": "logout-button", "index": "user-menu"}, "n_clicks"),
    prevent_initial_call=True
)
def handle_logout(user_menu_clicks):
    """Handle logout button click from user menu."""
    if user_menu_clicks:
        auth_service.logout()
        return "/login"
    return "/"


# License modal callbacks
@app.callback(
    Output("license-modal", "opened"),
    Input("license-info-btn", "n_clicks"),
    State("license-modal", "opened"),
    prevent_initial_call=True
)
def toggle_license_modal(n_clicks, opened):
    """Toggle license modal when license info button is clicked"""
    if n_clicks:
        return not opened
    return opened


@app.callback(
    Output("license-modal-content", "children"),
    Input("license-modal", "opened"),
    prevent_initial_call=True
)
def update_license_modal_content(opened):
    """Update license modal content when opened"""
    if opened:
        return get_license_modal_content()
    return html.Div()


if __name__ == "__main__":
    # Use debug mode and port from config, but override debug=False when packaged
    debug_from_config = config_manager.get_app_debug() and debug_mode
    port_from_config = config_manager.get_app_port()

    app.run(debug=debug_from_config, host="127.0.0.1", port=port_from_config)
