import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html


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
                                DashIconify(icon="noto:house", width=24,
                                            height=24, className="nav-icon"),
                                html.Span(
                                    "Home", className="nav-label sb-label"),
                            ], href="/", className="nav-link"),
                            html.A([
                                DashIconify(icon="tabler:arrows-exchange", width=24,
                                            height=24, className="nav-icon"),
                                html.Span(
                                    "Fluid ID Converter", className="nav-label sb-label"),
                            ], href="/fluid-id-converter", className="nav-link"),
                        ],
                    ),

                    # Bottom section for Settings
                    html.Div(
                        className="sidebar-bottom",
                        children=[
                            html.A([
                                DashIconify(icon="noto:gear", width=24,
                                            height=24, className="nav-icon"),
                                html.Span(
                                    "Settings", className="nav-label sb-label"),
                            ], href="/settings", className="nav-link"),
                        ],
                    ),
                ]
            )
        ],
    )
