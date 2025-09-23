"""
Password Change Page Component for WUTC application.
Allows users to change their passwords.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, no_update
from services.auth_service import auth_service
from logging_config import get_logger

logger = get_logger(__name__)


def create_password_change_page():
    """Create the password change page layout."""
    return html.Div([
        dmc.Center([
            dmc.Paper([
                dmc.Stack([
                    # Header
                    dmc.Center([
                        dmc.ThemeIcon(
                            html.I(className="bi bi-key-fill"),
                            size="xl",
                            color="blue",
                            variant="light"
                        )
                    ]),
                    dmc.Title("Change Password", order=2, ta="center", mb="md"),
                    
                    # Current password (for regular changes)
                    dmc.PasswordInput(
                        id="current-password",
                        label="Current Password",
                        placeholder="Enter your current password",
                        required=True,
                        size="md",
                        leftSection=dmc.ThemeIcon(
                            html.I(className="bi bi-lock"),
                            variant="light"
                        ),
                        style={"display": "block" if not auth_service.must_change_password() else "none"}
                    ),
                    
                    # New password
                    dmc.PasswordInput(
                        id="new-password",
                        label="New Password",
                        placeholder="Enter your new password",
                        required=True,
                        size="md",
                        leftSection=dmc.ThemeIcon(
                            html.I(className="bi bi-key"),
                            variant="light"
                        )
                    ),
                    
                    # Confirm password
                    dmc.PasswordInput(
                        id="confirm-password",
                        label="Confirm New Password",
                        placeholder="Confirm your new password",
                        required=True,
                        size="md",
                        leftSection=dmc.ThemeIcon(
                            html.I(className="bi bi-key-fill"),
                            variant="light"
                        )
                    ),
                    
                    # Message area
                    html.Div(id="password-change-message"),
                    
                    # Buttons
                    dmc.Group([
                        dmc.Button(
                            "Change Password",
                            id="password-change-submit",
                            color="green",
                            size="md",
                            leftSection=html.I(className="bi bi-check-circle")
                        ),
                        dmc.Button(
                            "Cancel",
                            id="password-change-cancel",
                            variant="outline",
                            color="gray",
                            size="md",
                            style={"display": "block" if not auth_service.must_change_password() else "none"}
                        )
                    ], justify="center", gap="md")
                ], align="stretch", gap="md")
            ], shadow="md", p="xl", radius="md", style={"width": "450px"})
        ])
    ], style={
        "height": "100vh",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "paddingTop": "10vh",
        "paddingBottom": "20vh"
    })


def create_forced_password_change_page():
    """Create the forced password change page (no current password required)."""
    return html.Div([
        dmc.Center([
            dmc.Paper([
                dmc.Stack([
                    # Header with warning
                    dmc.Center([
                        dmc.ThemeIcon(
                            html.I(className="bi bi-exclamation-triangle-fill"),
                            size="xl",
                            color="orange",
                            variant="light"
                        )
                    ]),
                    dmc.Title("Password Change Required", order=2, ta="center"),
                    dmc.Text(
                        "You must change your password before continuing to use the application.",
                        ta="center", c="dimmed", mb="md"
                    ),
                    
                    # New password
                    dmc.PasswordInput(
                        id="forced-new-password",
                        label="New Password",
                        placeholder="Enter your new password",
                        required=True,
                        size="md",
                        leftSection=dmc.ThemeIcon(
                            html.I(className="bi bi-key"),
                            variant="light"
                        )
                    ),
                    
                    # Confirm password
                    dmc.PasswordInput(
                        id="forced-confirm-password",
                        label="Confirm New Password",
                        placeholder="Confirm your new password",
                        required=True,
                        size="md",
                        leftSection=dmc.ThemeIcon(
                            html.I(className="bi bi-key-fill"),
                            variant="light"
                        )
                    ),
                    
                    # Message area
                    html.Div(id="forced-password-message"),
                    
                    # Submit button (no cancel for forced changes)
                    dmc.Button(
                        "Change Password",
                        id="forced-password-submit",
                        color="orange",
                        size="md",
                        fullWidth=True,
                        leftSection=html.I(className="bi bi-key-fill")
                    )
                ], align="stretch", gap="md")
            ], shadow="md", p="xl", radius="md", style={"width": "450px"})
        ])
    ], style={
        "height": "100vh",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "paddingTop": "10vh",
        "paddingBottom": "20vh"
    })


# Callback for regular password change
@callback(
    [Output("password-change-message", "children"),
     Output("current-password", "value"),
     Output("new-password", "value"),
     Output("confirm-password", "value")],
    Input("password-change-submit", "n_clicks"),
    [State("current-password", "value"),
     State("new-password", "value"),
     State("confirm-password", "value")],
    prevent_initial_call=True
)
def handle_password_change(n_clicks, current_password, new_password, confirm_password):
    """Handle regular password change."""
    if not n_clicks:
        return no_update, no_update, no_update, no_update
    
    # Validation
    if not all([current_password, new_password, confirm_password]):
        return dmc.Alert(
            "All fields are required.",
            title="Validation Error",
            color="red"
        ), no_update, no_update, no_update
    
    if new_password != confirm_password:
        return dmc.Alert(
            "New passwords do not match.",
            title="Validation Error",
            color="red"
        ), no_update, "", ""
    
    if len(new_password) < 6:
        return dmc.Alert(
            "Password must be at least 6 characters long.",
            title="Validation Error",
            color="red"
        ), no_update, "", ""
    
    # Change password
    success = auth_service.change_password(current_password, new_password)
    
    if success:
        return dmc.Alert(
            "Password changed successfully!",
            title="Success",
            color="green"
        ), "", "", ""
    else:
        return dmc.Alert(
            "Current password is incorrect.",
            title="Error",
            color="red"
        ), "", no_update, no_update


# Callback for forced password change
@callback(
    [Output("forced-password-message", "children"),
     Output("forced-new-password", "value"),
     Output("forced-confirm-password", "value")],
    Input("forced-password-submit", "n_clicks"),
    [State("forced-new-password", "value"),
     State("forced-confirm-password", "value")],
    prevent_initial_call=True
)
def handle_forced_password_change(n_clicks, new_password, confirm_password):
    """Handle forced password change."""
    if not n_clicks:
        return no_update, no_update, no_update
    
    # Validation
    if not all([new_password, confirm_password]):
        return dmc.Alert(
            "All fields are required.",
            title="Validation Error",
            color="red"
        ), no_update, no_update
    
    if new_password != confirm_password:
        return dmc.Alert(
            "Passwords do not match.",
            title="Validation Error",
            color="red"
        ), "", ""
    
    if len(new_password) < 6:
        return dmc.Alert(
            "Password must be at least 6 characters long.",
            title="Validation Error",
            color="red"
        ), "", ""
    
    # Change password (forced, no current password required)
    success = auth_service.change_password_forced(new_password)
    
    if success:
            # Redirect after successful password change
        return dmc.Alert(
            "Password changed successfully! Redirecting...",
            title="Success",
            color="green"
        ), "", ""
    else:
        return dmc.Alert(
            "Failed to change password. Please try again.",
            title="Error",
            color="red"
        ), no_update, no_update


# Callback for cancel button - redirect to home page
@callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("password-change-cancel", "n_clicks"),
    prevent_initial_call=True
)
def handle_password_change_cancel(n_clicks):
    """Handle cancel button click - redirect to home page."""
    if n_clicks:
        return "/"
    return no_update