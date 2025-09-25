"""
License Information Page for WUTC Application

This page provides users with detailed information about their current license,
including status, features, expiration dates, and other relevant details.
"""

import dash_mantine_components as dmc
from dash import html, dcc
from components.bootstrap_icon import BootstrapIcon
from services.license_service import license_service
from datetime import datetime


def create_license_info_page():
    """Create the license information page"""
    
    license_info = license_service.get_current_license()
    
    return html.Div([
        dcc.Store(id="license-info-store", data={}),
        
        # Page Header
        dmc.Container([
            dmc.Group([
                BootstrapIcon("award-fill", width=32),
                dmc.Title("License Information", order=1)
            ], gap="md", mb="lg"),
            
            dmc.Text(
                "View your current WUTC application license details and status",
                size="lg",
                c="dimmed",
                mb="xl"
            ),
            
            # License Status Cards
            create_license_status_cards(license_info),
            
            # Feature Access Information
            html.Div(id="license-features-section"),
            
        ], size="lg", py="xl")
    ])


def create_license_status_cards(license_info):
    """Create license status cards"""
    
    if not license_info:
        return dmc.Alert(
            "No valid license found. The application is running in limited mode.",
            title="No License",
            color="red",
            icon=BootstrapIcon("exclamation-triangle-fill", width=20),
            mb="lg"
        )
    
    # Determine colors and icons based on license status
    if license_info.status.value == "valid":
        if license_info.is_trial:
            if license_info.days_remaining <= 7:
                status_color = "red"
                status_icon = "exclamation-triangle-fill"
                status_text = "Trial Expiring Soon"
            elif license_info.days_remaining <= 14:
                status_color = "orange"
                status_icon = "clock-fill"
                status_text = "Trial Active"
            else:
                status_color = "blue"
                status_icon = "clock"
                status_text = "Trial Active"
        else:
            status_color = "green"
            status_icon = "check-circle-fill"
            status_text = "License Active"
    elif license_info.status.value == "expired":
        status_color = "red"
        status_icon = "x-circle-fill"
        status_text = "License Expired"
    else:
        status_color = "yellow"
        status_icon = "exclamation-triangle-fill"
        status_text = "License Issue"
    
    # Main license status card
    main_card = dmc.Card([
        dmc.Group([
            BootstrapIcon(status_icon, width=24, color=status_color),
            dmc.Stack([
                dmc.Title(status_text, order=3, c=status_color),
                dmc.Text(f"Server: {license_info.licensed_to}", size="sm", c="dimmed")
            ], gap="xs")
        ], gap="md"),
        
        dmc.Divider(my="md"),
        
        dmc.SimpleGrid([
            # Licensed Server
            dmc.Stack([
                dmc.Text("Licensed Server", size="sm", fw=600, c="dimmed"),
                dmc.Group([
                    BootstrapIcon("server", width=16),
                    dmc.Text(license_info.licensed_to, fw=500)
                ], gap="xs")
            ], gap="xs"),
            
            # Issue Date
            dmc.Stack([
                dmc.Text("Issue Date", size="sm", fw=600, c="dimmed"),
                dmc.Group([
                    BootstrapIcon("calendar-plus", width=16),
                    dmc.Text(license_info.issued_at.strftime("%Y-%m-%d"), fw=500)
                ], gap="xs")
            ], gap="xs"),
            
            # Expiration
            dmc.Stack([
                dmc.Text("Expiration", size="sm", fw=600, c="dimmed"),
                dmc.Group([
                    BootstrapIcon("calendar-x" if license_info.expires_at else "infinity", width=16),
                    dmc.Text(
                        license_info.expires_at.strftime("%Y-%m-%d") if license_info.expires_at else "Never",
                        fw=500,
                        c="red" if license_info.status.value == "expired" else "inherit"
                    )
                ], gap="xs")
            ], gap="xs"),
            
        ], cols=3, spacing="md"),
        
    ], shadow="sm", padding="lg", radius="md")
    
    cards = [main_card]
    
    # Add expiration warning card if needed
    if license_info.expires_at and license_info.days_remaining is not None:
        if license_info.days_remaining <= 30 and license_info.days_remaining > 0:
            warning_card = dmc.Alert(
                f"Your license will expire in {license_info.days_remaining} days on {license_info.expires_at.strftime('%Y-%m-%d')}. "
                "Please renew your license to continue using all features.",
                title="License Expiring Soon",
                color="orange" if license_info.days_remaining > 7 else "red",
                icon=BootstrapIcon("clock-fill", width=20),
                mt="md"
            )
            cards.append(warning_card)
        elif license_info.days_remaining <= 0:
            expired_card = dmc.Alert(
                f"Your license expired on {license_info.expires_at.strftime('%Y-%m-%d')}. "
                "Some features may be unavailable until you renew your license.",
                title="License Expired",
                color="red",
                icon=BootstrapIcon("x-circle-fill", width=20),
                mt="md"
            )
            cards.append(expired_card)
    
    return dmc.Stack(cards, gap="md")



def create_license_help_section():
    """Create a help section with license information"""
    
    return dmc.Card([
        dmc.Group([
            BootstrapIcon("question-circle-fill", width=20, color="blue"),
            dmc.Title("Need Help?", order=4)
        ], gap="md", mb="md"),
        
        dmc.Stack([
            dmc.Text("If you need to:", fw=500),
            
            dmc.List([
                dmc.ListItem("Upgrade your license"),
                dmc.ListItem("Renew an expired license"),
                dmc.ListItem("Transfer license to a new server"),
                dmc.ListItem("Report license issues")
            ]),
            
            dmc.Text("Contact your system administrator or use the standalone License Manager tool.", mt="sm"),
            
            dmc.Group([
                dmc.Badge("License Manager", color="blue", variant="light"),
                dmc.Text("Available in the application directory", size="sm", c="dimmed")
            ], gap="xs", mt="sm")
            
        ], gap="xs")
        
    ], shadow="sm", padding="lg", radius="md", mt="md")