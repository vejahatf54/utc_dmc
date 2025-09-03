import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import Dash, Input, Output, dcc, html, clientside_callback
from components.sidebar import build_sidebar

app = Dash(__name__)

# Theme toggle switch (kept) - we'll place it near bottom above Settings link
theme_toggle = dmc.Switch(
    offLabel=DashIconify(icon="radix-icons:sun", width=15,
                         color=dmc.DEFAULT_THEME["colors"]["yellow"][8]),
    onLabel=DashIconify(icon="radix-icons:moon", width=15,
                        color=dmc.DEFAULT_THEME["colors"]["yellow"][6]),
    id="color-scheme-switch",
    persistence=True,
    color="gray",
    size="md",
)

sidebar = build_sidebar()

# Main content container; content will be swapped by callback
content = html.Div(id="page-content", className="page-content")

app.layout = dmc.MantineProvider(
    html.Div(
        id="app-shell",
        children=[
            dcc.Location(id="url"),
            sidebar,
            html.Div(
                [
                    html.Div(theme_toggle, className="theme-toggle-topright"),
                    content
                ],
                className="main-content-shell"
            )
        ],
        className="app-shell",
    )
)

# Client-side callback for color scheme switching
clientside_callback(
    """
    (switchOn) => {
       document.documentElement.setAttribute('data-mantine-color-scheme', switchOn ? 'dark' : 'light');
       return window.dash_clientside.no_update
    }
    """,
    Output("color-scheme-switch", "id"),
    Input("color-scheme-switch", "checked"),
)

# Server side callback for routing


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page(pathname: str):
    if pathname in ("/", ""):
        return dmc.Stack([
            dmc.Title("Home", order=2),
            dmc.Text("Welcome to the Home page."),
        ], gap="md")
    if pathname == "/settings":
        return dmc.Stack([
            dmc.Title("Settings", order=2),
            dmc.Text("Adjust your preferences here."),
        ], gap="md")
    return dmc.Stack([
        dmc.Title("404", order=2),
        dmc.Text(f"Page '{pathname}' not found."),
    ], gap="md")


if __name__ == "__main__":
    app.run(debug=True)
