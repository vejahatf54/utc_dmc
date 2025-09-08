"""
Linefill data fetch page component.
This page allows users to fetch linefill data from the Oracle SCADA_CMT_PRD database.
"""

import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State, ALL, no_update, ctx, clientside_callback, ClientsideFunction
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import traceback
import os
from services.linefill_service import get_linefill_service
from components.bootstrap_icon import BootstrapIcon
from components.directory_selector import create_directory_selector


def create_linefill_page():
    """Create the linefill page layout."""

    return dmc.Stack([
        dmc.Center([
            dmc.Stack([
                dmc.Group([
                    dmc.Title("Fetch LineFill", order=2, ta="center"),
                    dmc.ActionIcon(
                        BootstrapIcon(icon="question-circle", width=20,
                                      color="var(--mantine-color-blue-6)"),
                        id="linefill-help-modal-btn",
                        variant="light",
                        color="blue",
                        size="lg"
                    )
                ], justify="center", align="center", gap="md"),
                dmc.Text("Fetch linefill data from SCADA CMT database for analysis",
                         c="dimmed", ta="center", size="md")
            ], gap="xs")
        ]),

        # Help Modal
        dmc.Modal(
            title="LineFill Data Fetcher Help",
            id="linefill-help-modal",
            children=[
                dmc.Text(
                    "This tool allows you to fetch linefill data from the SCADA CMT database.")
            ],
        ),

        # Main content grid - fluid container
        dmc.Grid([
            # Left offset column (1 column)
            dmc.GridCol([], span=1),

            # Left side - Configuration Card (3 columns)
            dmc.GridCol([
                dmc.Stack([
                    # Line selection section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="diagram-3", width=20),
                                dmc.Text("Pipeline Lines Selection",
                                         fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            # Error message placeholder
                            html.Div(id="lines-error-message-linefill"),

                            # Lines checklist with loading
                            dcc.Loading(
                                id="lines-loading-linefill",
                                type="default",
                                children=[
                                    dmc.CheckboxGroup(
                                        id="linefill-line-selection",
                                        value=[],
                                        children=[],
                                        style={
                                            "columnCount": "2",
                                            "columnGap": "16px",
                                            "lineHeight": "1.6",
                                            "fontSize": "0.85rem"
                                        },
                                        styles={
                                            "root": {"gap": "8px"}
                                        }
                                    )
                                ]
                            ),

                            # Select All section
                            dmc.Divider(size="xs"),
                            dmc.Center([
                                dmc.CheckboxGroup(
                                    id="select-all-lines-checkbox-linefill",
                                    value=[],  # Start unchecked
                                    children=[
                                        dmc.Checkbox(
                                            label="Select All Lines",
                                            value="select_all",
                                            styles={
                                                "input": {"border-radius": "4px"},
                                                "body": {"align-items": "flex-start"},
                                                "labelWrapper": {"margin-left": "8px"}
                                            }
                                        )
                                    ]
                                )
                            ])
                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True),

                    # Batch boundary selection
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="tag", width=20),
                                dmc.Text("Batch Boundary Selection",
                                         fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            dmc.RadioGroup(
                                children=dmc.Group([
                                    dmc.Radio(label="LAB", value="LAB"),
                                    dmc.Radio(label="ID1LAB", value="ID1LAB")
                                ], gap="xl", justify="center"),
                                id="linefill-batch-boundary",
                                value="LAB",  # Default to LAB
                                size="sm"
                            )
                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True),

                    # Date/Time selection
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="calendar3", width=20),
                                dmc.Text("Date/Time Selection",
                                         fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            dmc.RadioGroup(
                                children=dmc.Group([
                                    dmc.Radio("Single Date/Time",
                                              value="single"),
                                    dmc.Radio("Date Range", value="range")
                                ], gap="xl", justify="center"),
                                id="linefill-date-type",
                                value="single",
                                size="sm"
                            ),

                            # Single date/time controls
                            html.Div([
                                dmc.Stack([
                                    dmc.Text("Date and Time",
                                             size="sm", fw=500),
                                    dmc.DateTimePicker(
                                        id="linefill-single-datetime",
                                        value=datetime.now().replace(minute=0, second=0, microsecond=0),
                                        style={"width": "100%"},
                                        withSeconds=False,
                                        valueFormat="YYYY-MM-DD HH:00",
                                        timePickerProps={
                                            "withMinutes": False,
                                            "withSeconds": False
                                        }
                                    )
                                ], gap="xs")
                            ], id="linefill-single-controls"),

                            # Date range controls
                            html.Div([
                                dmc.Stack([
                                    dmc.Text("Start Date and Time",
                                             size="sm", fw=500),
                                    dmc.DateTimePicker(
                                        id="linefill-start-datetime",
                                        value=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                                        style={"width": "100%"},
                                        withSeconds=False,
                                        valueFormat="YYYY-MM-DD HH:00",
                                        timePickerProps={
                                            "withMinutes": False,
                                            "withSeconds": False
                                        }
                                    )
                                ], gap="xs"),
                                dmc.Stack([
                                    dmc.Text("End Date and Time",
                                             size="sm", fw=500),
                                    dmc.DateTimePicker(
                                        id="linefill-end-datetime",
                                        value=(datetime.now() + timedelta(days=1)
                                               ).replace(hour=23, minute=0, second=0, microsecond=0),
                                        style={"width": "100%"},
                                        withSeconds=False,
                                        valueFormat="YYYY-MM-DD HH:00",
                                        timePickerProps={
                                            "withMinutes": False,
                                            "withSeconds": False
                                        }
                                    )
                                ], gap="xs"),
                                dmc.Stack([
                                    dmc.Text(
                                        "Frequency", size="sm", fw=500),
                                    dmc.Select(
                                        id="linefill-frequency",
                                        data=[
                                            {"value": "Hourly",
                                                "label": "Hourly"},
                                            {"value": "Daily",
                                                "label": "Daily"},
                                            {"value": "Weekly",
                                                "label": "Weekly"},
                                            {"value": "Monthly",
                                             "label": "Monthly"}
                                        ],
                                        value="Daily",
                                        style={"width": "100%"}
                                    )
                                ], gap="xs")
                            ], id="linefill-range-controls", style={"display": "none"})
                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True)
                ], gap="md")
            ], span=3),

            # Right side - Results Card (6 columns)
            dmc.GridCol([
                dmc.Stack([
                    # Results section
                    dmc.Card([
                        dmc.CardSection([
                            dmc.Group([
                                dmc.Title("Results", order=4),
                            ], justify="space-between", align="center"),

                            # Results tabs
                            html.Div([
                                html.Div(id="linefill-results-container"),
                                dmc.LoadingOverlay(
                                    id="linefill-loading-results",
                                    visible=False
                                )
                            ], style={"position": "relative"})
                        ], p="md")
                    ], shadow="sm", h="800px"),

                    # Data extraction section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="download", width=20),
                                dmc.Text("Data Extraction",
                                         fw=500, size="md")
                            ], gap="xs", justify="center"),

                            dmc.Divider(size="xs"),

                            # Single date mode buttons
                            html.Div([
                                dmc.Group([
                                    dmc.Button(
                                        "Load Linefill Data",
                                        id="linefill-load-btn",
                                        leftSection=BootstrapIcon("download"),
                                        size="md",
                                        disabled=True,
                                        style={"flex": 1}
                                    ),
                                    dmc.Button(
                                        "Save All",
                                        id="linefill-save-all-btn",
                                        leftSection=BootstrapIcon("save"),
                                        variant="light",
                                        size="md",
                                        disabled=True,
                                        style={"flex": 1}
                                    )
                                ], gap="sm")
                            ], id="linefill-single-buttons", style={"display": "block"}),
                            
                            # Date range mode button
                            html.Div([
                                dmc.Button(
                                    "Download All Files",
                                    id="linefill-download-all-btn",
                                    leftSection=BootstrapIcon("cloud-download"),
                                    size="md",
                                    disabled=True,
                                    style={"width": "100%"}
                                )
                            ], id="linefill-range-buttons", style={"display": "none"})
                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True)
                ], gap="md")
            ], span=6),

            # Right offset column (1 column)
            dmc.GridCol([], span=1)
        ], gutter="lg", style={"width": "100%", "margin": 0}),  # Fluid grid

        # Save Directory Selection Modal
        dmc.Modal(
            title="Select Save Directory",
            id="save-directory-modal",
            size="lg",
            children=[
                dmc.Stack([
                    dmc.Text(
                        "Choose a directory to save all linefill data files:", size="sm"),
                    # Create directory selector
                    html.Div([
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="folder", width=20),
                                    dmc.Text("Save Directory",
                                             fw=500, size="md")
                                ], gap="xs"),
                                dmc.Divider(),
                                dmc.Group([
                                    dmc.TextInput(
                                        placeholder="Select directory to save *.inc files...",
                                        id="save-directory-input",
                                        style={"flex": 1},
                                        readOnly=True
                                    ),
                                    dmc.Button(
                                        BootstrapIcon("folder2-open"),
                                        id="save-directory-browse",
                                        variant="outline",
                                        size="sm"
                                    )
                                ], gap="sm"),
                                html.Div(id="save-directory-status",
                                         style={'minHeight': '20px'})
                            ], gap="sm", p="md")
                        ], shadow="sm", radius="md", withBorder=True)
                    ]),
                    dmc.Group([
                        dmc.Button(
                            "Cancel",
                            id="save-modal-cancel",
                            variant="outline",
                            color="gray"
                        ),
                        dmc.Button(
                            "Save Files",
                            id="save-modal-confirm",
                            leftSection=BootstrapIcon("save"),
                            disabled=True
                        )
                    ], justify="flex-end", gap="sm")
                ], gap="md")
            ]
        ),

        # Notifications container
        html.Div(id="linefill-notifications"),

        # Hidden stores for data
        dcc.Store(id="linefill-data-store"),
        dcc.Store(id="linefill-failed-lines-store")
    ])  # Close Stack


# Callbacks

@callback(
    Output("linefill-line-selection", "children"),
    Input("linefill-line-selection", "id"),  # Trigger on page load
    prevent_initial_call=False
)
def load_available_lines(_):
    """Load available lines from database on page load."""
    try:
        linefill_service = get_linefill_service()
        lines = linefill_service.fetch_list_of_distinct_lines_from_cmt()

        checkboxes = [
            dmc.Checkbox(
                label=f"Line {line}",
                value=line,
                styles={
                    "input": {"border-radius": "4px"},
                    "body": {"align-items": "flex-start"},
                    "labelWrapper": {"margin-left": "8px"}
                }
            )
            for line in lines
        ]

        return checkboxes

    except Exception as e:
        # Return error message
        error_msg = dmc.Alert(
            f"Error loading lines: {str(e)}",
            title="Database Error",
            color="red"
        )
        return [error_msg]


@callback(
    Output("linefill-line-selection", "value"),
    [Input("select-all-lines-checkbox-linefill", "value")],
    State("linefill-line-selection", "children"),
    prevent_initial_call=True
)
def handle_line_selection(select_all_value, line_checkboxes):
    """Handle select all checkbox."""
    if not line_checkboxes:
        return []

    # If "select_all" is in the value, select all lines
    if select_all_value and "select_all" in select_all_value:
        # Get all available line values
        return [checkbox["props"]["value"] for checkbox in line_checkboxes
                if isinstance(checkbox, dict) and "props" in checkbox]
    else:
        # Clear all selections
        return []


@callback(
    [Output("linefill-single-controls", "style"),
     Output("linefill-range-controls", "style"),
     Output("linefill-single-buttons", "style"),
     Output("linefill-range-buttons", "style"),
     Output("linefill-results-container", "style"),
     Output("linefill-results-container", "children", allow_duplicate=True),
     Output("linefill-data-store", "data", allow_duplicate=True),
     Output("linefill-failed-lines-store", "data", allow_duplicate=True)],
    Input("linefill-date-type", "value"),
    prevent_initial_call=True
)
def toggle_date_controls(date_type):
    """Toggle between single and range date controls, buttons, results visibility, and clear all data."""
    if date_type == "single":
        return (
            {"display": "block"},      # single controls
            {"display": "none"},       # range controls  
            {"display": "block"},      # single buttons
            {"display": "none"},       # range buttons
            {"display": "block"},      # results container
            [],                        # clear results content
            {},                        # clear data store
            {}                         # clear failed lines store
        )
    else:
        return (
            {"display": "none"},       # single controls
            {"display": "block"},      # range controls
            {"display": "none"},       # single buttons
            {"display": "block"},      # range buttons
            {"display": "none"},       # results container (hidden in range mode)
            [],                        # clear results content
            {},                        # clear data store
            {}                         # clear failed lines store
        )


@callback(
    Output("linefill-single-datetime", "value"),
    Input("linefill-single-datetime", "value"),
    prevent_initial_call=True
)
def force_single_datetime_minutes_to_zero(value):
    """Force minutes to zero for single datetime picker."""
    if value:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = value
        return dt.replace(minute=0, second=0, microsecond=0)
    return value


@callback(
    Output("linefill-start-datetime", "value"),
    Input("linefill-start-datetime", "value"),
    prevent_initial_call=True
)
def force_start_datetime_minutes_to_zero(value):
    """Force minutes to zero for start datetime picker."""
    if value:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = value
        return dt.replace(minute=0, second=0, microsecond=0)
    return value


@callback(
    Output("linefill-end-datetime", "value"),
    Input("linefill-end-datetime", "value"),
    prevent_initial_call=True
)
def force_end_datetime_minutes_to_zero(value):
    """Force minutes to zero for end datetime picker."""
    if value:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = value
        return dt.replace(minute=0, second=0, microsecond=0)
    return value


@callback(
    [Output("linefill-load-btn", "disabled"),
     Output("linefill-download-all-btn", "disabled")],
    Input("linefill-line-selection", "value")
)
def enable_buttons(selected_lines):
    """Enable buttons when at least one line is selected."""
    disabled = not (selected_lines and len(selected_lines) > 0)
    return disabled, disabled


@callback(
    [Output("linefill-results-container", "children"),
     Output("linefill-data-store", "data"),
     Output("linefill-failed-lines-store", "data"),
     Output("linefill-loading-results", "visible"),
     Output("linefill-save-all-btn", "disabled"),
     Output("linefill-notifications", "children")],
    Input("linefill-load-btn", "n_clicks"),
    [State("linefill-line-selection", "value"),
     State("linefill-batch-boundary", "value"),
     State("linefill-date-type", "value"),
     State("linefill-single-datetime", "value"),
     State("linefill-start-datetime", "value"),
     State("linefill-end-datetime", "value"),
     State("linefill-frequency", "value")],
    prevent_initial_call=True
)
def load_linefill_data(n_clicks, selected_lines, batch_boundary, date_type,
                       single_datetime, start_datetime, end_datetime, frequency):
    """Load linefill data based on user selections."""
    if not n_clicks or not selected_lines:
        return no_update, no_update, no_update, False, True, no_update

    try:
        linefill_service = get_linefill_service()
        linefill_service.clear_failed_lines()  # Clear any previous failed lines
        results_data = {}  # Always start fresh with empty dictionary

        if date_type == "single":
            # Single datetime processing
            if single_datetime:
                # DateTimePicker returns ISO format string, convert to datetime
                datetime_obj = datetime.fromisoformat(single_datetime.replace(
                    'Z', '+00:00')) if isinstance(single_datetime, str) else single_datetime

                for line in selected_lines:
                    try:
                        data = linefill_service.fetch_linefill(
                            line, datetime_obj, batch_boundary)
                        if data:
                            tab_title = f"{line} - {datetime_obj.strftime('%Y-%m-%d %H:%M')}"
                            results_data[tab_title] = "\n".join(data)
                        else:
                            # No data returned - add to failed lines (matching C# behavior)
                            failed_line_entry = f"{line}-{datetime_obj.strftime('%H%M %d-%b-%Y')}"
                            if not hasattr(linefill_service, '_failed_lines'):
                                linefill_service._failed_lines = []
                            linefill_service._failed_lines.append(failed_line_entry)
                    except Exception as e:
                        print(f"Error fetching data for line {line}: {str(e)}")
                        # Add to failed lines on exception as well
                        failed_line_entry = f"{line}-{datetime_obj.strftime('%H%M %d-%b-%Y')}"
                        if not hasattr(linefill_service, '_failed_lines'):
                            linefill_service._failed_lines = []
                        linefill_service._failed_lines.append(failed_line_entry)

        else:
            # Date range processing
            if start_datetime and end_datetime:
                # Convert DateTimePicker values to datetime objects
                start_dt = datetime.fromisoformat(start_datetime.replace(
                    'Z', '+00:00')) if isinstance(start_datetime, str) else start_datetime
                end_dt = datetime.fromisoformat(end_datetime.replace(
                    'Z', '+00:00')) if isinstance(end_datetime, str) else end_datetime

                multiple_results = linefill_service.fetch_multiple_linefill(
                    selected_lines, start_dt, end_dt, frequency, batch_boundary
                )

                for line, line_data in multiple_results.items():
                    for timestamp, data in line_data:
                        tab_title = f"{line} - {timestamp.strftime('%Y-%m-%d %H:%M')}"
                        results_data[tab_title] = "\n".join(data)

        # Get failed lines
        failed_lines = linefill_service.get_failed_lines()

        # Create tabs for results
        if results_data:
            # Add batch boundary info to results_data for saving
            enhanced_results_data = {}
            for tab_title, content in results_data.items():
                enhanced_results_data[tab_title] = {
                    'content': content,
                    'batch_boundary': batch_boundary
                }
            # Add timestamp and click count to ensure fresh rendering every time
            import time
            timestamp = int(time.time() * 1000)  # milliseconds timestamp
            # Include both timestamp and click count
            unique_suffix = f"{timestamp}-{n_clicks}"

            tabs = []
            for i, (tab_title, content) in enumerate(results_data.items()):
                tabs.append(
                    dmc.TabsTab(
                        tab_title,
                        # Include unique suffix for complete uniqueness
                        value=f"tab-{i}-{unique_suffix}"
                    )
                )

            panels = []
            for i, (tab_title, content) in enumerate(results_data.items()):
                # Format content for rich text display
                formatted_content = []

                # Extract line and datetime from tab_title (format: "Line - YYYY-MM-DD HH:MM")
                parts = tab_title.split(" - ")
                if len(parts) >= 2:
                    line_name = parts[0]
                    datetime_str = parts[1]
                    # Convert to the desired format: YYYY/MM/DD HH:MM:SS
                    try:
                        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                        formatted_datetime = dt.strftime("%Y/%m/%d %H:%M:%S")
                        header = f"/* Linefill Generated for the Period of {formatted_datetime}"
                    except:
                        header = f"/* Linefill Generated for the Period of {datetime_str}"
                else:
                    header = f"/* Linefill Generated for {tab_title}"

                # Add header as first line
                formatted_content.append(header)
                formatted_content.append("")  # Empty line after header

                # Add the appropriate table header based on batch boundary
                if batch_boundary == "ID1LAB":
                    table_header = "+ TABLE FLUID ID1 VOLUME /* | Density | Locn | Upstrm Vol | Dnstrm Vol |"
                else:  # LAB
                    table_header = "+ TABLE FLUID VOLUME /* | Density | Locn | Upstrm Vol | Dnstrm Vol |"

                formatted_content.append(table_header)

                # Add the actual content
                for line in content.split('\n'):
                    if line.strip():  # Skip empty lines
                        formatted_content.append(line)

                # Join with proper line breaks for rich text
                # Convert to HTML with proper formatting for editable content
                html_lines = []
                for line in formatted_content:
                    if line.strip():
                        # Escape HTML characters and convert to proper HTML
                        escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html_lines.append(f"<p>{escaped_line}</p>")
                    else:
                        html_lines.append("<br>")
                
                rich_html_content = ''.join(html_lines)

                panels.append(
                    dmc.TabsPanel(
                        dmc.Stack([
                            dmc.ScrollArea([
                                dmc.RichTextEditor(
                                    html=rich_html_content,
                                    toolbar={
                                        "sticky": True,
                                        "controlsGroups": [
                                            [
                                                "Bold",
                                                "Italic",
                                                "Underline",
                                                "Strikethrough",
                                                "ClearFormatting",
                                                "Highlight",
                                                "Code"
                                            ],
                                            ["H1", "H2", "H3", "H4", "H5", "H6"],
                                            [
                                                "Blockquote",
                                                "Hr",
                                                "BulletList",
                                                "OrderedList",
                                                "Subscript",
                                                "Superscript"
                                            ],
                                            ["Link", "Unlink"],
                                            ["AlignLeft", "AlignCenter",
                                                "AlignJustify", "AlignRight"],
                                            [
                                                {"Color": {"color": "red"}},
                                                {"Color": {"color": "green"}},
                                                {"Color": {"color": "cyan"}},
                                                {"Color": {"color": "yellow"}},
                                                {"Color": {"color": "lime"}},
                                            ],
                                            ["Undo", "Redo"]
                                        ]
                                    },
                                    style={
                                        "minHeight": "550px",
                                    },
                                    styles={
                                        "root": {
                                            "fontFamily": "Consolas, 'Courier New', monospace",
                                            "fontSize": "12px"
                                        },
                                        "content": {
                                            "fontFamily": "Consolas, 'Courier New', monospace !important",
                                            "fontSize": "12px !important"
                                        }
                                    }
                                )
                            ], h=600, type="auto")
                        ], gap="sm"),
                        # Include unique suffix for complete uniqueness
                        value=f"tab-{i}-{unique_suffix}"
                    )
                )

            results_component = html.Div([
                dmc.Tabs([
                    dmc.TabsList(tabs),
                    *panels
                    # Use unique suffix for default tab selection
                ], value=f"tab-0-{unique_suffix}")
                # Unique container to force re-rendering
            ], id=f"linefill-tabs-container-{unique_suffix}")

            # Show notification for failed lines if any
            if failed_lines:
                failed_notification = dmc.Notification(
                    title="Some lines failed to load",
                    message=f"Failed lines: {', '.join(failed_lines)}",
                    color="red",
                    autoClose=5000,
                    action="show"
                )
                results_component = html.Div(
                    [failed_notification, results_component])

        else:
            enhanced_results_data = {}
            results_component = dmc.Alert(
                "No data found for the selected criteria.",
                title="No Results",
                color="yellow"
            )

        return results_component, enhanced_results_data, failed_lines, False, False, dmc.Notification(
            title="Success",
            message="Linefill data loaded successfully!",
            color="green",
            autoClose=3000,
            action="show",
            icon=BootstrapIcon("check-circle-fill")
        )

    except Exception as e:
        error_component = dmc.Alert(
            f"Error loading linefill data: {str(e)}",
            title="Error",
            color="red"
        )
        return error_component, {}, [], False, True, dmc.Notification(
            title="Error",
            message=f"Failed to load linefill data: {str(e)}",
            color="red",
            autoClose=5000,
            action="show",
            icon=BootstrapIcon("exclamation-triangle-fill")
        )


# Callback for download all functionality (date range mode) - Just open modal
@callback(
    Output("save-directory-modal", "opened", allow_duplicate=True),
    Input("linefill-download-all-btn", "n_clicks"),
    prevent_initial_call=True
)
def open_download_modal(n_clicks):
    """Open the save directory modal immediately when download is clicked."""
    if n_clicks:
        return True
    return no_update


@callback(
    Output("linefill-save-notification", "children", allow_duplicate=True),
    Input("linefill-save-all-btn", "n_clicks"),
    State("linefill-data-store", "data"),
    prevent_initial_call=True
)
def save_all_data(n_clicks, data_store):
    """Save all linefill data to files."""
    if not n_clicks or not data_store:
        return no_update

    try:
        linefill_service = get_linefill_service()
        saved_files = []

        for tab_title, content in data_store.items():
            file_path = linefill_service.save_linefill_data(tab_title, content)
            saved_files.append(file_path)

        return dmc.Notification(
            title="Files Saved Successfully",
            message=f"Saved {len(saved_files)} files",
            color="green",
            autoClose=3000,
            action="show"
        )

    except Exception as e:
        return dmc.Notification(
            title="Save Error",
            message=f"Error saving files: {str(e)}",
            color="red",
            autoClose=5000,
            action="show"
        )


@callback(
    Output("linefill-help-modal", "opened"),
    Input("linefill-help-modal-btn", "n_clicks"),
    State("linefill-help-modal", "opened"),
    prevent_initial_call=True,
)
def toggle_help_modal(n_clicks, opened):
    """Toggle help modal."""
    return not opened


@callback(
    Output({"type": "copy-button", "index": ALL}, "children"),
    Input({"type": "copy-button", "index": ALL}, "n_clicks"),
    State({"type": "copy-content", "index": ALL}, "children"),
    prevent_initial_call=True
)
def copy_to_clipboard(n_clicks_list, content_list):
    """Handle copy to clipboard functionality."""
    if not any(n_clicks_list):
        return [no_update] * len(n_clicks_list)

    # Find which button was clicked
    ctx_triggered = ctx.triggered[0] if ctx.triggered else None
    if not ctx_triggered:
        return [no_update] * len(n_clicks_list)

    # Return updated button text to show feedback
    result = []
    for i, n_clicks in enumerate(n_clicks_list):
        if ctx_triggered["prop_id"].endswith(f'"index":{i}}}'):
            # This button was clicked - show "Copied!" temporarily
            result.append([
                BootstrapIcon("check"),
                "Copied!"
            ])
        else:
            # Other buttons keep original text
            result.append([
                BootstrapIcon("clipboard"),
                "Copy to Clipboard"
            ])

    return result


# Callbacks for Save All functionality

@callback(
    [Output("save-directory-input", "value"),
     Output("save-directory-status", "children")],
    Input("save-directory-browse", "n_clicks"),
    prevent_initial_call=True
)
def browse_save_directory(n_clicks):
    """Handle directory selection for saving files."""
    if not n_clicks:
        return no_update, no_update

    try:
        import tkinter as tk
        from tkinter import filedialog

        # Create a root window and hide it
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        # Open directory dialog
        directory = filedialog.askdirectory(
            title="Select Directory to Save Linefill Files"
        )

        root.destroy()

        if directory:
            status_msg = dmc.Text(
                f"✓ Selected: {directory}", size="sm", c="green")
            return directory, status_msg
        else:
            status_msg = dmc.Text("No directory selected", size="sm", c="gray")
            return "", status_msg

    except Exception as e:
        error_msg = dmc.Text(f"Error: {str(e)}", size="sm", c="red")
        return "", error_msg


@callback(
    Output("save-directory-modal", "opened"),
    Input("linefill-save-all-btn", "n_clicks"),
    prevent_initial_call=True
)
def open_save_modal(n_clicks):
    """Open the save directory selection modal."""
    if n_clicks:
        return True
    return False


@callback(
    Output("save-modal-confirm", "disabled"),
    Input("save-directory-input", "value")
)
def enable_save_confirm(directory_path):
    """Enable the save confirm button when a directory is selected."""
    return not directory_path


@callback(
    [Output("save-directory-modal", "opened", allow_duplicate=True),
     Output("linefill-notifications", "children", allow_duplicate=True)],
    Input("save-modal-cancel", "n_clicks"),
    prevent_initial_call=True
)
def cancel_save_modal(n_clicks):
    """Close the save modal when cancel is clicked."""
    if n_clicks:
        return False, no_update
    return no_update, no_update


@callback(
    Output("save-modal-confirm", "loading"),
    Input("save-modal-confirm", "n_clicks"),
    prevent_initial_call=True
)
def set_save_loading(n_clicks):
    """Show loading state when save button is clicked."""
    if n_clicks:
        return True
    return False


@callback(
    [Output("save-directory-modal", "opened", allow_duplicate=True),
     Output("linefill-notifications", "children", allow_duplicate=True),
     Output("save-modal-confirm", "loading", allow_duplicate=True)],
    Input("save-modal-confirm", "n_clicks"),
    [State("save-directory-input", "value"),
     State("linefill-data-store", "data"),
     State("linefill-line-selection", "value"),
     State("linefill-batch-boundary", "value"),
     State("linefill-start-datetime", "value"),
     State("linefill-end-datetime", "value"),
     State("linefill-frequency", "value"),
     State("linefill-date-type", "value")],
    prevent_initial_call=True
)
def save_all_files(n_clicks, directory_path, data_store, selected_lines, batch_boundary, start_datetime, end_datetime, frequency, date_type):
    """Save all linefill data to .inc files - handles both regular save and download operations."""
    if not n_clicks or not directory_path:
        return no_update, no_update, False

    try:
        # If data_store is empty and we're in date range mode, this is a download operation
        is_date_range_mode = (date_type == "range")
        if (not data_store or len(data_store) == 0) and is_date_range_mode and selected_lines:
            # This is a download operation - fetch data now
            linefill_service = get_linefill_service()
            linefill_service.clear_failed_lines()
            
            # Convert DateTimePicker values to datetime objects
            start_dt = datetime.fromisoformat(start_datetime.replace(
                'Z', '+00:00')) if isinstance(start_datetime, str) else start_datetime
            end_dt = datetime.fromisoformat(end_datetime.replace(
                'Z', '+00:00')) if isinstance(end_datetime, str) else end_datetime

            # Fetch data for all lines and time range
            results = linefill_service.fetch_multiple_linefill(
                selected_lines, start_dt, end_dt, frequency, batch_boundary
            )

            if not results:
                return False, dmc.Notification(
                    title="No Data Found",
                    message="No linefill data found for the selected criteria.",
                    color="yellow",
                    autoClose=5000,
                    action="show",
                    icon=BootstrapIcon("exclamation-triangle")
                ), False

            # Convert results to the format expected for saving
            data_store = {}
            for line_no, line_results in results.items():
                for timestamp, data in line_results:
                    if data:  # Only include if there's actual data
                        # Create tab title like "Line_101 - 2024-01-15 14:30"
                        tab_title = f"Line_{line_no} - {timestamp.strftime('%Y-%m-%d %H:%M')}"
                        
                        # Format data with proper line breaks
                        formatted_data = "\n".join(data)
                        
                        # Store in the format expected by save modal (with batch boundary info)
                        data_store[tab_title] = {
                            'content': formatted_data,
                            'batch_boundary': batch_boundary
                        }

        # If still no data, return error
        if not data_store:
            return False, dmc.Notification(
                title="No Data to Save",
                message="No data available for saving.",
                color="yellow",
                autoClose=5000,
                action="show",
                icon=BootstrapIcon("exclamation-triangle")
            ), False

        saved_files = []
        for tab_title, data_info in data_store.items():
            # Handle both old format (string) and new format (dict)
            if isinstance(data_info, dict):
                content = data_info['content']
                batch_boundary = data_info['batch_boundary']
            else:
                # Fallback for old format
                content = data_info
                batch_boundary = "LAB"  # Default

            # Extract line number and datetime from tab_title for proper filename
            parts = tab_title.split(" - ")
            if len(parts) >= 2:
                line_part = parts[0]  # e.g., "Line_101"
                datetime_str = parts[1]  # e.g., "2024-01-15 14:30"
                
                # Extract just the number from "Line_101" -> "101"
                line_number = line_part.replace("Line_", "")
                
                # Clean datetime string for filename
                clean_datetime = datetime_str.replace(":", "").replace(" ", "_").replace("/", "-")
                
                # Create proper filename: L101_2024-01-15_1430.inc
                filename = f"L{line_number}_{clean_datetime}.inc"
            else:
                # Fallback - clean the full tab_title and add L prefix
                filename = tab_title.replace(" - ", "_").replace(":", "").replace("/", "-")
                filename = f"L{filename}.inc"
                
            filepath = os.path.join(directory_path, filename)

            # Extract line and datetime from tab_title to create proper header
            parts = tab_title.split(" - ")
            if len(parts) >= 2:
                line_name = parts[0]
                datetime_str = parts[1]
                # Convert to the desired format: YYYY/MM/DD HH:MM:SS
                try:
                    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                    formatted_datetime = dt.strftime("%Y/%m/%d %H:%M:%S")
                    header = f"/* Linefill Generated for the Period of {formatted_datetime}\n\n"
                except:
                    header = f"/* Linefill Generated for the Period of {datetime_str}\n\n"
            else:
                header = f"/* Linefill Generated for {tab_title}\n\n"

            # Add the appropriate table header based on batch boundary
            if batch_boundary == "ID1LAB":
                table_header = "+ TABLE FLUID ID1 VOLUME /* | Density | Locn | Upstrm Vol | Dnstrm Vol |\n"
            else:  # LAB
                table_header = "+ TABLE FLUID VOLUME /* | Density | Locn | Upstrm Vol | Dnstrm Vol |\n"

            # Add the header, table header, and content
            file_content = header + table_header + content

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(file_content)
            saved_files.append(filename)

        success_notification = dmc.Notification(
            title="Files Saved Successfully",
            message=f"Saved {len(saved_files)} files to {directory_path}",
            color="green",
            autoClose=5000,
            action="show",
            icon=BootstrapIcon("check-circle-fill")
        )

        return False, success_notification, False

    except Exception as e:
        error_notification = dmc.Notification(
            title="Save Error",
            message=f"Failed to save files: {str(e)}",
            color="red",
            autoClose=5000,
            action="show",
            icon=BootstrapIcon("exclamation-triangle-fill")
        )

        return False, error_notification, False


# Add notification container for save operations
def create_linefill_page_with_notifications():
    """Create linefill page with notification container."""
    return html.Div([
        create_linefill_page(),
        html.Div(id="linefill-save-notification")
    ])
