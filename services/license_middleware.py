"""
License Middleware for WUTC Application

This middleware handles license-based feature restrictions and provides
decorators for protecting premium features.
"""

from functools import wraps
from typing import Callable, Any
from dash import html
import dash_mantine_components as dmc
from services.license_service import license_service, LicenseStatus
from components.bootstrap_icon import BootstrapIcon


def license_required(feature_name: str = None):
    """
    Decorator that restricts access to features based on license
    
    Args:
        feature_name: The specific feature to check. If None, just checks for valid license.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            license_info = license_service.get_current_license()
            
            # Check if license exists and is valid
            if not license_info or license_info.status != LicenseStatus.VALID:
                return create_license_required_message("A valid license is required to access this feature.")
            
            # Check specific feature if specified
            if feature_name and not license_service.is_feature_enabled(feature_name):
                return create_license_upgrade_message(
                    f"The '{feature_name.replace('_', ' ').title()}' feature requires a license upgrade."
                )
            
            # License check passed, call the original function
            return func(*args, **kwargs)
        return wrapper
    return decorator


def premium_feature(feature_name: str):
    """
    Decorator specifically for premium features that require non-trial licenses
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            license_info = license_service.get_current_license()
            
            # Check if license exists and is valid
            if not license_info or license_info.status != LicenseStatus.VALID:
                return create_license_required_message("A valid license is required to access this premium feature.")
            
            # Check if it's a trial license
            if license_info.is_trial:
                return create_license_upgrade_message(
                    f"The '{feature_name.replace('_', ' ').title()}' feature is not available in the trial version."
                )
            
            # Check specific feature
            if not license_service.is_feature_enabled(feature_name):
                return create_license_upgrade_message(
                    f"The '{feature_name.replace('_', ' ').title()}' feature requires a license upgrade."
                )
            
            # License check passed, call the original function
            return func(*args, **kwargs)
        return wrapper
    return decorator


def create_license_required_message(message: str = None):
    """Create a standard license required message"""
    if not message:
        message = "A valid license is required to access this feature."
    
    return dmc.Container([
        dmc.Paper([
            dmc.Stack([
                dmc.Group([
                    BootstrapIcon("shield-exclamation", size=48, color="orange"),
                    dmc.Title("License Required", order=2, c="orange")
                ], justify="center", gap="md"),
                
                dmc.Text(
                    message,
                    ta="center",
                    size="lg",
                    c="dimmed"
                ),
                
                dmc.Group([
                    dmc.Button(
                        "View License Information",
                        leftSection=BootstrapIcon("award-fill"),
                        variant="outline",
                        color="blue",
                        component="a",
                        href="/admin/license"
                    ),
                    dmc.Button(
                        "Contact Support",
                        leftSection=BootstrapIcon("envelope-fill"),
                        color="green",
                        component="a",
                        href="mailto:support@example.com",
                        target="_blank"
                    )
                ], justify="center", gap="md")
            ], align="center", gap="xl")
        ], p="xl", shadow="sm", radius="md")
    ], size="sm", mt="xl")


def create_license_upgrade_message(message: str = None):
    """Create a standard license upgrade message"""
    if not message:
        message = "This feature requires a license upgrade."
    
    return dmc.Container([
        dmc.Paper([
            dmc.Stack([
                dmc.Group([
                    BootstrapIcon("gem", size=48, color="purple"),
                    dmc.Title("Premium Feature", order=2, c="purple")
                ], justify="center", gap="md"),
                
                dmc.Text(
                    message,
                    ta="center",
                    size="lg",
                    c="dimmed"
                ),
                
                dmc.Text(
                    "Upgrade your license to unlock this and other premium features.",
                    ta="center",
                    size="sm",
                    c="dimmed"
                ),
                
                dmc.Group([
                    dmc.Button(
                        "View License Information",
                        leftSection=BootstrapIcon("award-fill"),
                        variant="outline",
                        color="blue",
                        component="a",
                        href="/admin/license"
                    ),
                    dmc.Button(
                        "Upgrade License",
                        leftSection=BootstrapIcon("arrow-up-circle-fill"),
                        color="purple",
                        component="a",
                        href="mailto:sales@example.com?subject=License Upgrade Request",
                        target="_blank"
                    )
                ], justify="center", gap="md")
            ], align="center", gap="xl")
        ], p="xl", shadow="sm", radius="md")
    ], size="sm", mt="xl")


def get_license_banner():
    """Get a license status banner for display"""
    license_info = license_service.get_current_license()
    
    if not license_info:
        return None
    
    # Show banner for trial licenses
    if license_info.is_trial and license_info.status == LicenseStatus.VALID:
        if license_info.days_remaining <= 7:
            color = "red"
            message = f"Trial expires in {license_info.days_remaining} days!"
        elif license_info.days_remaining <= 14:
            color = "orange"
            message = f"Trial expires in {license_info.days_remaining} days"
        else:
            return None  # Don't show banner if more than 14 days left
        
        return dmc.Alert([
            dmc.Text(message),
            html.Br(),
            dmc.Anchor("View License Details", href="/license-info", c="blue", td="underline")
        ],
            title="Trial License",
            color=color,
            mb="sm"
        )
    
    # Show banner for expired licenses
    elif license_info.status == LicenseStatus.EXPIRED:
        return dmc.Alert([
            dmc.Text("Your license has expired. Some features may be unavailable."),
            html.Br(),
            dmc.Anchor("View License Details", href="/license-info", c="blue", td="underline")
        ],
            title="License Expired",
            color="red",
            mb="sm"
        )
    
    # Show banner for corrupted licenses
    elif license_info.status == LicenseStatus.CORRUPTED:
        return dmc.Alert([
            dmc.Text("License file is corrupted. Please contact support."),
            html.Br(),
            dmc.Anchor("View License Details", href="/license-info", c="blue", td="underline")
        ],
            title="License Error",
            color="red",
            mb="sm"
        )
    
    return None


def check_feature_access(feature_name: str) -> dict:
    """
    Check if a feature is accessible under the current license
    
    Returns:
        dict with keys: 'accessible' (bool), 'reason' (str), 'license_type' (str)
    """
    license_info = license_service.get_current_license()
    
    if not license_info:
        return {
            'accessible': False,
            'reason': 'No license found',
            'license_type': 'none'
        }
    
    if license_info.status != LicenseStatus.VALID:
        return {
            'accessible': False,
            'reason': f'License is {license_info.status.value}',
            'license_type': license_info.license_type.value
        }
    
    if feature_name and not license_service.is_feature_enabled(feature_name):
        return {
            'accessible': False,
            'reason': f'Feature not included in {license_info.license_type.value} license',
            'license_type': license_info.license_type.value
        }
    
    return {
        'accessible': True,
        'reason': 'Feature accessible',
        'license_type': license_info.license_type.value
    }