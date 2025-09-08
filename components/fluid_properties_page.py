"""
Fluid Properties data fetch page component.
This page allows users to fetch fluid properties and commodities data from the Oracle SCADA_CMT_PRD database.
"""

import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State, ALL, no_update, ctx
import dash_ag_grid as dag
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
import traceback
import os
from services.fluid_properties_service import get_fluid_properties_service
from components.bootstrap_icon import BootstrapIcon
from components.directory_selector import create_directory_selector


def create_fluid_properties_page():
    """Create the fluid properties page layout."""

    return dmc.Stack([
        dmc.Center([
            dmc.Stack([
                dmc.Group([
                    dmc.Title("Fluid Properties", order=2, ta="center"),
                    dmc.ActionIcon(
                        BootstrapIcon(icon="question-circle", width=20,
                                      color="var(--mantine-color-blue-6)"),
                        id="fluid-properties-help-modal-btn",
                        variant="light",
                        color="blue",
                        size="lg"
                    )
                ], justify="center", align="center", gap="md"),
                dmc.Text("Fetch fluid properties and commodities data from SCADA CMT database",
                         c="dimmed", ta="center", size="md")
            ], gap="xs")
        ]),

        # Help Modal
        dmc.Modal(
            title="Fluid Properties Data Fetcher Help",
            id="fluid-properties-help-modal",
            children=[
                dmc.Text(
                    "This tool allows you to fetch fluid properties and commodities data from the SCADA CMT database. "
                    "Select 'Properties' to fetch density, viscosity, or vapor pressure data, or select 'Commodities' "
                    "to fetch unique fluid and line number data.")
            ],
        ),

        # Main content grid - fluid container
        dmc.Grid([
            # Left offset column (1 column)
            dmc.GridCol([], span=1),

            # Left side - Configuration Card (4 columns)
            dmc.GridCol([
                dmc.Stack([
                    # Data Type selection section
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="toggles", width=20),
                                dmc.Text("Data Type Selection",
                                         fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            dmc.RadioGroup(
                                children=dmc.Group([
                                    dmc.Radio(label="Properties", value="Properties"),
                                    dmc.Radio(label="Commodities", value="Commodities")
                                ], gap="xl", justify="center"),
                                id="fluid-properties-data-type",
                                value="Properties",  # Default to Properties
                                size="sm"
                            )
                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True),

                    # Date Range selection
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="calendar3", width=20),
                                dmc.Text("Date Range Selection",
                                         fw=500, size="md")
                            ], gap="xs"),

                            dmc.Divider(size="xs"),

                            dmc.Stack([
                                dmc.Text("Start Date", size="sm", fw=500),
                                dmc.DateInput(
                                    id="fluid-properties-start-date",
                                    value=(datetime.now() - timedelta(days=30)).date(),
                                    style={"width": "100%"},
                                    size="md",
                                    clearable=False
                                )
                            ], gap="xs"),
                            
                            dmc.Stack([
                                dmc.Text("End Date", size="sm", fw=500),
                                dmc.DateInput(
                                    id="fluid-properties-end-date",
                                    value=datetime.now().date(),
                                    style={"width": "100%"},
                                    size="md",
                                    clearable=False
                                )
                            ], gap="xs")
                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True),

                    # Properties-specific controls (Fluid Selection)
                    html.Div([
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="droplet", width=20),
                                    dmc.Text("Fluid Selection (Multiple)",
                                             fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # Error message placeholder
                                html.Div(id="fluid-names-error-message"),

                                # Fluid names select with loading
                                dcc.Loading(
                                    id="fluid-names-loading",
                                    type="default",
                                    children=[
                                        dmc.TagsInput(
                                            id="fluid-properties-fluid-selection",
                                            placeholder="Type to search and add fluid names...",
                                            data=[],
                                            clearable=True,
                                            style={"width": "100%"},
                                            maxDropdownHeight=200,
                                            splitChars=[",", " ", ";"],
                                            acceptValueOnBlur=True
                                        )
                                    ]
                                )
                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True)
                    ], id="fluid-selection-container"),

                    # Properties-specific controls (Property Type)
                    html.Div([
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="gear", width=20),
                                    dmc.Text("Property Type Selection",
                                             fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                dmc.RadioGroup(
                                    children=dmc.Stack([
                                        dmc.Radio(label="Density", value="Density"),
                                        dmc.Radio(label="Viscosity", value="Viscosity"),
                                        dmc.Radio(label="Vapor Pressure", value="Vapor Pressure")
                                    ], gap="sm"),
                                    id="fluid-properties-property-type",
                                    value="Density",  # Default to Density
                                    size="sm"
                                )
                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True)
                    ], id="property-type-container"),

                    # Fetch button
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="download", width=20),
                                dmc.Text("Data Fetching",
                                         fw=500, size="md")
                            ], gap="xs", justify="center"),

                            dmc.Divider(size="xs"),

                            dmc.Button(
                                "Fetch Data",
                                id="fluid-properties-fetch-btn",
                                leftSection=BootstrapIcon("download"),
                                size="md",
                                style={"width": "100%"},
                                disabled=False
                            )
                        ], gap="sm", p="sm")
                    ], shadow="sm", radius="md", withBorder=True)
                ], gap="md")
            ], span=4),

            # Right side - Results Card (6 columns)
            dmc.GridCol([
                dmc.Stack([
                    # Results section
                    dmc.Card([
                        dmc.CardSection([
                            dmc.Group([
                                dmc.Title("Results", order=4),
                                # Export button (initially hidden)
                                html.Div([
                                    dmc.Button(
                                        "Export to CSV",
                                        id="fluid-properties-export-btn",
                                        leftSection=BootstrapIcon("download"),
                                        variant="light",
                                        size="sm",
                                        color="green"
                                    )
                                ], id="export-button-container", style={"display": "none"})
                            ], justify="space-between", align="center"),

                            # Results container
                            html.Div([
                                html.Div(id="fluid-properties-results-container"),
                                dmc.LoadingOverlay(
                                    id="fluid-properties-loading-results",
                                    visible=False,
                                    overlayProps={"radius": "sm", "blur": 2},
                                    loaderProps={"color": "blue", "size": "lg", "variant": "dots"}
                                )
                            ], style={"position": "relative", "height": "100%"})
                        ], p="md", style={"height": "100%"})
                    ], shadow="sm", style={"height": "calc(100vh - 200px)", "minHeight": "500px"})
                ], gap="md")
            ], span=6),

            # Right offset column (1 column)
            dmc.GridCol([], span=1)
        ], gutter="lg", style={"width": "100%", "margin": 0, "height": "calc(100vh - 150px)", "minHeight": "600px"}),

        # Export Directory Selection Modal
        dmc.Modal(
            title="Select Export Directory",
            id="export-directory-modal",
            size="lg",
            children=[
                dmc.Stack([
                    dmc.Text(
                        "Choose a directory to save the CSV file:", size="sm"),
                    # Create directory selector
                    html.Div([
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="folder", width=20),
                                    dmc.Text("Export Directory",
                                             fw=500, size="md")
                                ], gap="xs"),
                                dmc.Divider(),
                                dmc.Group([
                                    dmc.TextInput(
                                        placeholder="Select directory to save CSV file...",
                                        id="export-directory-input",
                                        style={"flex": 1},
                                        readOnly=True
                                    ),
                                    dmc.Button(
                                        BootstrapIcon("folder2-open"),
                                        id="export-directory-browse",
                                        variant="outline",
                                        size="sm"
                                    )
                                ], gap="sm"),
                                html.Div(id="export-directory-status",
                                         style={'minHeight': '20px'})
                            ], gap="sm", p="md")
                        ], shadow="sm", radius="md", withBorder=True)
                    ]),
                    dmc.Group([
                        dmc.Button(
                            "Cancel",
                            id="export-modal-cancel",
                            variant="outline",
                            color="gray"
                        ),
                        dmc.Button(
                            "Export CSV",
                            id="export-modal-confirm",
                            leftSection=BootstrapIcon("download"),
                            disabled=True,
                            color="green"
                        )
                    ], justify="flex-end", gap="sm")
                ], gap="md")
            ]
        ),

        # Notifications container
        html.Div(id="fluid-properties-notifications"),

        # Hidden stores for data
        dcc.Store(id="fluid-properties-data-store"),
        dcc.Store(id="fluid-properties-current-mode-store", data="Properties"),
        dcc.Store(id="available-fluids-store", data=[])
    ])


# Callbacks

@callback(
    Output("fluid-properties-help-modal", "opened"),
    Input("fluid-properties-help-modal-btn", "n_clicks"),
    prevent_initial_call=True
)
def toggle_help_modal(n_clicks):
    """Toggle help modal visibility."""
    return True if n_clicks else False


@callback(
    [Output("fluid-selection-container", "style"),
     Output("property-type-container", "style"),
     Output("fluid-properties-current-mode-store", "data")],
    Input("fluid-properties-data-type", "value")
)
def toggle_property_controls(data_type):
    """Show/hide property-specific controls based on data type selection."""
    if data_type == "Properties":
        return {"display": "block"}, {"display": "block"}, "Properties"
    else:  # Commodities
        return {"display": "none"}, {"display": "none"}, "Commodities"


@callback(
    [Output("fluid-properties-fluid-selection", "data"),
     Output("fluid-names-error-message", "children"),
     Output("available-fluids-store", "data")],
    Input("fluid-properties-fluid-selection", "id"),  # Trigger on page load
    prevent_initial_call=False
)
def load_fluid_names(_):
    """Load available fluid names from database on page load."""
    try:
        fluid_service = get_fluid_properties_service()
        fluids = fluid_service.fetch_unique_fluid_names()

        if not fluids:
            error_msg = dmc.Alert(
                "No fluid names found in database",
                title="Warning",
                color="yellow",
                icon=BootstrapIcon("exclamation-triangle")
            )
            return [], error_msg, []

        # Convert to select options format
        options = [{"value": fluid, "label": fluid} for fluid in fluids]
        
        return options, no_update, fluids

    except Exception as e:
        error_msg = dmc.Alert(
            f"Failed to load fluid names: {str(e)}",
            title="Error",
            color="red",
            icon=BootstrapIcon("exclamation-triangle")
        )
        return [], error_msg, []


@callback(
    [Output("fluid-properties-fluid-selection", "value"),
     Output("fluid-properties-notifications", "children", allow_duplicate=True)],
    Input("fluid-properties-fluid-selection", "value"),
    State("available-fluids-store", "data"),
    prevent_initial_call=True
)
def validate_and_capitalize_fluid_selection(selected_fluids, available_fluids):
    """Validate and capitalize fluid selections."""
    if not selected_fluids or not available_fluids:
        return no_update, no_update
    
    # Capitalize all inputs
    capitalized_fluids = [fluid.upper() for fluid in selected_fluids]
    
    # Check for invalid fluids
    invalid_fluids = []
    valid_fluids = []
    
    for fluid in capitalized_fluids:
        if fluid in available_fluids:
            valid_fluids.append(fluid)
        else:
            invalid_fluids.append(fluid)
    
    # If there are invalid fluids, show error notification
    if invalid_fluids:
        error_notification = dmc.Notification(
            title="Invalid Fluid Names",
            message=f"The following fluid names are not available: {', '.join(invalid_fluids)}. Please select from the available list.",
            color="red",
            icon=BootstrapIcon("exclamation-triangle"),
            action="show",
            autoClose=5000
        )
        # Return only valid fluids and show error
        return valid_fluids, error_notification
    
    # All fluids are valid, return capitalized version
    return capitalized_fluids, no_update


@callback(
    [Output("fluid-properties-fetch-btn", "loading"),
     Output("fluid-properties-fetch-btn", "disabled")],
    Input("fluid-properties-fetch-btn", "n_clicks"),
    State("fluid-properties-loading-results", "visible"),
    prevent_initial_call=True
)
def manage_fetch_button_state(n_clicks, loading_visible):
    """Manage fetch button loading and disabled state."""
    if n_clicks:
        # Show loading and disable button when clicked
        return True, True
    return False, False


@callback(
    [Output("fluid-properties-fetch-btn", "loading", allow_duplicate=True),
     Output("fluid-properties-fetch-btn", "disabled", allow_duplicate=True)],
    Input("fluid-properties-loading-results", "visible"),
    prevent_initial_call=True
)
def reset_fetch_button_state(loading_visible):
    """Reset fetch button state when loading is complete."""
    if not loading_visible:
        # Reset button when loading is complete
        return False, False
    return no_update, no_update


@callback(
    Output("fluid-properties-loading-results", "visible", allow_duplicate=True),
    Input("fluid-properties-fetch-btn", "n_clicks"),
    prevent_initial_call=True
)
def show_loading_on_fetch(n_clicks):
    """Show loading overlay immediately when fetch button is clicked."""
    if n_clicks:
        return True
    return no_update


@callback(
    [Output("fluid-properties-results-container", "children"),
     Output("fluid-properties-loading-results", "visible"),
     Output("fluid-properties-data-store", "data"),
     Output("export-button-container", "style"),
     Output("fluid-properties-notifications", "children")],
    Input("fluid-properties-fetch-btn", "n_clicks"),
    [State("fluid-properties-data-type", "value"),
     State("fluid-properties-start-date", "value"),
     State("fluid-properties-end-date", "value"),
     State("fluid-properties-fluid-selection", "value"),
     State("fluid-properties-property-type", "value")],
    prevent_initial_call=True
)
def fetch_fluid_data(n_clicks, data_type, start_date, end_date, fluid_name, property_type):
    """Fetch fluid properties or commodities data based on user selection."""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update

    try:
        # Validate inputs
        if not start_date or not end_date:
            error_notification = dmc.Notification(
                title="Input Error",
                message="Please select both start and end dates",
                color="red",
                icon=BootstrapIcon("exclamation-triangle"),
                action="show"
            )
            return no_update, False, no_update, no_update, error_notification

        # Convert dates - DateInput returns date objects or ISO strings
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_dt = datetime.combine(start_date, datetime.min.time())
            
        if isinstance(end_date, str):
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_dt = datetime.combine(end_date, datetime.min.time())

        if start_dt > end_dt:
            error_notification = dmc.Notification(
                title="Date Error",
                message="Start date must be before end date",
                color="red",
                icon=BootstrapIcon("exclamation-triangle"),
                action="show"
            )
            return no_update, False, no_update, no_update, error_notification

        fluid_service = get_fluid_properties_service()

        # Show loading
        if data_type == "Properties":
            # Validate property-specific inputs
            if not fluid_name or len(fluid_name) == 0:
                error_notification = dmc.Notification(
                    title="Input Error",
                    message="Please select at least one fluid name for properties data",
                    color="red",
                    icon=BootstrapIcon("exclamation-triangle"),
                    action="show"
                )
                return no_update, False, no_update, no_update, error_notification

            # Fetch properties data for multiple fluids
            all_data = []
            for fluid in fluid_name:
                df = fluid_service.fetch_properties_data(start_dt, end_dt, fluid, property_type)
                if not df.empty:
                    all_data.append(df)
            
            if all_data:
                df = pd.concat(all_data, ignore_index=True)
                # Sort by commodity_id and sample_date for better organization
                df = df.sort_values(['COMMODITY_ID', 'SAMPLE_DATE'], ignore_index=True)
            else:
                df = pd.DataFrame()  # Empty dataframe if no data found
        else:
            # Fetch commodities data
            df = fluid_service.fetch_commodities_data(start_dt, end_dt)

        if df.empty:
            no_data_msg = dmc.Alert(
                "No data found for the specified criteria",
                title="No Data",
                color="yellow",
                icon=BootstrapIcon("info-circle")
            )
            return no_data_msg, False, no_update, {"display": "none"}, no_update

        # Create AG Grid table
        column_defs = []
        for col in df.columns:
            column_defs.append({
                "field": col,
                "headerName": col,
                "sortable": True,
                "filter": True,
                "resizable": True,
                "editable": False
            })

        table_component = html.Div([
            dmc.Text(f"Found {len(df)} records", size="sm", c="dimmed", mb="sm"),
            dcc.Loading(
                id="fluid-properties-table-loading",
                type="default",
                children=[
                    dag.AgGrid(
                        id="fluid-properties-results-table",
                        className="ag-theme-alpine",
                        rowData=df.to_dict('records'),
                        columnDefs=column_defs,
                        defaultColDef={
                            'sortable': True, 
                            'filter': True, 
                            'resizable': True, 
                            'editable': False,
                            'minWidth': 100
                        },
                        dashGridOptions={
                            'rowHeight': 32,
                            'headerHeight': 40,
                            'enableCellTextSelection': True,
                            'ensureDomOrder': True,
                            'pagination': True,
                            'paginationPageSize': 25,
                            'paginationPageSizeSelector': [10, 25, 50, 100],
                            'rowSelection': 'multiple',
                            'suppressRowClickSelection': True,
                            'animateRows': True,
                            'columnMenu': 'new',
                            'enableAdvancedFilter': True,
                            'enableRangeSelection': True,
                            'suppressMovableColumns': False
                        },
                        style={"height": "calc(100vh - 350px)", "width": "100%", "minHeight": "400px"}
                    )
                ],
                style={'height': '100%', 'minHeight': 0}
            )
        ], style={"height": "calc(100vh - 320px)", "minHeight": "420px", "display": "flex", "flexDirection": "column"})

        success_message = f"Successfully fetched {len(df)} records"
        if data_type == "Properties" and fluid_name:
            success_message += f" for {len(fluid_name)} fluid(s): {', '.join(fluid_name)}"
        
        success_notification = dmc.Notification(
            title="Success",
            message=success_message,
            color="green",
            icon=BootstrapIcon("check-circle"),
            action="show"
        )

        return table_component, False, df.to_dict('records'), {"display": "block"}, success_notification

    except Exception as e:
        error_notification = dmc.Notification(
            title="Error",
            message=f"Failed to fetch data: {str(e)}",
            color="red",
            icon=BootstrapIcon("exclamation-triangle"),
            action="show"
        )
        return no_update, False, no_update, no_update, error_notification


@callback(
    Output("export-directory-modal", "opened", allow_duplicate=True),
    Input("fluid-properties-export-btn", "n_clicks"),
    prevent_initial_call=True
)
def open_export_modal(n_clicks):
    """Open the export directory modal when export button is clicked."""
    return True if n_clicks else False


@callback(
    [Output("export-directory-input", "value"),
     Output("export-modal-confirm", "disabled"),
     Output("export-directory-status", "children")],
    Input("export-directory-browse", "n_clicks"),
    prevent_initial_call=True
)
def browse_export_directory(n_clicks):
    """Handle directory selection for export using tkinter file dialog."""
    if not n_clicks:
        return no_update, no_update, no_update
    
    try:
        import tkinter as tk
        from tkinter import filedialog

        # Create a root window and hide it
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        # Open directory dialog
        directory = filedialog.askdirectory(
            title="Select Directory to Save CSV File"
        )

        root.destroy()

        if directory:
            status_msg = dmc.Text(
                f"✓ Selected: {directory}", size="sm", c="green")
            return directory, False, status_msg
        else:
            status_msg = dmc.Text("No directory selected", size="sm", c="gray")
            return "", True, status_msg

    except Exception as e:
        error_msg = dmc.Text(f"Error: {str(e)}", size="sm", c="red")
        return "", True, error_msg


@callback(
    Output("export-modal-confirm", "disabled", allow_duplicate=True),
    Input("export-directory-input", "value"),
    prevent_initial_call=True
)
def enable_export_button(directory_path):
    """Enable export button only when directory is selected."""
    return not bool(directory_path and directory_path.strip())


@callback(
    [Output("export-directory-modal", "opened", allow_duplicate=True),
     Output("fluid-properties-notifications", "children", allow_duplicate=True),
     Output("export-modal-confirm", "loading")],
    Input("export-modal-confirm", "n_clicks"),
    [State("export-directory-input", "value"),
     State("fluid-properties-data-store", "data"),
     State("fluid-properties-current-mode-store", "data")],
    prevent_initial_call=True
)
def export_to_csv(n_clicks, export_path, data, current_mode):
    """Export the current data to CSV file."""
    if not n_clicks or not data or not export_path:
        return no_update, no_update, False
    
    try:
        # Convert data back to DataFrame
        df = pd.DataFrame(data)
        
        fluid_service = get_fluid_properties_service()
        success = fluid_service.save_to_csv(df, export_path, current_mode)
        
        if success:
            success_notification = dmc.Notification(
                title="Export Successful",
                message=f"Data exported successfully to {export_path}",
                color="green",
                icon=BootstrapIcon("check-circle"),
                action="show"
            )
            return False, success_notification, False
        else:
            error_notification = dmc.Notification(
                title="Export Failed",
                message="Failed to export data to CSV",
                color="red",
                icon=BootstrapIcon("exclamation-triangle"),
                action="show"
            )
            return False, error_notification, False
            
    except Exception as e:
        error_notification = dmc.Notification(
            title="Export Error",
            message=f"Error exporting data: {str(e)}",
            color="red",
            icon=BootstrapIcon("exclamation-triangle"),
            action="show"
        )
        return False, error_notification, False


@callback(
    Output("export-directory-modal", "opened", allow_duplicate=True),
    Input("export-modal-cancel", "n_clicks"),
    prevent_initial_call=True
)
def cancel_export_modal(n_clicks):
    """Close the export modal when cancel is clicked."""
    return False if n_clicks else no_update


@callback(
    Output("fluid-properties-results-table", "className"),
    Input("color-scheme-switch", "checked"),
    prevent_initial_call=False
)
def sync_fluid_properties_grid_theme(is_dark):
    """Sync AG Grid theme with application theme."""
    try:
        return 'ag-theme-alpine-dark' if is_dark else 'ag-theme-alpine'
    except:
        # Fallback to light theme if color scheme switch is not available
        return 'ag-theme-alpine'
