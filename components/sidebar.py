import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback
from components.bootstrap_icon import BootstrapIcon
from services.auth_middleware import check_authentication_status, should_show_admin_features, get_current_username


def build_sidebar():
    return html.Nav(
        id="sidebar",
        children=[
            html.Nav(
                id="sidebar-nav",
                className="mt-2 flex-grow-1",
                children=[
                    # Main Navigation
                    html.Div(
                        className="sidebar-top",
                        children=[
                            html.A([
                                BootstrapIcon(icon="house", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Home", className="nav-label sb-label"),
                            ], href="/", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="arrow-repeat", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Fluid ID Converter", className="nav-label sb-label"),
                            ], href="/fluid-id-converter", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="clock-history", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "SPS Time Converter", className="nav-label sb-label"),
                            ], href="/sps-time-converter", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="file-binary", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "CSV to RTU", className="nav-label sb-label"),
                            ], href="/csv-to-rtu", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="filetype-csv", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "RTU to CSV", className="nav-label sb-label"),
                            ], href="/rtu-to-csv", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="scissors", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "RTU Resizer | Retagger", className="nav-label sb-label"),
                            ], href="/rtu-resizer", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="filetype-csv", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Review to CSV", className="nav-label sb-label"),
                            ], href="/review-to-csv", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="cloud-download", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Fetch Archive", className="nav-label sb-label"),
                            ], href="/fetch-archive", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="cloud-download-fill", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Fetch RTU Data", className="nav-label sb-label"),
                            ], href="/fetch-rtu-data", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="graph-up", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Elevation Tool", className="nav-label sb-label"),
                            ], href="/elevation", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="file-earmark-text", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Linefill Data", className="nav-label sb-label"),
                            ], href="/linefill", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="droplet", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Fluid Properties", className="nav-label sb-label"),
                            ], href="/fluid-properties", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="search-heart", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Replace Text", className="nav-label sb-label"),
                            ], href="/replace-text", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="funnel-fill", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Replay Poke Extractor", className="nav-label sb-label"),
                            ], href="/replay-poke-extractor", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="gear-wide-connected", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "PyMBSd Services", className="nav-label sb-label"),
                            ], href="/pymbsd-services", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="speedometer2", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Flowmeter Acceptance", className="nav-label sb-label"),
                            ], href="/flowmeter-acceptance", className="nav-link"),
                        ],
                    ),
                    
                    # License Information at bottom
                    html.Div(
                        className="sidebar-bottom mt-auto",
                        children=[
                            html.Div(
                                style={
                                    "borderTop": "1px solid rgba(255,255,255,0.1)",
                                    "margin": "8px 16px",
                                    "marginBottom": "12px"
                                }
                            ),
                            html.A([
                                BootstrapIcon(icon="award", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "License Information", className="nav-label sb-label"),
                            ], id="license-info-btn", className="nav-link", style={"cursor": "pointer"}),
                        ],
                        style={"marginTop": "auto"}
                    ),
                ]
            )
        ],
    )


# Sidebar callbacks removed - user menu now handled in separate component
