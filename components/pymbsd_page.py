import dash
from dash import html, dcc, Input, Output, State, callback, ALL, ctx
import dash_mantine_components as dmc
import asyncio
from services.pymbsd_service import PyMBSdService
from components.bootstrap_icon import BootstrapIcon
import logging

logger = logging.getLogger(__name__)


def create_pymbsd_page():
    """Create the PyMBSd service management page"""
    return dmc.Container([
        # Data stores
        dcc.Store(id='pymbsd-services-store', data=[]),
        dcc.Store(id='pymbsd-selected-services-store', data=[]),
        dcc.Store(id='pymbsd-operation-status-store', data={'status': 'idle'}),
        dcc.Store(id='pymbsd-checkbox-states', data=[]),

        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("PyMBSd Service Management",
                                  order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(
                                icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="pymbsd-help-modal-btn",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Manage Windows services for PyMBSd packages with install, start, stop, and uninstall operations",
                             c="dimmed", ta="center", size="md")
                ], gap="xs")
            ]),

            # Help Modal
            dmc.Modal(
                title="PyMBSd Service Management Help",
                id="pymbsd-help-modal",
                children=[
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(
                                        icon="info-circle", width=20),
                                    dmc.Text("Requirements", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem(
                                        "Administrator privileges required"),
                                    dmc.ListItem(
                                        "Access to UNC package paths"),
                                    dmc.ListItem(
                                        "WinSW service wrapper support"),
                                    dmc.ListItem(
                                        "Valid PyMBSd packages in configured location")
                                ], size="sm")
                            ])
                        ], span=6),
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="lightbulb", width=20),
                                    dmc.Text("Process", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem(
                                        "Click 'Fetch Services' to load available packages"),
                                    dmc.ListItem(
                                        "Select services using checkboxes"),
                                    dmc.ListItem(
                                        "Use Install/Start/Stop/Uninstall buttons for operations"),
                                    dmc.ListItem(
                                        "Monitor status and logs in the right panel")
                                ], size="sm")
                            ])
                        ], span=6)
                    ])
                ],
                opened=False,
                size="lg"
            ),

            dmc.Space(h="md"),

            # Main Content - Two-column layout
            dmc.Grid([
                # Left Column - Service List (wider)
                dmc.GridCol([
                    dmc.Paper([
                        dmc.Group([
                            dmc.Title("Available Services",
                                      order=4, c="dimmed"),
                            dmc.Button(
                                "Refresh List",
                                id="pymbsd-refresh-btn",
                                leftSection=BootstrapIcon(
                                    icon="arrow-clockwise", width=16, height=16),
                                variant="filled",
                                size="sm"
                            ),
                        ], justify="space-between", mb="md"),

                        dmc.Divider(size="xs"),

                        # Service content with loading overlay
                        html.Div([
                            dmc.LoadingOverlay(
                                id="pymbsd-loading",
                                visible=False
                            ),
                            # Multi-column service list container
                            html.Div(
                                id="pymbsd-service-list",
                                children=[],
                                className="service-multi-column-container"
                            ),
                        ], style={"position": "relative"}),

                        # Select All checkbox moved below the list
                        dmc.Divider(size="xs", mt="md"),
                        dmc.Checkbox(
                            id="pymbsd-select-all",
                            label="Select All Services",
                            checked=False,
                            size="md",
                            mt="sm"
                        ),
                    ], p="lg", shadow="sm", radius="md"),
                ], span=8),  # 8/12 columns for service list

                # Right Column - Options and Actions (narrower)
                dmc.GridCol([
                    # Installation Options
                    dmc.Paper([
                        dmc.Group([
                            BootstrapIcon(icon="gear", width=20),
                            dmc.Text("Installation Options", fw=500, size="md")
                        ], gap="xs", mb="md"),
                        dmc.Stack([
                            dmc.Checkbox(
                                id="pymbsd-start-service",
                                label="Start service after installation",
                                checked=True,
                                size="md"
                            ),
                            dmc.Checkbox(
                                id="pymbsd-auto-mode",
                                label="Set service start mode to automatic",
                                checked=True,
                                size="md"
                            ),
                        ], gap="md"),
                    ], p="lg", shadow="sm", radius="md", mb="md"),

                    # Action Buttons Section
                    dmc.Paper([
                        dmc.Group([
                            BootstrapIcon(icon="play-circle", width=20),
                            dmc.Text("Service Actions", fw=500, size="md")
                        ], gap="xs", mb="md"),
                        dmc.Stack([
                            dmc.Button(
                                "Install",
                                id="pymbsd-install-btn",
                                leftSection=BootstrapIcon(
                                    icon="download", width=16, height=16),
                                color="green",
                                size="md",
                                disabled=True,
                                fullWidth=True
                            ),
                            dmc.Button(
                                "Start",
                                id="pymbsd-start-btn",
                                leftSection=BootstrapIcon(
                                    icon="play-fill", width=16, height=16),
                                color="blue",
                                size="md",
                                disabled=True,
                                fullWidth=True
                            ),
                            dmc.Button(
                                "Stop",
                                id="pymbsd-stop-btn",
                                leftSection=BootstrapIcon(
                                    icon="stop-fill", width=16, height=16),
                                color="orange",
                                size="md",
                                disabled=True,
                                fullWidth=True
                            ),
                            dmc.Button(
                                "Uninstall",
                                id="pymbsd-uninstall-btn",
                                leftSection=BootstrapIcon(
                                    icon="trash", width=16, height=16),
                                color="red",
                                size="md",
                                disabled=True,
                                fullWidth=True
                            ),
                        ], gap="sm"),
                    ], p="lg", shadow="sm", radius="md"),
                ], span=4),  # 4/12 columns for options and actions
            ], gutter="lg"),

            # Status/Results Section
            html.Div(id="pymbsd-status-messages"),

            # Auto-refresh interval component
            dcc.Interval(
                id="pymbsd-status-interval",
                interval=5000,  # Update every 5 seconds
                n_intervals=0,
                disabled=True
            )
        ]),  # Close Stack

        # Store for service data (moved outside the Stack)
        dcc.Store(id="pymbsd-service-data", data=[]),
    ], fluid=True, px="lg")


def create_service_card(service_info, index, is_selected=False):
    """Create a compact service card with status icon and checkbox"""
    package_name = service_info.get("package_name", "")
    service_name = service_info.get("service_name", "")
    status = service_info.get("status", "not_found")

    # Determine icon and color based on status
    icon_config = get_status_icon(status)

    # Add loading animation class for transitional states
    icon_class = "service-status-loading" if status in [
        "starting", "stopping", "loading"] else ""

    # Create compact service item
    return html.Div([
        dmc.Group([
            # Checkbox with preserved selection state
            dmc.Checkbox(
                id={"type": "pymbsd-service-checkbox", "index": index},
                checked=is_selected,
                size="sm"
            ),

            # Status icon
            BootstrapIcon(
                icon=icon_config["icon"],
                width=16,
                height=16,
                className=f"{icon_class} {icon_config['color_class']}"
            ),

            # Service name (compact with controlled width)
            dmc.Text(
                package_name,
                size="sm",
                fw=500,
                truncate=True,
                style={"maxWidth": "160px", "minWidth": "120px"}
            ),

            # Status badge (small)
            dmc.Badge(
                status.replace("_", " ").title(),
                color=icon_config["badge_color"],
                size="xs",
                variant="light"
            ),
        ],
            align="center",
            gap="sm",
            justify="space-between",
            className="service-compact-item",
            style={"padding": "4px 6px", "minHeight": "28px"}
        ),
    ],
        className="service-item-wrapper mb-1",
        **{"data-status": status, "title": f"Package: {package_name}\nService: {service_name}"}
    )


def get_status_icon(status):
    """Get icon configuration based on service status"""
    status_configs = {
        "running": {
            "icon": "check-circle-fill",
            "color_class": "text-success",
            "badge_color": "green"
        },
        "stopped": {
            "icon": "stop-circle-fill",
            "color_class": "text-danger",
            "badge_color": "red"
        },
        "starting": {
            "icon": "arrow-clockwise",
            "color_class": "text-primary service-status-loading",
            "badge_color": "blue"
        },
        "stopping": {
            "icon": "arrow-clockwise",
            "color_class": "text-warning service-status-loading",
            "badge_color": "orange"
        },
        "loading": {
            "icon": "arrow-clockwise",
            "color_class": "text-info service-status-loading",
            "badge_color": "blue"
        },
        "not_found": {
            "icon": "question-circle",
            "color_class": "text-muted",
            "badge_color": "gray"
        },
        "error": {
            "icon": "exclamation-triangle-fill",
            "color_class": "text-danger",
            "badge_color": "red"
        }
    }
    return status_configs.get(status, status_configs["not_found"])

# Callbacks


@callback(
    [Output("pymbsd-service-list", "children"),
     Output("pymbsd-service-data", "data"),
     Output("pymbsd-loading", "visible")],
    [Input("pymbsd-refresh-btn", "n_clicks")],
    prevent_initial_call=False
)
def refresh_service_list(n_clicks):
    """Refresh the list of available services"""
    try:
        # Fetch services without status (fast initial load)
        services = PyMBSdService.fetch_service_packages_fast()

        service_cards = []
        for i, service in enumerate(services):
            # Initially show with "loading" status
            service_with_loading = service.copy()
            service_with_loading["status"] = "loading"
            service_cards.append(create_service_card(service_with_loading, i))

        return service_cards, services, False
    except Exception as e:
        logger.error(f"Error refreshing service list: {e}")

        # Create a more detailed error message
        error_text = str(e)
        if "not accessible" in error_text:
            title = "Network Path Not Accessible"
            icon = BootstrapIcon(icon="wifi-off", width=20,
                                 height=20, className="text-danger")
        elif "not configured" in error_text:
            title = "Configuration Error"
            icon = BootstrapIcon(icon="gear", width=20,
                                 height=20, className="text-danger")
        else:
            title = "Error Loading Services"
            icon = BootstrapIcon(icon="exclamation-triangle",
                                 width=20, height=20, className="text-danger")

        error_message = dmc.Alert(
            [
                dmc.Group([
                    icon,
                    dmc.Stack([
                        dmc.Text(title, fw=500),
                        dmc.Text(error_text, size="sm")
                    ], gap="xs")
                ], gap="md")
            ],
            color="red",
            className="mb-3"
        )
        return [error_message], [], False, []


@callback(
    [Output("pymbsd-status-interval", "disabled"),
     Output("pymbsd-status-interval", "n_intervals")],
    [Input("pymbsd-service-list", "children")],
    prevent_initial_call=True
)
def enable_status_updates(service_list):
    """Enable status updates when services are loaded and trigger immediate update"""
    has_services = len(service_list) > 0
    if has_services:
        # Reset intervals to trigger immediate status update
        return False, 1
    return True, 0


@callback(
    [Output("pymbsd-service-list", "children", allow_duplicate=True),
     Output("pymbsd-service-data", "data", allow_duplicate=True)],
    [Input("pymbsd-status-interval", "n_intervals")],
    [State("pymbsd-service-data", "data"),
     State("pymbsd-checkbox-states", "data")],
    prevent_initial_call=True
)
def update_service_status(n_intervals, service_data, checkbox_states):
    """Update service status icons periodically while preserving selections"""
    if not service_data:
        return dash.no_update, dash.no_update

    try:
        # Update service statuses
        updated_services = PyMBSdService.update_service_statuses(service_data)

        service_cards = []
        for i, service in enumerate(updated_services):
            # Get current selection state for this service from store
            is_selected = checkbox_states[i] if i < len(
                checkbox_states) else False
            service_cards.append(create_service_card(service, i, is_selected))

        return service_cards, updated_services
    except Exception as e:
        logger.error(f"Error updating service status: {e}")
        return dash.no_update, dash.no_update


# Track checkbox state changes and initialize states
@callback(
    Output("pymbsd-checkbox-states", "data"),
    [Input({"type": "pymbsd-service-checkbox", "index": ALL}, "checked"),
     Input("pymbsd-select-all", "checked"),
     Input("pymbsd-service-data", "data")],
    [State("pymbsd-checkbox-states", "data")],
    prevent_initial_call=False
)
def update_checkbox_states(individual_checks, select_all_checked, service_data, current_states):
    """Track and update checkbox states, initialize when services refresh"""
    ctx_triggered = ctx.triggered_id if ctx.triggered else None

    if not service_data:
        return []

    # If service data was updated (refresh), initialize checkbox states
    if ctx_triggered == "pymbsd-service-data":
        return [False] * len(service_data)

    # If select all was triggered
    if ctx_triggered == "pymbsd-select-all":
        return [select_all_checked] * len(service_data)

    # If individual checkboxes were triggered
    if individual_checks is not None:
        return individual_checks

    return current_states or [False] * len(service_data)


@callback(
    [Output("pymbsd-install-btn", "disabled"),
     Output("pymbsd-start-btn", "disabled"),
     Output("pymbsd-stop-btn", "disabled"),
     Output("pymbsd-uninstall-btn", "disabled")],
    [Input("pymbsd-checkbox-states", "data")],
    prevent_initial_call=True
)
def update_button_states(checkbox_states):
    """Enable/disable action buttons based on service selection"""
    has_selection = any(checkbox_states) if checkbox_states else False
    disabled = not has_selection
    return disabled, disabled, disabled, disabled


@callback(
    Output("pymbsd-status-messages", "children"),
    [Input("pymbsd-install-btn", "n_clicks"),
     Input("pymbsd-start-btn", "n_clicks"),
     Input("pymbsd-stop-btn", "n_clicks"),
     Input("pymbsd-uninstall-btn", "n_clicks")],
    [State("pymbsd-checkbox-states", "data"),
     State("pymbsd-service-data", "data"),
     State("pymbsd-start-service", "checked"),
     State("pymbsd-auto-mode", "checked")],
    prevent_initial_call=True
)
def handle_service_actions(install_clicks, start_clicks, stop_clicks, uninstall_clicks,
                           checkbox_states, service_data, start_after_install, auto_mode):
    """Handle service management actions"""
    if not ctx.triggered or not any(checkbox_states):
        return []

    # Get selected services
    selected_indices = [i for i, checked in enumerate(
        checkbox_states) if checked]
    selected_services = [service_data[i]
                         for i in selected_indices if i < len(service_data)]

    if not selected_services:
        return [dmc.Alert("No services selected", color="yellow", className="mb-3")]

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    try:
        if "install" in triggered_id:
            result = PyMBSdService.install_services(
                selected_services, start_after_install, auto_mode)
        elif "start" in triggered_id:
            result = PyMBSdService.start_services(selected_services)
        elif "stop" in triggered_id:
            result = PyMBSdService.stop_services(selected_services)
        elif "uninstall" in triggered_id:
            result = PyMBSdService.uninstall_services(selected_services)
        else:
            return []

        if result["success"]:
            return [dmc.Alert(result["message"], color="green", className="mb-3")]
        else:
            return [dmc.Alert(result["message"], color="red", className="mb-3")]

    except Exception as e:
        logger.error(f"Error in service action: {e}")
        return [dmc.Alert(f"Error: {str(e)}", color="red", className="mb-3")]


@callback(
    Output("pymbsd-help-modal", "opened"),
    Input("pymbsd-help-modal-btn", "n_clicks"),
    State("pymbsd-help-modal", "opened"),
    prevent_initial_call=True
)
def toggle_help_modal(n_clicks, opened):
    """Toggle the help modal visibility"""
    if n_clicks:
        return not opened
    return opened
