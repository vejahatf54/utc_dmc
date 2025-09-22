"""
SPS Time Converter page component for WUTC application.
Uses pure Dash Mantine components with default theme styling.
Based on UcSpsTimeConverter from UTC_Core project.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context
from components.bootstrap_icon import BootstrapIcon
from services.sps_time_converter_service import SpsTimeConverterService
from datetime import datetime


def create_sps_time_converter_page():
    """Create the SPS Time Converter page layout."""
    return dmc.Container([
        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("SPS Time Converter", order=1, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="sps-help-modal-btn",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Real-time bidirectional conversion between SPS Unix Timestamp and DateTime",
                             c="dimmed", ta="center", size="lg")
                ], gap="xs")
            ]),

            # Help Modal
            dmc.Modal(
                title="How It Works",
                id="sps-help-modal",
                children=[
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="info-circle", width=20),
                                    dmc.Text("Conversion Logic", fw=500)
                                ], gap="xs"),
                                dmc.Text([
                                    "The SPS (Supervisory Process System) uses a custom Unix timestamp system ",
                                    "with epoch starting at December 31, 1967 00:00:00 UTC. The timestamp is ",
                                    "stored in minutes since this epoch, providing precise time tracking for ",
                                    "industrial process control systems."
                                ], size="sm", c="dimmed")
                            ])
                        ], span=6),
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="lightbulb", width=20),
                                    dmc.Text("Usage Tips", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem("Enter values in either field for automatic conversion"),
                                    dmc.ListItem("SPS timestamp is in minutes since 1967-12-31"),
                                    dmc.ListItem("DateTime format: YYYY/MM/DD HH:MM:SS"),
                                    dmc.ListItem("Times use standard timezone (ignores daylight saving time)"),
                                    dmc.ListItem("Use 'Current Time' button for current timestamp")
                                ], size="sm")
                            ])
                        ], span=6)
                    ])
                ],
                opened=False,
                size="lg"
            ),

            dmc.Space(h="lg"),

            # Main Conversion Section
            dmc.Grid([
                # SPS Timestamp Card (Left)
                dmc.GridCol([
                    dmc.Paper([
                        dmc.Stack([
                            # Header with icon
                            dmc.Group([
                                BootstrapIcon(icon="stopwatch", width=24),
                                dmc.Text("SPS Unix Timestamp", fw=500, size="lg")
                            ], justify="center", gap="xs"),

                            dmc.Divider(),

                            # Input section
                            dmc.Stack([
                                dmc.Text("SPS Unix Time Stamp in Minutes",
                                         ta="center", c="dimmed", size="sm"),
                                dmc.TextInput(
                                    id="sps-timestamp-input",
                                    placeholder="e.g. 30000000",
                                    size="lg",
                                    styles={
                                        "input": {
                                            "textAlign": "center",
                                            "fontSize": "1.5rem",
                                            "fontWeight": 600
                                        }
                                    }
                                ),
                                dmc.Text("Minutes since 1967-12-31 00:00:00 UTC",
                                         ta="center", c="dimmed", size="xs"),
                                # Current time button
                                dmc.Center([
                                    dmc.Button(
                                        "Get Current Time",
                                        id="get-current-time-btn",
                                        variant="light",
                                        size="sm",
                                        leftSection=BootstrapIcon(icon="clock", width=16)
                                    )
                                ])
                            ], gap="md")
                        ], gap="lg", p="lg")
                    ], shadow="sm", radius="md", withBorder=True, style={"minHeight": "320px"})
                ], span=5),

                # Arrow Column (Center)
                dmc.GridCol([
                    dmc.Center([
                        dmc.Stack([
                            BootstrapIcon(
                                icon="arrow-left-right",
                                width=50,
                                style={
                                    "filter": "drop-shadow(0 2px 4px rgba(0,0,0,0.1))"}
                            ),
                            dmc.Text("Bidirectional", size="xs",
                                     ta="center", c="dimmed")
                        ], gap="sm", align="center")
                    ], style={"minHeight": "320px"})
                ], span=2),

                # DateTime Card (Right)
                dmc.GridCol([
                    dmc.Paper([
                        dmc.Stack([
                            # Header with icon
                            dmc.Group([
                                BootstrapIcon(icon="calendar3", width=24),
                                dmc.Text("Date Time", fw=500, size="lg")
                            ], justify="center", gap="xs"),

                            dmc.Divider(),

                            # Input section
                            dmc.Stack([
                                dmc.Text("Pick date and time",
                                         ta="center", c="dimmed", size="sm"),
                                
                                # DateTime picker with seconds
                                dmc.DateTimePicker(
                                    id="sps-datetime-input",
                                    label="",
                                    placeholder="Pick date and time",
                                    withSeconds=True,
                                    valueFormat="YYYY/MM/DD HH:mm:ss",
                                    size="lg",
                                    styles={
                                        "input": {
                                            "textAlign": "center",
                                            "fontSize": "1.2rem",
                                            "fontWeight": 500
                                        }
                                    }
                                ),
                                
                                dmc.Text("Format: YYYY/MM/DD HH:MM:SS (24-hour)",
                                         ta="center", c="dimmed", size="xs")
                            ], gap="md")
                        ], gap="lg", p="lg")
                    ], shadow="sm", radius="md", withBorder=True, style={"minHeight": "320px"})
                ], span=5)
            ], justify="center", gutter="lg"),

            dmc.Space(h="xl"),

            # Status/Message Section
            dmc.Center([
                html.Div(id="sps-conversion-message")
            ])

        ], gap="lg")
    ], size="lg", p="md")


# Initialize the SPS time converter service
sps_service = SpsTimeConverterService()


# Callback for Current Time button
@callback(
    Output("sps-timestamp-input", "value", allow_duplicate=True),
    Input("get-current-time-btn", "n_clicks"),
    prevent_initial_call=True
)
def get_current_time(n_clicks):
    """Get current time as SPS timestamp."""
    if n_clicks:
        result = sps_service.get_current_sps_timestamp()
        if result["success"]:
            return result["sps_timestamp"]
    return ""


# Callback for SPS Time Converter
@callback(
    [Output("sps-datetime-input", "value"),
     Output("sps-timestamp-input", "value", allow_duplicate=True),
     Output("sps-conversion-message", "children")],
    [Input("sps-timestamp-input", "value"),
     Input("sps-datetime-input", "value")],
    prevent_initial_call=True
)
def handle_sps_conversion(timestamp_value, datetime_value):
    """Handle automatic bidirectional conversion as user types"""

    # Determine which input triggered the callback
    ctx = callback_context
    if not ctx.triggered:
        return None, "", ""

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Handle SPS Timestamp to DateTime conversion
    if trigger_id == 'sps-timestamp-input':
        if not timestamp_value or timestamp_value.strip() == "":
            return None, timestamp_value or "", ""

        result = sps_service.sps_timestamp_to_datetime(timestamp_value.strip())

        if result["success"]:
            # Convert the timezone-aware datetime to a naive datetime for the DateTimePicker
            # The DateTimePicker expects a naive datetime representing local time
            dt_obj = result["datetime_obj"]
            naive_dt = dt_obj.replace(tzinfo=None)  # Remove timezone info but keep the time values
            
            message = dmc.Alert(
                title="Conversion Successful",
                children=f"Converted: {timestamp_value} minutes → {result['datetime']}",
                color="green",
                icon=BootstrapIcon(icon="check")
            )
            return naive_dt, timestamp_value, message
        else:
            message = dmc.Alert(
                title="Conversion Error",
                children=result['error'],
                color="red",
                icon=BootstrapIcon(icon="exclamation-circle")
            )
            return None, timestamp_value, message

    # Handle DateTime to SPS Timestamp conversion
    elif trigger_id == 'sps-datetime-input':
        if not datetime_value:
            return datetime_value, "", ""
        
        # Convert datetime object to string format expected by service
        if isinstance(datetime_value, datetime):
            # DateTimePicker returns a naive datetime representing local time in our standard timezone
            # Convert it to the format expected by our service
            datetime_str = datetime_value.strftime("%Y/%m/%d %H:%M:%S")
        else:
            # If it's already a string, convert format
            datetime_str = str(datetime_value).replace("-", "/")

        result = sps_service.datetime_to_sps_timestamp(datetime_str)

        if result["success"]:
            message = dmc.Alert(
                title="Conversion Successful",
                children=f"Converted: {datetime_str} → {result['sps_timestamp']} minutes",
                color="green",
                icon=BootstrapIcon(icon="check")
            )
            return datetime_value, result["sps_timestamp"], message
        else:
            message = dmc.Alert(
                title="Conversion Error",
                children=result['error'],
                color="red",
                icon=BootstrapIcon(icon="exclamation-circle")
            )
            return datetime_value, "", message

    # Default case
    return None, "", ""


# Callback for help modal
@callback(
    Output("sps-help-modal", "opened"),
    Input("sps-help-modal-btn", "n_clicks"),
    State("sps-help-modal", "opened"),
    prevent_initial_call=True,
)
def toggle_sps_help_modal(n_clicks, opened):
    """Toggle the help modal."""
    return not opened
