"""
Login Page Component for WUTC application.
Provides user authentication interface.
"""

import dash_mantine_components as dmc
from dash import html, dcc, Input, Output, State, callback, no_update, callback_context, ALL
from services.auth_service import auth_service
from logging_config import get_logger

logger = get_logger(__name__)


def create_login_page():
    """Create the login page layout."""
    return html.Div([
        dmc.Center([
            dmc.Paper([
                dmc.Stack([
                    # Logo or header
                    dmc.Center([
                        dmc.Title("WUTC Login", order=1, ta="center", mb="lg")
                    ]),
                    
                    # Login form
                    dmc.TextInput(
                        id="login-username",
                        label="Username or Email",
                        placeholder="Enter your username or email",
                        required=True,
                        size="md",
                        leftSection=dmc.ThemeIcon(
                            html.I(className="bi bi-person"),
                            variant="light"
                        )
                    ),
                    
                    dmc.PasswordInput(
                        id="login-password",
                        label="Password",
                        placeholder="Enter your password",
                        required=True,
                        size="md",
                        leftSection=dmc.ThemeIcon(
                            html.I(className="bi bi-lock"),
                            variant="light"
                        )
                    ),
                    
                    # Error message area
                    html.Div(id="login-error-message"),
                    
                    # Login button
                    dmc.Button(
                        "Login",
                        id="login-submit-button",
                        fullWidth=True,
                        size="lg",
                        mt="md"
                    ),
                    
                    # Session info for debugging (remove in production)
                    html.Div(id="login-debug-info", style={"display": "none"})
                    
                ], gap="lg")
            ], shadow="xl", p="xl", radius="lg", w=450, maw="90vw")
        ])
    ], style={
        "height": "100vh",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "paddingTop": "10vh",  # Move the card higher by adding top padding
        "paddingBottom": "20vh"  # More bottom padding to push it up
    })


def create_admin_registration_page():
    """Create the admin user registration page (admin only)."""
    return dmc.Container([
        dmc.Paper([
            dmc.Stack([
                dmc.Title("Register New User", order=2),
                dmc.Text("Create a new user account", c="dimmed"),
                
                # Registration form
                dmc.TextInput(
                    id="register-username",
                    label="Username",
                    placeholder="Enter username",
                    required=True,
                    size="md"
                ),
                
                dmc.TextInput(
                    id="register-email",
                    label="Email",
                    placeholder="Enter email address",
                    required=True,
                    size="md"
                ),
                
                dmc.PasswordInput(
                    id="register-password",
                    label="Password",
                    placeholder="Enter password",
                    required=True,
                    size="md"
                ),
                
                dmc.PasswordInput(
                    id="register-password-confirm",
                    label="Confirm Password",
                    placeholder="Confirm password",
                    required=True,
                    size="md"
                ),
                
                dmc.Switch(
                    id="register-is-admin",
                    label="Admin User",
                    description="Give this user administrative privileges",
                    size="md",
                    mt="lg"
                ),
                
                # Error/success message area
                html.Div(id="register-message"),
                
                # Buttons
                dmc.Group([
                    dmc.Button(
                        "Register User",
                        id="register-submit-button"
                    ),
                    dmc.Button(
                        "Cancel",
                        id="register-cancel-button",
                        variant="outline"
                    )
                ], justify="flex-end", mt="xl")
                
            ], gap="lg")
        ], shadow="md", p="xl", radius="md")
    ], size="sm")


def create_user_management_page():
    """Create the user management page (admin only)."""
    return dmc.Container([
        dmc.Stack([
            dmc.Group([
                dmc.Title("User Management", order=2),
                dmc.Button(
                    "Add New User",
                    id="add-user-button",
                    leftSection=html.I(className="bi bi-plus"),
                    color="green"
                )
            ], justify="space-between"),
            
            # Users table will be populated by callback
            html.Div(id="users-table-container"),
            
            # Modals for user operations
            dmc.Modal(
                id="add-user-modal",
                title="Add New User",
                children=create_admin_registration_page().children[0].children[0].children,
                size="md"
            ),
            
            # Password change modal
            dmc.Modal(
                id="change-password-modal",
                title="Change Password",
                children=[
                    dmc.Stack([
                        dmc.PasswordInput(
                            id="current-password",
                            label="Current Password",
                            placeholder="Enter current password",
                            required=True,
                            size="md"
                        ),
                        dmc.PasswordInput(
                            id="new-password",
                            label="New Password",
                            placeholder="Enter new password",
                            required=True,
                            size="md"
                        ),
                        dmc.PasswordInput(
                            id="confirm-new-password",
                            label="Confirm New Password",
                            placeholder="Confirm new password",
                            required=True,
                            size="md"
                        ),
                        html.Div(id="password-change-message"),
                        dmc.Group([
                            dmc.Button(
                                "Change Password",
                                id="change-password-submit"
                            ),
                            dmc.Button(
                                "Cancel",
                                id="change-password-cancel",
                                variant="outline"
                            )
                        ], justify="flex-end")
                    ], gap="md")
                ],
                size="md"
            )
            
        ], gap="md")
    ], size="xl")


# Callbacks for login functionality
@callback(
    [Output("login-error-message", "children"),
     Output("url", "pathname", allow_duplicate=True)],
    [Input("login-submit-button", "n_clicks"),
     Input("login-password", "n_submit")],
    [State("login-username", "value"),
     State("login-password", "value")],
    prevent_initial_call=True
)
def handle_login(n_clicks, n_submit, username, password):
    """Handle login form submission."""
    if (not n_clicks and not n_submit) or not username or not password:
        return no_update, no_update
    
    user_info = auth_service.login(username, password)
    
    if user_info:
        logger.info(f"User logged in successfully: {username}")
        # Redirect to home page
        return "", "/"
    else:
        logger.warning(f"Failed login attempt: {username}")
        return dmc.Alert(
            "Invalid username or password. Please try again.",
            title="Login Failed",
            color="red",
            id="login-error-alert"
        ), no_update


@callback(
    [Output("register-message", "children"),
     Output("users-table-container", "children", allow_duplicate=True)],
    Input("register-submit-button", "n_clicks"),
    [State("register-username", "value"),
     State("register-email", "value"),
     State("register-password", "value"),
     State("register-password-confirm", "value"),
     State("register-is-admin", "checked")],
    prevent_initial_call=True
)
def handle_user_registration(n_clicks, username, email, password, password_confirm, is_admin):
    """Handle user registration form submission (admin only)."""
    if not n_clicks:
        return no_update, no_update
    
    # Validation
    if not all([username, email, password, password_confirm]):
        return dmc.Alert(
            "All fields are required.",
            title="Validation Error",
            color="red"
        ), no_update
    
    if password != password_confirm:
        return dmc.Alert(
            "Passwords do not match.",
            title="Validation Error",
            color="red"
        ), no_update
    
    if len(password) < 6:
        return dmc.Alert(
            "Password must be at least 6 characters long.",
            title="Validation Error",
            color="red"
        ), no_update
    
    # Create user
    user_id = auth_service.create_user_by_admin(username, email, password, bool(is_admin))
    
    if user_id:
        # Refresh the users table with AG Grid
        users = auth_service.list_all_users()
        updated_table = create_ag_grid_table(users)
        
        return dmc.Alert(
            f"User '{username}' created successfully.",
            title="Success",
            color="green"
        ), updated_table
    else:
        return dmc.Alert(
            "Failed to create user. Username or email may already exist.",
            title="Error",
            color="red"
        ), no_update


@callback(
    Output("users-table-container", "children"),
    Input("url", "pathname")
)
def populate_users_table(pathname):
    """Populate the users table (admin only)."""
    if pathname != "/admin/users":
        return no_update
    
    if not auth_service.is_admin():
        return dmc.Alert(
            "Access denied. Admin privileges required.",
            title="Unauthorized",
            color="red"
        )
    
    users = auth_service.list_all_users()
    
    if not users:
        return dmc.Text("No users found.", c="dimmed")
    
    return create_ag_grid_table(users)


def create_ag_grid_table(users):
    """Create AG Grid table for users with checkbox selection."""
    try:
        import dash_ag_grid as dag
    except ImportError:
        return create_users_html_table(users)
    
    current_user = auth_service.get_current_user()
    current_user_id = current_user['id'] if current_user else None
    
    grid_data = []
    
    for user in users:
        grid_data.append({
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "is_admin": "✅ Admin" if user['is_admin'] else "👤 User",
            "is_admin_bool": user['is_admin'],  # Keep original boolean for logic
            "created_at": user['created_at'][:10] if user['created_at'] else "N/A",
            "last_login": user['last_login'][:16] if user['last_login'] else "Never"
        })
    
    # Column definitions with checkbox selection
    column_defs = [
        {
            "headerName": "",
            "checkboxSelection": True,
            "headerCheckboxSelection": True,
            "width": 50,
            "pinned": "left",
            "lockPosition": True,
            "cellRenderer": "agCheckboxCellRenderer"
        },
        {"headerName": "Username", "field": "username", "sortable": True, "filter": True, "flex": 1},
        {"headerName": "Email", "field": "email", "sortable": True, "filter": True, "flex": 1.5},
        {"headerName": "Role", "field": "is_admin", "sortable": True, "filter": True, "width": 120},
        {"headerName": "Created", "field": "created_at", "sortable": True, "filter": True, "width": 120},
        {"headerName": "Last Login", "field": "last_login", "sortable": True, "filter": True, "width": 150}
    ]
    
    return html.Div([
        # Bulk action buttons above the grid
        dmc.Group([
            dmc.Button(
                [
                    html.I(className="bi bi-key-fill", style={"marginRight": "0.5rem"}),
                    "Change My Password"
                ],
                id="bulk-change-password-btn",
                variant="outline",
                color="blue",
                size="sm"
            ),
            dmc.Button(
                [
                    html.I(className="bi bi-trash-fill", style={"marginRight": "0.5rem"}),
                    "Delete Selected Users"
                ],
                id="bulk-delete-btn",
                variant="outline",
                color="red",
                size="sm",
                disabled=True  # Start disabled
            )
        ], gap="md", mb="md"),
        
        # AG Grid with checkbox selection
        dag.AgGrid(
            id="users-grid",
            rowData=grid_data,
            columnDefs=column_defs,
            defaultColDef={
                "resizable": True,
                "sortable": True,
                "filter": True
            },
            dashGridOptions={
                "pagination": True,
                "paginationPageSize": 10,
                "domLayout": "autoHeight",
                "rowSelection": "multiple",
                "suppressRowClickSelection": True
            },
            style={"height": None},
            className="ag-theme-alpine"
        )
    ], className="users-grid-container", id="users-grid-wrapper")


def create_users_html_table(users):
    """Fallback HTML table for users."""
    current_user = auth_service.get_current_user()
    current_user_id = current_user['id'] if current_user else None
    
    table_rows = []
    for user in users:
        # Action buttons
        action_buttons = []
        
        # Change password button (only for current user)
        if user['id'] == current_user_id:
            action_buttons.append(
                dmc.Button(
                    "Change Password",
                    size="xs",
                    variant="outline",
                    id={"type": "change-password-btn", "index": user['id']},
                    style={"marginRight": "5px"}
                )
            )
        
        # Deactivate button (not for current user)
        if user['id'] != current_user_id and user['is_active']:
            action_buttons.append(
                dmc.Button(
                    "Deactivate",
                    size="xs",
                    color="red",
                    variant="outline",
                    id={"type": "deactivate-user-btn", "index": user['id']}
                )
            )
        
        table_rows.append(
            html.Tr([
                html.Td(user['username']),
                html.Td(user['email']),
                html.Td("Yes" if user['is_admin'] else "No"),
                html.Td("Active" if user['is_active'] else "Inactive"),
                html.Td(user['created_at'][:10] if user['created_at'] else "N/A"),
                html.Td(user['last_login'][:16] if user['last_login'] else "Never"),
                html.Td(action_buttons)
            ])
        )
    
    return dmc.Table([
        html.Thead([
            html.Tr([
                html.Th("Username"),
                html.Th("Email"),
                html.Th("Admin"),
                html.Th("Status"),
                html.Th("Created"),
                html.Th("Last Login"),
                html.Th("Actions")
            ])
        ]),
        html.Tbody(table_rows)
    ], striped=True, highlightOnHover=True)


# Callback for opening add user modal
@callback(
    Output("add-user-modal", "opened"),
    [Input("add-user-button", "n_clicks"),
     Input("register-cancel-button", "n_clicks")],
    State("add-user-modal", "opened"),
    prevent_initial_call=True
)
def toggle_add_user_modal(add_clicks, cancel_clicks, opened):
    """Toggle the add user modal."""
    ctx = callback_context
    if not ctx.triggered:
        return opened
    
    button_id = ctx.triggered[0]["prop_id"]
    
    if "register-cancel-button" in button_id:
        return False  # Close modal
    elif add_clicks:
        return not opened
    return opened


# Callback for opening change password modal
@callback(
    Output("change-password-modal", "opened"),
    [Input({"type": "change-password-btn", "index": ALL}, "n_clicks"),
     Input("change-password-cancel", "n_clicks")],
    State("change-password-modal", "opened"),
    prevent_initial_call=True
)
def toggle_change_password_modal(change_btn_clicks, cancel_clicks, opened):
    """Toggle the change password modal."""
    ctx = callback_context
    if not ctx.triggered:
        return opened
    
    button_id = ctx.triggered[0]["prop_id"]
    
    if "change-password-cancel" in button_id:
        return False  # Close modal
    elif any(change_btn_clicks):
        return not opened
    return opened


# Callback for handling password change in modal
@callback(
    Output("password-change-message", "children", allow_duplicate=True),
    [Input("change-password-submit", "n_clicks"),
     Input("change-password-cancel", "n_clicks")],
    [State("current-password", "value"),
     State("new-password", "value"),
     State("confirm-new-password", "value")],
    prevent_initial_call=True
)
def handle_modal_password_change(submit_clicks, cancel_clicks, current_password, new_password, confirm_password):
    """Handle password change form submission."""
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "change-password-cancel":
        return ""
    
    if button_id == "change-password-submit" and submit_clicks:
        # Validation
        if not all([current_password, new_password, confirm_password]):
            return dmc.Alert(
                "All fields are required.",
                title="Validation Error",
                color="red"
            )
        
        if new_password != confirm_password:
            return dmc.Alert(
                "New passwords do not match.",
                title="Validation Error",
                color="red"
            )
        
        if len(new_password) < 6:
            return dmc.Alert(
                "New password must be at least 6 characters long.",
                title="Validation Error",
                color="red"
            )
        
        # Change password
        success = auth_service.change_password(current_password, new_password)
        
        if success:
            return dmc.Alert(
                "Password changed successfully.",
                title="Success",
                color="green"
            )
        else:
            return dmc.Alert(
                "Failed to change password. Current password may be incorrect.",
                title="Error",
                color="red"
            )
    
    return no_update


# Callback for handling user deactivation



# Callback for bulk change password (admin only - changes their own password)
@callback(
    Output("change-password-modal", "opened", allow_duplicate=True),
    Input("bulk-change-password-btn", "n_clicks"),
    prevent_initial_call=True
)
def open_admin_password_change(n_clicks):
    """Open password change modal for the current admin."""
    if n_clicks:
        return True
    return no_update


# Callback for bulk delete selected users
@callback(
    Output("users-table-container", "children", allow_duplicate=True),
    Input("bulk-delete-btn", "n_clicks"),
    State("users-grid", "selectedRows"),
    prevent_initial_call=True
)
def handle_bulk_delete(n_clicks, selected_rows):
    """Handle bulk deletion of selected users."""
    if not n_clicks or not selected_rows:
        return no_update
    
    current_user = auth_service.get_current_user()
    current_user_id = current_user['id'] if current_user else None
    
    # Delete selected users (but not admins or current user)
    deleted_count = 0
    skipped_count = 0
    
    for row in selected_rows:
        user_id = row.get('id')
        is_admin = row.get('is_admin_bool', False)
        
        # Skip deletion if it's the current user or an admin
        if user_id == current_user_id or is_admin:
            skipped_count += 1
            continue
            
        success = auth_service.delete_user_by_admin(user_id)
        if success:
            deleted_count += 1
    
    # Refresh the users table
    users = auth_service.list_all_users()
    if not users:
        return dmc.Text("No users found.", c="dimmed")
    
    return create_ag_grid_table(users)


# Callback to sync AG Grid theme with color scheme
@callback(Output('users-grid', 'className'), Input('color-scheme-switch', 'checked'))
def sync_users_grid_theme(is_dark):
    return 'ag-theme-alpine-dark' if is_dark else 'ag-theme-alpine'


# Callback to enable/disable delete button based on selected users
@callback(
    Output('bulk-delete-btn', 'disabled'),
    Input('users-grid', 'selectedRows')
)
def update_delete_button_state(selected_rows):
    """Enable delete button only if non-admin users are selected."""
    if not selected_rows:
        return True  # Disable if nothing selected
    
    current_user = auth_service.get_current_user()
    current_user_id = current_user['id'] if current_user else None
    
    # Check if any selected user is an admin or the current user
    for row in selected_rows:
        user_id = row.get('id')
        is_admin = row.get('is_admin_bool', False)
        
        # If current user is selected or any admin is selected, disable delete
        if user_id == current_user_id or is_admin:
            return True
    
    return False  # Enable if only non-admin users (and not current user) are selected


