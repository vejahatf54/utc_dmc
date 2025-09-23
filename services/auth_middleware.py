"""
Authentication Middleware for WUTC application.
Handles route protection and authentication checks.
"""

from functools import wraps
from dash import callback_context, no_update
from services.auth_service import auth_service
from components.login_page import create_login_page
from logging_config import get_logger

logger = get_logger(__name__)


def require_auth(func):
    """
    Decorator to require authentication for a route or callback.
    
    Args:
        func: The function to protect
        
    Returns:
        Wrapped function that checks authentication
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not auth_service.require_authentication():
            logger.info("Unauthenticated access attempt, redirecting to login")
            return create_login_page()
        return func(*args, **kwargs)
    return wrapper


def require_admin(func):
    """
    Decorator to require admin privileges for a route or callback.
    
    Args:
        func: The function to protect
        
    Returns:
        Wrapped function that checks admin privileges
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not auth_service.require_admin():
            logger.warning("Unauthorized admin access attempt")
            # Return access denied page or redirect
            return create_access_denied_page()
        return func(*args, **kwargs)
    return wrapper


def create_access_denied_page():
    """Create an access denied page for unauthorized users."""
    import dash_mantine_components as dmc
    from dash import html
    
    return dmc.Container([
        dmc.Center([
            dmc.Paper([
                dmc.Stack([
                    dmc.ThemeIcon(
                        html.I(className="bi bi-shield-x"),
                        size="xl",
                        color="red",
                        variant="light"
                    ),
                    dmc.Title("Access Denied", order=2, ta="center"),
                    dmc.Text(
                        "You don't have permission to access this page. Admin privileges are required.",
                        ta="center", c="dimmed"
                    ),
                    dmc.Button(
                        "Return to Home",
                        component="a",
                        href="/",
                        color="green",
                        fullWidth=True
                    )
                ], align="center", gap="md")
            ], shadow="md", p="xl", radius="md", style={"width": "400px"})
        ])
    ], size="sm", style={"height": "100vh", "display": "flex", "alignItems": "center"})


def check_authentication_status():
    """
    Check current authentication status.
    
    Returns:
        Dict with authentication information
    """
    return {
        'is_authenticated': auth_service.is_authenticated(),
        'is_admin': auth_service.is_admin(),
        'must_change_password': auth_service.must_change_password(),
        'current_user': auth_service.get_current_user(),
        'session_info': auth_service.get_session_info()
    }


def require_password_change_check(func):
    """
    Decorator that redirects to password change page if required.
    Should be used after require_auth but before the main function.
    
    Args:
        func: The function to protect
        
    Returns:
        Wrapped function that checks for forced password change
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Skip password change check for login and password change pages
        ctx = callback_context
        if ctx and ctx.inputs:
            # Get the current pathname from context if available
            pathname = None
            for input_item in ctx.inputs:
                if 'pathname' in str(input_item):
                    pathname = input_item.get('value', '')
                    break
            
            # Allow access to login and password change pages
            if pathname in ['/', '/login', '/change-password']:
                return func(*args, **kwargs)
        
        if auth_service.is_authenticated() and auth_service.must_change_password():
            logger.info("User must change password, redirecting")
            return create_password_change_page()
        
        return func(*args, **kwargs)
    return wrapper


def create_password_change_page():
    """Create a forced password change page."""
    import dash_mantine_components as dmc
    from dash import html
    
    return dmc.Container([
        dmc.Center([
            dmc.Paper([
                dmc.Stack([
                    dmc.ThemeIcon(
                        html.I(className="bi bi-key-fill"),
                        size="xl",
                        color="orange",
                        variant="light"
                    ),
                    dmc.Title("Password Change Required", order=2, ta="center"),
                    dmc.Text(
                        "You must change your password before continuing to use the application.",
                        ta="center", c="dimmed", mb="md"
                    ),
                    
                    # Password change form
                    dmc.PasswordInput(
                        id="forced-new-password",
                        label="New Password",
                        placeholder="Enter your new password",
                        required=True,
                        size="md"
                    ),
                    
                    dmc.PasswordInput(
                        id="forced-confirm-password",
                        label="Confirm New Password",
                        placeholder="Confirm your new password",
                        required=True,
                        size="md"
                    ),
                    
                    # Error/success message area
                    html.Div(id="forced-password-message"),
                    
                    dmc.Button(
                        "Change Password",
                        id="forced-password-submit",
                        color="green",
                        fullWidth=True,
                        size="md"
                    )
                ], align="stretch", gap="md")
            ], shadow="md", p="xl", radius="md", style={"width": "400px"})
        ])
    ], size="sm", style={"height": "100vh", "display": "flex", "alignItems": "center"})


def get_protected_content(pathname, regular_content_func):
    """
    Get content for a protected route.
    
    Args:
        pathname: The current pathname
        regular_content_func: Function to call if user is authenticated
        
    Returns:
        Either the regular content, forced password change, or login page
    """
    if not auth_service.is_authenticated():
        logger.info(f"Unauthenticated access to {pathname}")
        return create_login_page()
    
    # Check if user must change password (except for login and password change pages)
    if auth_service.must_change_password() and pathname not in ["/", "/login", "/change-password"]:
        logger.info(f"User must change password, redirecting from {pathname}")
        from components.password_change_page import create_forced_password_change_page
        return create_forced_password_change_page()
    
    return regular_content_func()


def get_admin_protected_content(pathname, admin_content_func):
    """
    Get content for an admin-protected route.
    
    Args:
        pathname: The current pathname
        admin_content_func: Function to call if user is admin
        
    Returns:
        Either the admin content, access denied, or login page
    """
    if not auth_service.is_authenticated():
        logger.info(f"Unauthenticated access to admin route {pathname}")
        return create_login_page()
    
    if not auth_service.is_admin():
        logger.warning(f"Non-admin access attempt to {pathname}")
        return create_access_denied_page()
    
    return admin_content_func()


def get_user_protected_content(pathname, user_content_func):
    """
    Get content for a user-protected route (authenticated users only).
    Does not check for forced password changes since this is likely the password change page.
    
    Args:
        pathname: The current pathname
        user_content_func: Function to call if user is authenticated
        
    Returns:
        Either the user content or login page
    """
    if not auth_service.is_authenticated():
        logger.info(f"Unauthenticated access to user route {pathname}")
        return create_login_page()
    
    # For password change page, use forced version if required
    if pathname == "/change-password" and auth_service.must_change_password():
        from components.password_change_page import create_forced_password_change_page
        return create_forced_password_change_page()
    
    return user_content_func()


def should_show_admin_features():
    """
    Check if admin features should be shown in the UI.
    
    Returns:
        True if current user is admin
    """
    return auth_service.is_admin()


def get_current_username():
    """
    Get the current authenticated username.
    
    Returns:
        Username if authenticated, None otherwise
    """
    user = auth_service.get_current_user()
    return user['username'] if user else None