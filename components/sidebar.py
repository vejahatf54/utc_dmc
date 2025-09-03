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
                                DashIconify(icon="noto:gear", width=24,
                                            height=24, className="nav-icon"),
                                html.Span(
                                    "Fluid ID Converter", className="nav-label sb-label"),
                            ], href="/fluid-id-converter", className="nav-link"),
                            html.A([
                                DashIconify(icon="noto:page-with-curl", width=24,
                                            height=24, className="nav-icon"),
                                html.Span(
                                    "CSV to RTU", className="nav-label sb-label"),
                            ], href="/csv-to-rtu", className="nav-link"),
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
