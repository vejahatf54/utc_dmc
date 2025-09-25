"""
License Management Page Component

Provides UI for viewing license information and entering license keys.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, dcc, no_update
from datetime import datetime
import json
from services.license_service import license_service, LicenseStatus
from components.bootstrap_icon import BootstrapIcon


def create_license_page():
    """Create the license management page"""
    
    license_info = license_service.get_current_license()
    
    return html.Div([
        dcc.Store(id="license-store", data={}),
        
        # Page Header
        dmc.Paper([
            dmc.Group([
                BootstrapIcon("award-fill", width=32, color="blue"),
                dmc.Title("License Management", order=2)
            ], gap="md"),
            dmc.Text("Manage your WUTC application license", color="dimmed")
        ], p="md", mb="lg"),
        
        # Current License Status
        html.Div(id="license-status-section"),
        
        # License Key Entry (only show if needed)
        html.Div(id="license-entry-section"),
        
        # License Information
        html.Div(id="license-info-section"),
        
        # Alerts
        html.Div(id="license-alerts")
    ])


def create_license_status_card(license_info):
    """Create a card showing current license status"""
    
    if not license_info:
        return dmc.Alert(
            "Unable to load license information",
            title="Error",
            color="red",
            mb="lg"
        )
    
    # Determine status color and icon
    if license_info.status == LicenseStatus.VALID:
        status_color = "green"
        status_icon = "check-circle-fill"
        status_text = "Valid"
    elif license_info.status == LicenseStatus.EXPIRED:
        status_color = "red"
        status_icon = "x-circle-fill"
        status_text = "Expired"
    elif license_info.status == LicenseStatus.CORRUPTED:
        status_color = "orange"
        status_icon = "exclamation-triangle-fill"
        status_text = "Corrupted"
    else:
        status_color = "gray"
        status_icon = "question-circle-fill"
        status_text = "Unknown"
    
    # License type badge color
    type_colors = {
        "trial": "orange",
        "standard": "blue",
        "professional": "purple",
        "enterprise": "green"
    }
    type_color = type_colors.get(license_info.license_type.value, "gray")
    
    return dmc.Paper([
        dmc.Group([
            dmc.Group([
                BootstrapIcon(status_icon, size=24, color=status_color),
                dmc.Title(f"License Status: {status_text}", order=3)
            ], gap="sm"),
            dmc.Badge(
                license_info.license_type.value.title(),
                color=type_color,
                size="lg"
            )
        ], justify="space-between", mb="md"),
        
        dmc.SimpleGrid([
            dmc.Stack([
                dmc.Text("Company", size="sm", c="dimmed"),
                dmc.Text(license_info.company_name or "Not specified", weight=500)
            ], gap="xs"),
            
            dmc.Stack([
                dmc.Text("Licensed To", size="sm", c="dimmed"),
                dmc.Text(license_info.licensed_to or "Not specified", weight=500)
            ], gap="xs"),
            
            dmc.Stack([
                dmc.Text("Max Users", size="sm", c="dimmed"),
                dmc.Text(str(license_info.max_users), weight=500)
            ], gap="xs"),
            
            dmc.Stack([
                dmc.Text("Expires", size="sm", c="dimmed"),
                dmc.Text(
                    license_info.expires_at.strftime("%Y-%m-%d") if license_info.expires_at else "Never",
                    weight=500,
                    c="red" if license_info.status == LicenseStatus.EXPIRED else None
                )
            ], gap="xs")
        ], cols=2, spacing="md"),
        
        # Days remaining warning
        html.Div([
            dmc.Alert(
                f"Your license will expire in {license_info.days_remaining} days.",
                title="License Expiring Soon",
                color="yellow",
                mt="md"
            ) if license_info.days_remaining and license_info.days_remaining <= 30 else None,
            
            dmc.Alert(
                "Your license has expired. Please contact support to renew.",
                title="License Expired",
                color="red",
                mt="md"
            ) if license_info.status == LicenseStatus.EXPIRED else None,
            
            dmc.Alert(
                "You are using a trial license with limited features.",
                title="Trial License",
                color="orange",
                mt="md"
            ) if license_info.is_trial else None
        ])
        
    ], p="md", mb="lg")


def create_license_entry_form():
    """Create the license key entry form"""
    
    return dmc.Paper([
        dmc.Title("Enter License Key", order=4, mb="md"),
        dmc.Text("Enter your license key to unlock full features", size="sm", c="dimmed", mb="md"),
        
        dmc.TextInput(
            id="license-key-input",
            label="License Key",
            placeholder="Enter your license key here...",
            style={"width": "100%"},
            mb="md"
        ),
        
        dmc.Group([
            dmc.Button(
                "Validate License",
                id="validate-license-btn",
                leftSection=BootstrapIcon("key-fill"),
                color="blue"
            ),
            dmc.Button(
                "Clear",
                id="clear-license-btn",
                variant="outline",
                color="gray"
            )
        ], gap="sm")
        
    ], p="md", mb="lg")


def create_features_list(license_info):
    """Create a list of enabled/disabled features"""
    
    if not license_info or not license_info.features:
        return html.Div()
    
    feature_items = []
    
    feature_names = {
        "basic_functionality": "Basic Functionality",
        "advanced_reports": "Advanced Reports",
        "api_access": "API Access",
        "multi_user": "Multi-User Support",
        "premium_support": "Premium Support",
        "custom_features": "Custom Features"
    }
    
    for feature_key, enabled in license_info.features.items():
        feature_name = feature_names.get(feature_key, feature_key.replace("_", " ").title())
        
        feature_items.append(
            dmc.Group([
                BootstrapIcon(
                    "check-circle-fill" if enabled else "x-circle",
                    color="green" if enabled else "gray"
                ),
                dmc.Text(feature_name, c="dimmed" if not enabled else None)
            ], gap="sm")
        )
    
    return dmc.Paper([
        dmc.Title("Available Features", order=4, mb="md"),
        dmc.Stack(feature_items, gap="sm")
    ], p="md")


@callback(
    Output("license-status-section", "children"),
    Output("license-entry-section", "children"),
    Output("license-info-section", "children"),
    Input("license-store", "data")
)
def update_license_display(_):
    """Update the license display sections"""
    
    license_info = license_service.get_current_license()
    
    # Status section
    status_section = create_license_status_card(license_info)
    
    # Entry section (show only if trial or invalid)
    entry_section = html.Div()
    if license_info and (license_info.is_trial or license_info.status != LicenseStatus.VALID):
        entry_section = create_license_entry_form()
    
    # Info section
    info_section = create_features_list(license_info)
    
    return status_section, entry_section, info_section


@callback(
    Output("license-alerts", "children"),
    Output("license-store", "data"),
    Input("validate-license-btn", "n_clicks"),
    State("license-key-input", "value"),
    prevent_initial_call=True
)
def validate_license_key(n_clicks, license_key):
    """Validate and apply a license key"""
    
    if not n_clicks or not license_key:
        return html.Div(), {}
    
    try:
        # Validate the license key
        is_valid, license_data = license_service.validate_license_key(license_key.strip())
        
        if is_valid:
            # Save the license
            if license_service.save_license(license_data):
                # Reload the license
                license_service._current_license = None
                new_license = license_service.load_license()
                
                return dmc.Alert(
                    f"License key validated successfully! License type: {new_license.license_type.value.title()}",
                    title="Success",
                    color="green",
                    mb="lg"
                ), {"updated": True}
            else:
                return dmc.Alert(
                    "Valid license key, but failed to save license file.",
                    title="Error",
                    color="red",
                    mb="lg"
                ), {}
        else:
            return dmc.Alert(
                "Invalid license key. Please check your key and try again.",
                title="Invalid License",
                color="red",
                mb="lg"
            ), {}
            
    except Exception as e:
        return dmc.Alert(
            f"Error validating license: {str(e)}",
            title="Error",
            color="red",
            mb="lg"
        ), {}


@callback(
    Output("license-key-input", "value"),
    Input("clear-license-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_license_input(n_clicks):
    """Clear the license key input"""
    if n_clicks:
        return ""
    return no_update