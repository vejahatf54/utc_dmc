import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback
from components.bootstrap_icon import BootstrapIcon
from services.auth_middleware import check_authentication_status

# Main user menu component
user_menu = dmc.Box(
    [
        dmc.ActionIcon(
            BootstrapIcon(icon="person-circle", width=24),
            id="user-menu-button",
            variant="light",
            size="xl",
            radius="xl",
        ),
        dmc.Modal(
            id="user-menu-modal",
            size="sm",
            title=dmc.Group([
                BootstrapIcon(icon="person-circle", width=20),
                dmc.Text("User Menu", fw=600)
            ]),
            children=[
                dmc.Stack(
                    [
                        # Change Password section
                        dmc.Group([
                            BootstrapIcon(icon="key-fill", width=20),
                            html.A(
                                "Change Password",
                                href="/change-password",
                                style={"color": "var(--mantine-color-text)", "textDecoration": "none", "fontWeight": "500"},
                                id="user-menu-change-password"
                            )
                        ], gap="sm", className="user-menu-item"),
                        
                        # Admin section (conditionally shown)
                        html.Div(
                            id="user-menu-admin-section",
                            children=[
                                dmc.Divider(label="Admin", labelPosition="center"),
                                dmc.Group([
                                    BootstrapIcon(icon="people-fill", width=20),
                                    html.A(
                                        "User Management", 
                                        href="/admin/users",
                                        style={"color": "var(--mantine-color-text)", "textDecoration": "none", "fontWeight": "500"},
                                        id="user-menu-user-management"
                                    )
                                ], gap="sm", className="user-menu-item"),
                            ],
                            style={"display": "none"}  # Hidden by default, shown via callback
                        ),
                        
                        dmc.Divider(),
                        
                        # Logout section
                        dmc.Group([
                            BootstrapIcon(icon="box-arrow-right", width=20),
                            dmc.Button(
                                "Logout",
                                variant="subtle",
                                color="red",
                                fw=500,
                                id={"type": "logout-button", "index": "user-menu"},
                                style={"padding": "4px 8px", "minHeight": "24px"}
                            )
                        ], gap="sm", className="user-menu-item"),
                    ],
                    gap="md",
                    p="sm",
                )
            ],
            zIndex=10000,
            centered=True,
            overlayProps={"backgroundOpacity": 0.3, "blur": 3},
        ),
    ]
)


# Callback to toggle user menu modal
@callback(
    Output("user-menu-modal", "opened"),
    Input("user-menu-button", "n_clicks"),
    State("user-menu-modal", "opened"),
    prevent_initial_call=True,
)
def toggle_user_menu_modal(n_clicks, opened):
    """Toggle the user menu modal."""
    return not opened


# Callback to close modal when URL changes (navigation occurs)
@callback(
    Output("user-menu-modal", "opened", allow_duplicate=True),
    Input("url", "pathname"),
    State("user-menu-modal", "opened"),
    prevent_initial_call=True
)
def close_user_menu_on_navigation(pathname, modal_opened):
    """Close user menu modal when navigation occurs."""
    if modal_opened and pathname in ["/change-password", "/admin/users"]:
        return False
    return modal_opened


# Callback to show/hide admin section based on user role
@callback(
    Output("user-menu-admin-section", "style"),
    Input("url", "pathname")
)
def update_user_menu_for_auth(pathname):
    """Update user menu based on authentication status."""
    auth_status = check_authentication_status()
    
    if not auth_status['is_authenticated'] or not auth_status['is_admin']:
        return {"display": "none"}
    
    return {"display": "block"}