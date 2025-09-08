import dash_mantine_components as dmc
from dash import html
from components.bootstrap_icon import BootstrapIcon


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
                                BootstrapIcon(icon="file-text", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "CSV to RTU", className="nav-label sb-label"),
                            ], href="/csv-to-rtu", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="cloud-download", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Fetch Archive", className="nav-label sb-label"),
                            ], href="/fetch-archive", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="database", width=24,
                                              height=24, className="nav-icon"),
                                html.Span(
                                    "Fetch RTU Data", className="nav-label sb-label"),
                            ], href="/fetch-rtu-data", className="nav-link"),
                            html.A([
                                BootstrapIcon(icon="activity", width=24,
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
                        ],
                    ),

                    # Bottom section - can be used for other items if needed
                    html.Div(
                        className="sidebar-bottom",
                        children=[
                            # Settings removed - now accessible via modal in top-right
                        ],
                    ),
                ]
            )
        ],
    )
