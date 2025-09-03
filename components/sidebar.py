import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html


def build_sidebar():
    return html.Nav(
        id="sidebar",
        children=[
            html.Div(
                className="sidebar-top",
                children=[
                    html.A([
                        DashIconify(icon="radix-icons:home", width=24,
                                    height=24, className="nav-icon"),
                        html.Span("Home", className="nav-label"),
                    ], href="/", className="nav-link"),
                ],
            ),
            html.Div(
                className="sidebar-bottom",
                children=[
                    html.A([
                        DashIconify(icon="radix-icons:gear", width=24,
                                    height=24, className="nav-icon"),
                        html.Span("Settings", className="nav-label"),
                    ], href="/settings", className="nav-link"),
                ],
            ),
        ],
    )
