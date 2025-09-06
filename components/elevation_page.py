import os
import sys
import tempfile
import io
import zipfile
import base64
import time
import re
import numpy as np
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State
import dash_mantine_components as dmc
import plotly.graph_objs as go
import dash_ag_grid as dag
from services.onesource_service import get_onesource_service
from services.elevation_data_service import fetch_elevation_profile, validate_elevation_data
from services.pipe_analysis_service import PipeAnalysisService
from components.bootstrap_icon import BootstrapIcon
from components.directory_selector import create_directory_selector, create_directory_selector_callback

# ---------------------------
# Config (assets only; CSV removed)
# ---------------------------
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(__file__)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
SPLASH_IMG_NAME = 'logo.png'

# Global profile cache
_profile_cache: dict[str, pd.DataFrame] = {}

# Theme constants
DARK_CLASS = "d-flex flex-column bg-dark text-light"
LIGHT_CLASS = "d-flex flex-column bg-light text-dark"

# Simple service instances
pipe_analysis_service = None


def get_pipe_analysis_service():
    """Get pipe analysis service instance."""
    global pipe_analysis_service
    if pipe_analysis_service is None:
        pipe_analysis_service = PipeAnalysisService()
    return pipe_analysis_service

# Register the directory selector callback at module level
@dash.callback(
    [Output('directory-input-mbs-profile', 'value'),
     Output('directory-store-mbs-profile', 'data')],
    Input('browse-btn-mbs-profile', 'n_clicks'),
    prevent_initial_call=True
)
def handle_mbs_directory_selection(browse_clicks):
    """Handle MBS directory selection."""
    from dash import callback_context
    ctx = callback_context
    if not ctx.triggered:
        return "", {'path': ''}

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'browse-btn-mbs-profile':
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()  # Hide the main window
            root.lift()      # Bring to front
            root.attributes("-topmost", True)

            directory = filedialog.askdirectory(title="Select MBS Profile Directory")
            root.destroy()

            if directory:
                return directory, {'path': directory}
            else:
                return "", {'path': ''}

        except Exception as e:
            print(f"Error selecting directory: {str(e)}")
            return "", {'path': ''}

    return "", {'path': ''}


def simplify_dataframe_rdp(
    df: pd.DataFrame,
    epsilon: float,
    extra_keep_mask: np.ndarray | None = None,
):
    """Simplify elevation data using Ramer-Douglas-Peucker algorithm."""
    service = get_pipe_analysis_service()
    return service.simplify_dataframe_rdp(df, epsilon, extra_keep_mask)


def compute_top_n_deviations(df: pd.DataFrame, flags: np.ndarray, n=5):
    """Compute the top N largest deviations from the RDP simplified line."""
    service = get_pipe_analysis_service()
    return service.compute_top_n_deviations(df, flags, n)


def get_pipes_csv_headers(dist_unit='mi'):
    """Get the correct column headers for pipes.csv based on distance unit"""
    service = get_pipe_analysis_service()
    return service.get_pipes_csv_headers(dist_unit)


def create_pipes_dataframe(df_current, reduced_df=None, segments=None, dist_unit='mi'):
    """
    Create a pipes.csv DataFrame with pipe names matching the reduced data segments,
    lengths, OD, and volume-conserving wall thickness using the correct formula.
    """
    service = get_pipe_analysis_service()
    return service.create_pipes_dataframe(df_current, reduced_df, segments, dist_unit)


def create_wt_dataframe(df_current, reduced_df=None, dist_unit='mi'):
    """
    Create a wall thickness CSV DataFrame with distance and wall thickness data.
    """
    service = get_pipe_analysis_service()
    return service.create_wt_dataframe(df_current, reduced_df, dist_unit)


def calculate_volume_conserving_wt(matching_rows, segment_length_user_units, od_inches, dist_unit):
    """
    Calculate volume-conserving wall thickness for the segment using original profile data.
    """
    service = get_pipe_analysis_service()
    return service.calculate_volume_conserving_wt(matching_rows, segment_length_user_units, od_inches, dist_unit)


SPLASH_IMG_PATH = os.path.join(ASSETS_DIR, SPLASH_IMG_NAME)
SPLASH_IMG_URL = f"/assets/{SPLASH_IMG_NAME}"
SPLASH_IMG_VISIBLE = os.path.exists(SPLASH_IMG_PATH)

# ---------------------------
# DB engine placeholder and line options (loaded lazily)
# ---------------------------
_engine = None
LINE_OPTIONS = []
_profile_cache: dict[str, pd.DataFrame] = {}

# ---------------------------
# RDP + helpers (copied from previous app.py)
# ---------------------------


def rdp_keep_mask(x: np.ndarray, y: np.ndarray, epsilon: float, must_keep_mask: np.ndarray = None):
    n = x.shape[0]
    if n <= 2:
        return np.ones(n, dtype=bool)
    keep = np.zeros(n, dtype=bool)
    keep[0] = True
    keep[-1] = True
    if must_keep_mask is not None:
        keep |= must_keep_mask.astype(bool)
    stack = [(0, n - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        x1, y1 = x[start], y[start]
        x2, y2 = x[end], y[end]
        idxs = np.arange(start + 1, end)
        if idxs.size == 0:
            continue
        px = x[idxs]
        py = y[idxs]
        dx = (x2 - x1)
        if dx == 0:
            y_line = np.full_like(py, y1, dtype=float)
        else:
            t = (px - x1) / dx
            y_line = y1 + t * (y2 - y1)
        dists = np.abs(py - y_line)
        max_rel = np.argmax(dists)
        max_dist = float(dists[max_rel])
        max_idx = int(idxs[max_rel])
        if must_keep_mask is not None and must_keep_mask[max_idx]:
            keep[max_idx] = True
            stack.append((start, max_idx))
            stack.append((max_idx, end))
            continue
        if max_dist > epsilon:
            keep[max_idx] = True
            stack.append((start, max_idx))
            stack.append((max_idx, end))
    if must_keep_mask is not None:
        keep |= must_keep_mask.astype(bool)
    return keep


# Removed local extrema computation as feature is deprecated


def simplify_dataframe_rdp(
    df: pd.DataFrame,
    epsilon: float,
    extra_keep_mask: np.ndarray | None = None,
):
    """Simplify elevation data using Ramer-Douglas-Peucker algorithm."""
    service = get_pipe_analysis_service()
    return service.simplify_dataframe_rdp(df, epsilon, extra_keep_mask)


def compute_top_n_deviations(df: pd.DataFrame, flags: np.ndarray, n=5):
    """Compute the top N largest deviations from the RDP simplified line."""
    service = get_pipe_analysis_service()
    return service.compute_top_n_deviations(df, flags, n)


# ---------------------------
# Pipe Analysis Functions
# ---------------------------

def get_pipes_csv_headers(dist_unit='mi'):
    """Get the correct column headers for pipes.csv based on distance unit"""
    service = get_pipe_analysis_service()
    return service.get_pipes_csv_headers(dist_unit)


def create_pipes_dataframe(df_current, reduced_df=None, segments=None, dist_unit='mi'):
    """
    Create a pipes.csv DataFrame with pipe names matching the reduced data segments,
    lengths, OD, and volume-conserving wall thickness using the correct formula.
    """
    service = get_pipe_analysis_service()
    return service.create_pipes_dataframe(df_current, reduced_df, segments, dist_unit)


def create_wt_dataframe(df_current, reduced_df=None, dist_unit='mi'):
    """
    Create a wall thickness CSV DataFrame with distance and wall thickness data.
    """
    service = get_pipe_analysis_service()
    return service.create_wt_dataframe(df_current, reduced_df, dist_unit)


def calculate_volume_conserving_wt(matching_rows, segment_length_user_units, od_inches, dist_unit):
    """
    Calculate volume-conserving wall thickness for the segment using original profile data.
    """
    service = get_pipe_analysis_service()
    return service.calculate_volume_conserving_wt(
        matching_rows, segment_length_user_units, od_inches, dist_unit
    )


# ---------------------------
# Layout (unchanged parts omitted for brevity)
# ---------------------------


DARK_CLASS = "d-flex flex-column bg-dark text-light"
LIGHT_CLASS = "d-flex flex-column bg-light text-dark"


def simplify_dataframe_rdp(
    df: pd.DataFrame,
    epsilon: float,
    extra_keep_mask: np.ndarray | None = None,
):
    """Simplify elevation data using Ramer-Douglas-Peucker algorithm."""
    service = get_pipe_analysis_service()
    return service.simplify_dataframe_rdp(df, epsilon, extra_keep_mask)


def compute_top_n_deviations(df: pd.DataFrame, flags: np.ndarray, n=5):
    """Compute the top N largest deviations from the RDP simplified line."""
    service = get_pipe_analysis_service()
    return service.compute_top_n_deviations(df, flags, n)


# ---------------------------
# Pipe Analysis Functions
# ---------------------------

def get_pipes_csv_headers(dist_unit='mi'):
    """Get the correct column headers for pipes.csv based on distance unit"""
    service = get_pipe_analysis_service()
    return service.get_pipes_csv_headers(dist_unit)


def create_pipes_dataframe(df_current, reduced_df=None, segments=None, dist_unit='mi'):
    """
    Create a pipes.csv DataFrame with pipe names matching the reduced data segments,
    lengths, OD, and volume-conserving wall thickness using the correct formula.
    """
    service = get_pipe_analysis_service()
    return service.create_pipes_dataframe(df_current, reduced_df, segments, dist_unit)


def create_wt_dataframe(df_current, reduced_df=None, dist_unit='mi'):
    """
    Create a wall thickness CSV DataFrame with distance and wall thickness data.
    """
    service = get_pipe_analysis_service()
    return service.create_wt_dataframe(df_current, reduced_df, dist_unit)


def calculate_volume_conserving_wt(matching_rows, segment_length_user_units, od_inches, dist_unit):
    """
    Calculate volume-conserving wall thickness for the segment using original profile data.
    """
    service = get_pipe_analysis_service()
    return service.calculate_volume_conserving_wt(
        matching_rows, segment_length_user_units, od_inches, dist_unit
    )


# ---------------------------
# Layout using DMC components
# ---------------------------

DARK_CLASS = "d-flex flex-column bg-dark text-light"
LIGHT_CLASS = "d-flex flex-column bg-light text-dark"


def create_elevation_page():
    """Create the elevation page layout"""
    layout = dmc.Container(
    id="page-container",
    fluid=True,
    style={
        'display': 'flex',
        'flexDirection': 'column',
        'padding': '8px',
        'overflowX': 'hidden',
        'overflowY': 'auto'
    },
    children=[
        dcc.Store(id='init-store', data={'ready': False}),
        dcc.Store(id='graph-data-store'),
        dcc.Store(id='mbs-data-store', data={}),
        dcc.Store(id='unit-store', data={'dist': 'mi', 'elev': 'ft'}),
        dcc.Store(id='features-collapse-store', data={'collapsed': False}),
        dcc.Store(id='directory-store-mbs-profile', data={'path': ''}),
        # Remove local theme store - use global plotly-theme-store instead
        dcc.Store(id='valve-state-store', data={'added': False}),
        html.Div(
            id='splash-overlay',
            children=html.Div([
                html.Img(
                    src=SPLASH_IMG_URL,
                    style={
                        'maxWidth': '1200px', 'width': '100%', 'height': 'auto',
                        'marginBottom': '16px',
                        'display': 'block' if SPLASH_IMG_VISIBLE else 'none'
                    }
                ),
                dmc.Loader(color='blue', size='lg'),
                html.Div("Loading data", style={
                         'fontSize': '22px', 'marginTop': '12px'})
            ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}),
            style={
                'position': 'fixed', 'zIndex': 2000,
                'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
                'backgroundColor': 'rgba(0,0,0,0.6)',
                'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'color': 'white'
            }
        ),
        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("Elevation Point Reduction",
                                  order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(
                                icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="elevation-help-modal-btn",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Ramer–Douglas–Peucker algorithm for pipeline elevation data reduction",
                             c="dimmed", ta="center", size="md")
                ], gap="xs")
            ]),

            dmc.Space(h="md"),
        ]),  # Close the dmc.Stack

        dmc.Grid([
            # Data selection card (Line & Section)
            dmc.GridCol([
                dmc.Card([
                    dmc.CardSection([
                        dmc.Text("Data Selection", fw=600)
                    ], p="sm", withBorder=True),
                    dmc.CardSection([
                        dmc.Stack([
                            # Line, Distance, and Elevation in one row
                            dmc.Group([
                                dmc.Stack([
                                    dmc.Text("Line", size="sm", fw=500),
                                    dmc.Autocomplete(
                                        id='line-dropdown',
                                        data=LINE_OPTIONS,
                                        placeholder='Select line…',
                                        clearable=True,
                                        disabled=True,
                                        selectFirstOptionOnChange=True,
                                        style={'minWidth': '120px',
                                               'width': '150px'}
                                    ),
                                ], gap="xs", style={'flex': '2'}),
                                dmc.Stack([
                                    dmc.Text("Distance", size="sm", fw=500),
                                    dmc.Select(
                                        id='distance-unit-dd',
                                        data=[
                                            {'label': 'km', 'value': 'km'},
                                            {'label': 'mi', 'value': 'mi'},
                                        ],
                                        value='mi',
                                        clearable=False,
                                        style={'width': '75px'}
                                    ),
                                ], gap="xs", style={'flex': '1'}),
                                dmc.Stack([
                                    dmc.Text("Elevation", size="sm", fw=500),
                                    dmc.Select(
                                        id='elevation-unit-dd',
                                        data=[
                                            {'label': 'm', 'value': 'm'},
                                            {'label': 'ft', 'value': 'ft'},
                                        ],
                                        value='ft',
                                        clearable=False,
                                        style={'width': '75px'}
                                    ),
                                ], gap="xs", style={'flex': '1'}),
                            ], align="flex-end", gap="xs", style={'width': '100%'}),
                            dmc.Button([
                                BootstrapIcon(icon="cloud-download",
                                              width=16, height=16),
                                html.Span("Load Data", style={
                                          'marginLeft': '8px'})
                            ], id='load-line-btn', variant="fill", fullWidth=True, size="sm"),
                        ], gap="xs")
                    ], p="xs")
                ], shadow="sm", h="100%")
            ], span=2),
            # Reduction settings card (epsilon + reduce)
            dmc.GridCol([
                dmc.Card([
                    dmc.CardSection([
                        dmc.Text("Reduction", fw=600)
                    ], p="sm", withBorder=True),
                    dmc.CardSection([
                        dmc.Stack([
                            dmc.Stack([
                                dmc.Text("Max vertical deviation:", size="sm"),
                                dmc.NumberInput(
                                    id='epsilon-input',
                                    min=0,
                                    step=0.001,
                                    value=0.1,
                                    style={'minWidth': '80px', 'width': '100%'}
                                ),
                            ], gap="xs"),
                            dmc.Button([
                                BootstrapIcon(
                                    icon="funnel", width=16, height=16),
                                html.Span("Reduce Points", style={
                                          'marginLeft': '8px'})
                            ], id='reduce-btn', variant="fill", fullWidth=True, size="sm"),
                        ], gap="xs")
                    ], p="xs")
                ], shadow="sm", h="100%")
            ], id='right-controls-col', span=2, style={'display': 'none'}),
            # MBS File Upload Card
            dmc.GridCol([
                dmc.Card([
                    dmc.CardSection([
                        dmc.Text("MBS Profile", fw=600)
                    ], p="sm", withBorder=True),
                    dmc.CardSection([
                        dmc.Stack([
                            # MBS directory input and browse button (no card wrapper)
                            dmc.Stack([
                                dmc.Group([
                                    dmc.TextInput(
                                        id='directory-input-mbs-profile',
                                        placeholder="Select folder containing inprep files...",
                                        value='',
                                        readOnly=True,
                                        leftSection=BootstrapIcon(icon="folder-open", width=16),
                                        size="md",
                                        style={"flex": 1}
                                    ),
                                    dmc.Button(
                                        BootstrapIcon(icon="search", width=16),
                                        id='browse-btn-mbs-profile',
                                        variant="outline",
                                        size="md"
                                    )
                                ], gap="xs", style={"alignItems": "end"})
                            ], gap="0"),
                            dcc.Loading(
                                id='mbs-loading',
                                type='default',
                                children=dmc.Stack([
                                    dmc.Text(
                                        id='mbs-file-status',
                                        size="sm",
                                        style={'minHeight': '0px'}
                                    ),
                                    dmc.Group([
                                        dmc.Button([
                                            BootstrapIcon(
                                                icon="upload", width=16, height=16),
                                            html.Span("Load Profile", style={
                                                      'marginLeft': '8px'})
                                        ], id='load-mbs-btn', variant="fill", disabled=True, size="sm", style={'flex': '1'}),
                                        dmc.Button([
                                            BootstrapIcon(
                                                icon="x-circle", width=16, height=16),
                                            html.Span("Unload", style={
                                                      'marginLeft': '8px'})
                                        ], id='unload-mbs-btn', variant="fill", disabled=True, size="sm", style={'flex': '1'})
                                    ], gap="xs", style={'width': '100%'})
                                ], gap="0")
                            ),
                        ], gap="xs")
                    ], p="xs")
                ], shadow="sm", h="100%")
            ], id='mbs-controls-col', span=3, style={'display': 'none'}),
            # Actions card (Save + Units combined inline)
            dmc.GridCol([
                dmc.Card([
                    dmc.CardSection([
                        dmc.Text("Export Profiles", fw=600)
                    ], p="sm", withBorder=True),
                    dmc.CardSection([
                        dmc.Stack([
                            dmc.Button([
                                BootstrapIcon(icon="download",
                                              width=16, height=16),
                                html.Span("Save Reduced Data", style={
                                          'marginLeft': '8px'})
                            ], id='save-btn', variant="fill", fullWidth=True, size="sm"),
                            dcc.Download(id="download-reduced-csv"),
                        ], gap="xs")
                    ], p="xs")
                ], shadow="sm", h="100%")
            ], id='actions-controls-col', span=2, style={'display': 'none'}),
        ], gutter="md", align="stretch"),

        dmc.Space(h="lg"),

        html.Div(id='main-content-container', className='main-layout', children=[
            # Elevation Profile Panel (70%)
            html.Div(id='elevation-panel', className='elevation-panel', children=[
                html.Div(className='panel-header', children=[
                    html.Span("Elevation Profile"),
                ]),
                html.Div(className='panel-content', children=[
                    dcc.Loading(
                        id='graph-loading', type='default',
                        children=dmc.Stack([
                            dmc.Group(
                                id='graph-stats', style={'padding': '6px 0', 'fontWeight': '600'}, justify="center"),
                            dmc.Text("💡 Tip: Click on any point in the elevation profile to open its location in ArcGIS.",
                                     c="dimmed", size="sm", style={'marginBottom': '8px'}),
                            dcc.Graph(id='comparison-graph', config={'responsive': True})
                        ], gap="xs", style={'height': '100%', 'minHeight': 0})
                    )
                ])
            ]),
            
            # Features Panel (30%, collapsible)
            html.Div(id='features-panel', className='features-panel', children=[
                html.Div(className='panel-header', style={
                    'display': 'flex !important', 
                    'justifyContent': 'space-between !important', 
                    'alignItems': 'center !important', 
                    'gridTemplateColumns': 'none !important'
                }, children=[
                    dmc.Button([
                        BootstrapIcon(
                            icon="plus", width=16, height=16),
                        html.Span("Add Selected Features", style={
                                  'marginLeft': '6px'})
                    ], id='add-valves-btn', className='features-panel-button', variant="outline", size="sm", style={'margin': '0', 'padding': '4px 6px', 'width': 'fit-content', 'whiteSpace': 'nowrap'}),
                    html.Button(
                        BootstrapIcon(icon="chevron-right", width=16, height=16),
                        id='features-collapse-btn',
                        className='collapse-toggle',
                        title='Collapse panel'
                    )
                ]),
                html.Div(className='panel-content', children=[
                    dcc.Loading(
                        id='results-loading', type='default',
                        children=dag.AgGrid(
                            id='results-grid', className='ag-theme-alpine', rowData=[], columnDefs=[],
                            defaultColDef={
                                'sortable': False, 'filter': True, 'resizable': True, 'editable': True},
                            filterModel={}, columnSize='sizeToFit',
                            dashGridOptions={'rowHeight': 24, 'headerHeight': 28, 'enableCellTextSelection': True,
                                             'ensureDomOrder': True, 'pagination': True, 'paginationPageSize': 40,
                                             'rowSelection': 'multiple', 'suppressRowClickSelection': True}
                        ),
                        style={'height': '100%', 'minHeight': 0}
                    )
                ])
            ])
        ])
    ]
)
    
    return layout


# ---------------------------
# Callbacks (features collapse + main logic)
# ---------------------------

@dash.callback(
    [Output('features-panel', 'className'),
     Output('elevation-panel', 'className'),
     Output('features-collapse-btn', 'children')],
    [Input('features-collapse-btn', 'n_clicks')],
    [State('features-collapse-store', 'data')],
    prevent_initial_call=True
)
def toggle_features_panel(n_clicks, collapse_data):
    """Handle features panel collapse/expand"""
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update
    
    current_collapsed = collapse_data.get('collapsed', False) if collapse_data else False
    new_collapsed = not current_collapsed
    
    # Update CSS classes and button icon
    features_class = 'features-panel collapsed' if new_collapsed else 'features-panel'
    elevation_class = 'elevation-panel expanded' if new_collapsed else 'elevation-panel'
    # Chevron points left when collapsed, right when open
    button_icon = BootstrapIcon(icon='chevron-left' if new_collapsed else 'chevron-right', width=16, height=16)
    return features_class, elevation_class, button_icon


@dash.callback(
    Output('features-collapse-store', 'data'),
    [Input('features-collapse-btn', 'n_clicks')],
    [State('features-collapse-store', 'data')],
    prevent_initial_call=True
)
def update_collapse_store(n_clicks, collapse_data):
    """Update the collapse state in the store"""
    if not n_clicks:
        return dash.no_update
    
    current_collapsed = collapse_data.get('collapsed', False) if collapse_data else False
    return {'collapsed': not current_collapsed}


@dash.callback(
    [Output('line-dropdown', 'data'),
     Output('line-dropdown', 'disabled'),
     Output('init-store', 'data'),
     Output('splash-overlay', 'style')],
    [Input('init-store', 'data')],
    prevent_initial_call=False
)
def initialize_page(init_data):
    """Initialize the page by loading pipeline lines and hiding splash screen"""
    if init_data and init_data.get('ready'):
        return dash.no_update, dash.no_update, dash.no_update, {'display': 'none'}

    try:
        onesource_service = get_onesource_service()
        df = onesource_service.get_pipeline_lines()
        options = [{"label": str(v), "value": str(v)}
                   for v in df['PLIntegrityLineSegmentNumber'].astype(str).tolist()]
        return options, False, {'ready': True}, {'display': 'none'}
    except Exception as e:
        print(f"ERROR in initialize_page: {e}")
        import traceback
        traceback.print_exc()
        # Still mark as ready and hide splash, but with empty options
        return [], False, {'ready': True}, {'display': 'none'}


@dash.callback(
    [Output('load-line-btn', 'disabled'),
     Output('right-controls-col', 'style'),
     Output('mbs-controls-col', 'style'),
     Output('actions-controls-col', 'style')],
    [Input('line-dropdown', 'value')],
    prevent_initial_call=True
)
def handle_line_selection(line_value):
    """Enable controls when a line is selected"""
    if line_value:
        return False, {'display': 'block'}, {'display': 'block'}, {'display': 'block'}
    else:
        return True, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}


@dash.callback(
    [Output('results-grid', 'rowData', allow_duplicate=True),
     Output('graph-data-store', 'data', allow_duplicate=True),
     Output('unit-store', 'data')],
    [Input('load-line-btn', 'n_clicks')],
    [State('line-dropdown', 'value'),
     State('distance-unit-dd', 'value'),
     State('elevation-unit-dd', 'value')],
    prevent_initial_call=True
)
def load_elevation_data(load_clicks, line_value, dist_unit, elev_unit):
    """Load elevation data for the selected pipeline line"""
    if not load_clicks or not line_value:
        return dash.no_update, dash.no_update, dash.no_update

    try:
        onesource_service = get_onesource_service()
        df = onesource_service.get_elevation_profile(line_value)

        if df is not None and not df.empty:
            # Prepare data for grid display
            row_data = df.to_dict('records')
            unit_data = {'dist': dist_unit, 'elev': elev_unit}

            return row_data, row_data, unit_data
        else:
            return [], [], {'dist': dist_unit, 'elev': elev_unit}

    except Exception as e:
        print(f"ERROR in load_elevation_data: {e}")
        import traceback
        traceback.print_exc()
        return [], [], {'dist': dist_unit, 'elev': elev_unit}


# Disabled - functionality moved to main callback to fix Load Data issue
# @dash.callback(
#     [Output('comparison-graph', 'figure', allow_duplicate=True),
#      Output('graph-stats', 'children', allow_duplicate=True)],
#     [Input('reduce-btn', 'n_clicks'),
#      Input('graph-data-store', 'data'),
#      Input('unit-store', 'data'),
#      Input('plotly-theme-store', 'data')],
#     [State('epsilon-input', 'value')],
#     prevent_initial_call=True
# )
# def update_graph(reduce_clicks, cached_rows, unit_data, theme_data, epsilon_value):
#     """Update the elevation graph with original and reduced data"""
#     try:
#         # Get template from theme data, default to mantine_light
#         template = theme_data.get('template', 'mantine_light') if theme_data else 'mantine_light'
#
#         # Unit helpers
#         dist_unit = ((unit_data or {}).get('distance') or 'mi')
#         elev_unit = ((unit_data or {}).get('elevation') or 'ft')
#         dist_label = {'m': 'meters', 'km': 'kilometers',
#                       'mi': 'miles'}.get(dist_unit, 'miles')
#         elev_label = {'m': 'm', 'ft': 'ft'}.get(elev_unit, 'ft')
#         DIST_FACTOR = {'m': 1.0, 'km': 0.001,
#                        'mi': 0.000621371}.get(dist_unit, 0.000621371)
#         ELEV_FACTOR = {'m': 1.0, 'ft': 3.28084}.get(elev_unit, 3.28084)
#
#         # Early exit if no data
#         if not cached_rows:
#             empty_fig = go.Figure()
#             empty_fig.update_layout(template=template, margin=dict(l=30, r=30, t=40, b=20),
#                                     xaxis_title=f'Distance ({dist_label})', yaxis_title=f'Elevation ({elev_label})')
#             stats = dmc.Group([
#                 dmc.Badge("Input Points: 0", color="blue", variant="dot"),
#                 dmc.Badge("Output Points: 0", color="green", variant="dot"),
#             ], gap="sm")
#             return empty_fig, stats
#
#         # Build dataframe
#         df_current = pd.DataFrame(cached_rows)
#         if df_current.empty:
#             empty_fig = go.Figure()
#             empty_fig.update_layout(template=template, margin=dict(l=30, r=30, t=40, b=20),
#                                     xaxis_title=f'Distance ({dist_label})', yaxis_title=f'Elevation ({elev_label})')
#             stats = dmc.Group([
#                 dmc.Badge("Input Points: 0", color="blue", variant="dot"),
#                 dmc.Badge("Output Points: 0", color="green", variant="dot"),
#             ], gap="sm", justify="center")
#             return empty_fig, stats
#
#         # Convert distance and elevation columns using the working field names
#         if 'CorrectedMilepost' in df_current.columns:
#             df_current['DistanceMeters'] = pd.to_numeric(
#                 df_current['CorrectedMilepost'], errors='coerce') / DIST_FACTOR
#         elif 'HydroMilePost' in df_current.columns:
#             df_current['DistanceMeters'] = pd.to_numeric(
#                 df_current['HydroMilePost'], errors='coerce') / DIST_FACTOR
#
#         if 'ILIElevationMeters' in df_current.columns:
#             df_current['ElevationMeters'] = pd.to_numeric(
#                 df_current['ILIElevationMeters'], errors='coerce')
#
#         # Clean data
#         required_cols = ['DistanceMeters', 'ElevationMeters']
#         if not all(col in df_current.columns for col in required_cols):
#             empty_fig = go.Figure()
#             empty_fig.update_layout(template=template, margin=dict(l=30, r=30, t=40, b=20),
#                                     xaxis_title=f'Distance ({dist_label})', yaxis_title=f'Elevation ({elev_label})')
#             stats = dmc.Group([
#                 dmc.Badge("Data Error: Missing columns",
#                           color="red", variant="dot"),
#             ], gap="sm", justify="center")
#             return empty_fig, stats
#
#         df_current = df_current.dropna(
#             subset=required_cols).reset_index(drop=True)
#         if df_current.empty:
#             empty_fig = go.Figure()
#             empty_fig.update_layout(template=template, margin=dict(l=30, r=30, t=40, b=20),
#                                     xaxis_title=f'Distance ({dist_label})', yaxis_title=f'Elevation ({elev_label})')
#             stats = dmc.Group([
#                 dmc.Badge("No valid data", color="red", variant="dot"),
#             ], gap="sm", justify="center")
#             return empty_fig, stats
#
#         # Apply unit conversions for plotting
#         df_current['Milepost'] = df_current['DistanceMeters'] * DIST_FACTOR
#         df_current['Elevation'] = df_current['ElevationMeters'] * ELEV_FACTOR
#         df_current = df_current.sort_values(
#             'DistanceMeters', kind='stable').reset_index(drop=True)
#
#         # Create figure
#         fig = go.Figure()
#         fig.update_layout(template=template, margin=dict(l=30, r=30, t=40, b=20),
#                           xaxis_title=f'Distance ({dist_label})', yaxis_title=f'Elevation ({elev_label})')
#
#         # Add original data trace
#         fig.add_trace(go.Scatter(
#             x=df_current['Milepost'],
#             y=df_current['Elevation'],
#             mode='lines',
#             name='Original',
#             line=dict(width=1)
#         ))
#
#         # Add reduced data trace if reduce button was clicked
#         reduced_points = len(df_current)
#         if reduce_clicks and reduce_clicks > 0 and epsilon_value:
#             try:
#                 reduced_df, flags = simplify_dataframe_rdp(
#                     df_current, epsilon_value)
#                 if not reduced_df.empty:
#                     fig.add_trace(go.Scatter(
#                         x=reduced_df['Milepost'],
#                         y=reduced_df['Elevation'],
#                         mode='lines',
#                         name='Reduced',
#                         line=dict(width=2)
#                     ))
#                     reduced_points = len(reduced_df)
#             except Exception as e:
#                 print(f"Error in RDP simplification: {e}")
#
#         # Update stats
#         stats = dmc.Group([
#             dmc.Badge(f"Input Points: {len(df_current)}",
#                       color="blue", variant="dot"),
#             dmc.Badge(f"Output Points: {reduced_points}",
#                       color="green", variant="dot"),
#         ], gap="sm", justify="center")
#
#         return fig, stats
#
#     except Exception as e:
#         print(f"Error in update_graph: {e}")
#         import traceback
#         traceback.print_exc()
#         empty_fig = go.Figure()
#         stats = dmc.Group([
#             dmc.Badge("Error loading graph", color="red", variant="dot"),
#         ], gap="sm", justify="center")
#         return empty_fig, stats


# Enable Load Data button only when a line is selected
@dash.callback(Output('load-line-btn', 'disabled', allow_duplicate=True), [Input('line-dropdown', 'value')], prevent_initial_call=True)
def toggle_load_button(line_value):
    return not bool(line_value)


# Capture units at the time of loading so future updates don't trigger from unit changes
@dash.callback(Output('unit-store', 'data', allow_duplicate=True),
               [Input('load-line-btn', 'n_clicks')],
               [State('distance-unit-dd', 'value'), State('elevation-unit-dd', 'value'), State('unit-store', 'data')], prevent_initial_call=True)
def capture_units_on_load(load_clicks, dist_unit, elev_unit, current):
    if not load_clicks:
        raise dash.exceptions.PreventUpdate
    return {'distance': dist_unit or 'mi', 'elevation': elev_unit or 'ft'}


@dash.callback(Output('unit-store', 'data', allow_duplicate=True),
               [Input('distance-unit-dd', 'value'), Input('elevation-unit-dd', 'value')],
               [State('unit-store', 'data')], prevent_initial_call=True)
def update_units_on_change(dist_unit, elev_unit, current_units):
    """Update unit store when distance or elevation unit dropdown changes"""
    if dist_unit is None and elev_unit is None:
        raise dash.exceptions.PreventUpdate
    
    # Get current units or use defaults
    current_units = current_units or {'distance': 'mi', 'elevation': 'ft'}
    
    # Update the changed unit(s)
    updated_units = current_units.copy()
    if dist_unit is not None:
        updated_units['distance'] = dist_unit
    if elev_unit is not None:
        updated_units['elevation'] = elev_unit
        
    return updated_units


# Manage valve state: reset when data/grid changes; set added when button clicked
@dash.callback(
    Output('valve-state-store', 'data'),
    [Input('add-valves-btn', 'n_clicks'),
     Input('results-grid', 'rowData'),
     Input('line-dropdown', 'value')],
    [State('valve-state-store', 'data')]
)
def toggle_valves(add_clicks, row_data, line_val, current):
    current = current or {'added': False}
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    trig_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if trig_id == 'add-valves-btn':
        return {'added': True}
    # Any data or selection change resets valves off by default
    return {'added': False}


@dash.callback(Output('results-grid', 'className'), Input('color-scheme-switch', 'checked'))
def sync_aggrid_theme(is_dark):
    return 'ag-theme-alpine-dark' if is_dark else 'ag-theme-alpine'


# MBS Folder Input Callbacks
@dash.callback(
    [Output('load-mbs-btn', 'disabled'),
     Output('unload-mbs-btn', 'disabled'),
     Output('load-mbs-btn', 'style'),
     Output('unload-mbs-btn', 'style'),
     Output('mbs-data-store', 'data'),
     Output('notification-container', 'sendNotifications', allow_duplicate=True)],
    [Input('directory-store-mbs-profile', 'data'),
     Input('load-mbs-btn', 'n_clicks'),
     Input('unload-mbs-btn', 'n_clicks')],
    [State('mbs-data-store', 'data')],
    prevent_initial_call=True
)
def handle_mbs_folder_input(directory_data, load_clicks, unload_clicks, current_data):
    ctx = dash.callback_context

    if not ctx.triggered:
        # Initial: show Load (disabled), hide Unload
        return True, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, current_data or {}, dash.no_update

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Extract folder path from directory selector data
    folder_path = directory_data.get('path', '') if directory_data else ''

    # If the directory selector was cleared, automatically unload the profile
    if trigger_id == 'directory-store-mbs-profile' and (not folder_path or not folder_path.strip()):
        # Clear the profile if it was loaded
        if current_data and current_data.get('loaded'):
            unload_notification = [{
                "title": "MBS Profile Unloaded",
                "message": "MBS Profile unloaded (directory cleared)",
                "color": "gray",
                "autoClose": 3000,
                "action": "show"
            }]
            cleared_data = {'loaded': False, 'data': [],
                            'folder_path': '', 'ready_to_load': False}
            return True, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, cleared_data, unload_notification
        else:
            # No profile was loaded, just reset UI
            return True, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, {}, dash.no_update

    if trigger_id == 'directory-store-mbs-profile' and folder_path:
        try:
            folder_path = folder_path.strip()

            if not os.path.exists(folder_path):
                error_notification = [{
                    "title": "Error",
                    "message": f"Folder not found: {folder_path}",
                    "color": "red",
                    "autoClose": 5000,
                    "action": "show"
                }]
                return True, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, dash.no_update, error_notification

            if not os.path.isdir(folder_path):
                error_notification = [{
                    "title": "Error",
                    "message": f"Path is not a folder: {folder_path}",
                    "color": "red",
                    "autoClose": 5000,
                    "action": "show"
                }]
                return True, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, dash.no_update, error_notification

            # Check if folder contains inprep files
            has_inprep = False
            for f in os.listdir(folder_path):
                if f.lower().endswith('.inprep') or f.lower() == 'inprep.txt':
                    has_inprep = True
                    break

            if not has_inprep:
                warning_notification = [{
                    "title": "Warning",
                    "message": "No inprep files found in folder",
                    "color": "orange",
                    "autoClose": 5000,
                    "action": "show"
                }]
                return True, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, dash.no_update, warning_notification

            success_notification = [{
                "title": "Ready to Load",
                "message": f"MBS profile directory validated: {folder_path}",
                "color": "green",
                "autoClose": 3000,
                "action": "show"
            }]
            ready_data = current_data.copy() if current_data else {}
            ready_data.update(
                {'ready_to_load': True, 'folder_path': folder_path})
            return False, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, ready_data, success_notification

        except Exception as e:
            error_notification = [{
                "title": "Error",
                "message": f"Error validating directory: {str(e)}",
                "color": "red",
                "autoClose": 5000,
                "action": "show"
            }]
            return True, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, dash.no_update, error_notification

    elif trigger_id == 'load-mbs-btn' and load_clicks:
        try:
            if not current_data or not current_data.get('ready_to_load'):
                raise ValueError("No folder ready to load")

            folder_path = current_data.get('folder_path', '')
            if not folder_path:
                raise ValueError("No folder path specified")

            # Load elevation data using the service
            df_profile = fetch_elevation_profile(folder_path)

            if df_profile is None or df_profile.empty:
                raise ValueError("No elevation data found in folder")

            # Validate data
            if not validate_elevation_data(df_profile):
                raise ValueError("Invalid elevation data format")

            # Store in the expected format
            profile_data = df_profile.to_dict('records')

            success_notification = [{
                "title": "MBS Profile Loaded",
                "message": f"MBS Profile loaded successfully ({len(profile_data)} points)",
                "color": "green",
                "autoClose": 3000,
                "action": "show"
            }]

            loaded_data = {
                'loaded': True,
                'data': profile_data,
                'folder_path': folder_path,
                'ready_to_load': False
            }

            return True, False, {'display': 'none'}, {'display': 'inline-block', 'width': '100%'}, loaded_data, success_notification

        except Exception as e:
            error_notification = [{
                "title": "Load Failed",
                "message": f"Failed to load MBS profile: {str(e)}",
                "color": "red",
                "autoClose": 5000,
                "action": "show"
            }]
            return True, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, dash.no_update, error_notification

    elif trigger_id == 'unload-mbs-btn' and unload_clicks:
        # Unload the profile
        unload_notification = [{
            "title": "MBS Profile Unloaded",
            "message": "MBS Profile unloaded successfully",
            "color": "gray",
            "autoClose": 3000,
            "action": "show"
        }]

        unloaded_data = {'loaded': False, 'data': [],
                         'folder_path': '', 'ready_to_load': False}
        return True, True, {'display': 'inline-block', 'width': '100%'}, {'display': 'none'}, unloaded_data, unload_notification

    # Default fallback
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update


# Main data processing callback
@dash.callback(
    [Output('comparison-graph', 'figure'),
     Output('graph-stats', 'children'),
     Output('download-reduced-csv', 'data'),
     Output('page-container', 'className')],
    [Input('reduce-btn', 'n_clicks'),
     Input('load-line-btn', 'n_clicks'),
     Input('save-btn', 'n_clicks'),
     Input('valve-state-store', 'data'),
     Input('mbs-data-store', 'data'),
     Input('graph-data-store', 'data'),
     Input('unit-store', 'data'),
     Input('plotly-theme-store', 'data')],
    [State('results-grid', 'rowData'),
     State('comparison-graph', 'relayoutData'),
     State('epsilon-input', 'value'),
     State('results-grid', 'selectedRows')]
)
def on_reduce_or_save(reduce_clicks, load_clicks, save_clicks, valve_state, mbs_data, cached_rows, unit_data, theme_data, grid_rows, relayout_data, eps_input, selected_rows):
    try:
        ctx = dash.callback_context
        # Get template from theme data, default to mantine_light
        template = theme_data.get('template', 'mantine_light') if theme_data else 'mantine_light'
        dark_mode = template == 'mantine_dark'

        # Unit helpers
        dist_unit = ((unit_data or {}).get('distance') or 'mi')
        elev_unit = ((unit_data or {}).get('elevation') or 'ft')
        dist_label = {'m': 'meters', 'km': 'kilometers',
                      'mi': 'miles'}.get(dist_unit, 'miles')
        elev_label = {'m': 'm', 'ft': 'ft'}.get(elev_unit, 'ft')
        DIST_FACTOR = {'m': 1.0, 'km': 0.001,
                       'mi': 0.000621371}.get(dist_unit, 0.000621371)
        ELEV_FACTOR = {'m': 1.0, 'ft': 3.28084}.get(elev_unit, 3.28084)

        # Guard: ignore valve-state resets unless Add Selected just toggled on
        if ctx and ctx.triggered:
            trig_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if trig_id == 'valve-state-store' and not (isinstance(valve_state, dict) and valve_state.get('added')):
                return dash.no_update, dash.no_update, dash.no_update, (DARK_CLASS if dark_mode else LIGHT_CLASS)
            
            # Guard: ignore MBS data changes when only directory selection (ready_to_load) changes
            # Only trigger on actual load/unload operations
            if trig_id == 'mbs-data-store':
                if isinstance(mbs_data, dict):
                    # Only update if profile is actually loaded or unloaded
                    is_loaded = mbs_data.get('loaded', False)
                    ready_to_load = mbs_data.get('ready_to_load', False)
                    # If only ready_to_load is set but not loaded, don't update graph
                    if ready_to_load and not is_loaded:
                        return dash.no_update, dash.no_update, dash.no_update, (DARK_CLASS if dark_mode else LIGHT_CLASS)

        # Early exit if no data
        if not grid_rows and not cached_rows:
            empty_fig = go.Figure()
            page_class = DARK_CLASS if dark_mode else LIGHT_CLASS
            empty_fig.update_layout(template=template, margin=dict(l=30, r=30, t=40, b=20),
                                    xaxis_title=f'Distance ({dist_label})', yaxis_title=f'Elevation ({elev_label})')
            stats = dmc.Group([
                dmc.Badge("Input Points: 0", color="blue",
                          className="mx-1", variant="dot"),
                dmc.Badge("Output Points: 0", color="green",
                          className="mx-1", variant="dot"),
                dmc.Badge("Top 3 deviations: —", color="yellow",
                          className="mx-1", variant="dot"),
            ], className="mb-2")
            return empty_fig, stats, dash.no_update, page_class

        # Build dataframe for plotting from the full dataset store (prefer cached_rows)
        df_current = pd.DataFrame(cached_rows or grid_rows or [])
        if df_current.empty or not set(['DistanceMeters', 'ElevationMeters']).issubset(df_current.columns):
            empty_fig = go.Figure()
            page_class = DARK_CLASS if dark_mode else LIGHT_CLASS
            empty_fig.update_layout(template=template, margin=dict(l=30, r=30, t=40, b=20),
                                    xaxis_title=f'Distance ({dist_label})', yaxis_title=f'Elevation ({elev_label})')
            stats = dmc.Group([
                dmc.Badge("Input Points: 0", color="blue",
                          className="mx-1", variant="dot"),
                dmc.Badge("Output Points: 0", color="green",
                          className="mx-1", variant="dot"),
                dmc.Badge("Top 3 deviations: —", color="yellow",
                          className="mx-1", variant="dot"),
            ], className="mb-2", justify="center")
            return empty_fig, stats, dash.no_update, page_class

        # Clean and convert
        df_current = df_current.copy()
        df_current['DistanceMeters'] = pd.to_numeric(
            df_current['DistanceMeters'], errors='coerce')
        df_current['ElevationMeters'] = pd.to_numeric(
            df_current['ElevationMeters'], errors='coerce')
        df_current = df_current.dropna(
            subset=['DistanceMeters', 'ElevationMeters']).reset_index(drop=True)
        if not df_current.empty:
            min_dist = df_current['DistanceMeters'].min()
            if min_dist < 0:
                df_current['DistanceMeters'] = df_current['DistanceMeters'] - min_dist

        # Apply unit conversions for plotting/simplification
        df_current['Milepost'] = df_current['DistanceMeters'] * DIST_FACTOR
        df_current['Elevation'] = df_current['ElevationMeters'] * ELEV_FACTOR
        df_current = df_current.sort_values(
            'DistanceMeters', kind='stable').reset_index(drop=True)
        df_current['OrigRowID'] = np.arange(len(df_current), dtype=int)

        # Detect pipe size changes for divider placement (always detect, regardless of valve state)
        service = get_pipe_analysis_service()
        divider_positions = service.detect_pipe_size_changes(df_current)

        eps_val = float(eps_input or 0.1)
        epsilon_abs = max(eps_val, 0.0)

        # Feature placement by meter distance (valves + stations)
        show_valves = bool(valve_state.get('added')) if isinstance(
            valve_state, dict) else False
        mask_valves = np.zeros(len(df_current), dtype=bool)
        valve_positions_gate = []
        valve_positions_check = []
        station_positions = []  # (x_milepost, y_elev, name)
        if show_valves:
            try:
                dists_m = df_current['DistanceMeters'].to_numpy(dtype=float)
                elev_plot = df_current['Elevation'].to_numpy(dtype=float)
                dist_plot = df_current['Milepost'].to_numpy(dtype=float)
                nearest_idxs = []  # (idx, type, label)
                for r in (selected_rows or []):
                    feats = str((r or {}).get('Features', ''))

                    # Try to get user-edited distance value from DistanceMeter column
                    # This represents the potentially edited value in the grid
                    dm = None
                    if 'DistanceMeter' in r and r['DistanceMeter'] is not None:
                        # Convert user-edited DistanceMeter back to meters based on current unit
                        try:
                            user_dist = float(r['DistanceMeter'])
                            if dist_unit == 'km':
                                dm = user_dist * 1000.0  # Convert km to m
                            elif dist_unit == 'mi':
                                dm = user_dist / 0.000621371  # Convert miles to m
                            else:  # meters
                                dm = user_dist
                        except (TypeError, ValueError):
                            dm = None

                    # Fallback to original DistanceMeters if no edited values found
                    if dm is None:
                        dm = r.get('DistanceMeters')
                        try:
                            dm = float(dm)
                        except (TypeError, ValueError):
                            dm = None

                    if dm is None or dists_m.size == 0:
                        continue
                    idx = int(np.nanargmin(np.abs(dists_m - dm)))
                    is_gate = ("GATE" in feats.upper())
                    is_check = ("CHECK" in feats.upper())
                    st_name = str((r or {}).get('Station') or '').strip()
                    if is_gate or is_check:
                        nearest_idxs.append(
                            (idx, 'GATE' if is_gate else 'CHECK', ''))
                    if st_name:
                        nearest_idxs.append((idx, 'STATION', st_name))
                idx_to_type = {}
                idx_to_station_label = {}
                for idx, typ, label in nearest_idxs:
                    prev = idx_to_type.get(idx)
                    # Prefer STATION over any valve; otherwise prefer GATE over CHECK
                    if prev is None:
                        idx_to_type[idx] = typ
                    else:
                        if typ == 'STATION':
                            idx_to_type[idx] = 'STATION'
                        elif prev != 'STATION':
                            if typ == 'GATE' and prev != 'GATE':
                                idx_to_type[idx] = 'GATE'
                            elif typ == 'CHECK' and prev not in ('GATE', 'CHECK'):
                                idx_to_type[idx] = 'CHECK'
                    if typ == 'STATION' and label:
                        idx_to_station_label[idx] = label
                # Determine which indices have a nonblank Station in the underlying data
                station_nonblank_idx = set()
                st_series_norm = None
                try:
                    st_series_norm = df_current.get('Station')
                    if st_series_norm is not None:
                        st_series_norm = st_series_norm.astype(
                            object).where(~pd.isna(st_series_norm), '')
                        st_series_norm = st_series_norm.astype(
                            str).replace({'nan': ''})
                        station_nonblank_idx = set(np.flatnonzero(
                            st_series_norm.str.strip().ne('').to_numpy()))
                except Exception:
                    station_nonblank_idx = set()

                for idx, typ in idx_to_type.items():
                    mask_valves[idx] = True
                    x = float(dist_plot[idx])
                    y = float(elev_plot[idx])
                    # If station was explicitly selected at this index, show it and skip valves
                    if typ == 'STATION':
                        label = idx_to_station_label.get(idx, '')
                        if not label and st_series_norm is not None:
                            try:
                                label = str(st_series_norm.iloc[idx])
                            except Exception:
                                label = ''
                        station_positions.append((x, y, label))
                        continue
                    # Otherwise, if the underlying data has a nonblank station at this index, prefer station
                    if idx in station_nonblank_idx:
                        label = idx_to_station_label.get(idx, '')
                        if not label and st_series_norm is not None:
                            try:
                                label = str(st_series_norm.iloc[idx])
                            except Exception:
                                label = ''
                        station_positions.append((x, y, label))
                        continue
                    # Fall back to valve icons
                    if typ == 'GATE':
                        valve_positions_gate.append((x, y))
                    elif typ == 'CHECK':
                        valve_positions_check.append((x, y))
                # Optionally add ALL nonblank stations from the full dataset (disabled to respect selections)
                auto_add_all_stations = False
                if auto_add_all_stations:
                    try:
                        st_series = df_current.get('Station')
                        if st_series is not None:
                            # Normalize to strings and blank out NaNs
                            st_series = st_series.astype(
                                object).where(~pd.isna(st_series), '')
                            st_series = st_series.astype(
                                str).replace({'nan': ''})
                            nonblank_idxs = np.flatnonzero(
                                st_series.str.strip().ne('').to_numpy())
                            # Track existing station indices to avoid duplicates, and avoid overlapping valve indices
                            existing_station_idx = set()
                            for _, y, _ in station_positions:
                                for i, (x_mp, y_el, _) in enumerate(station_positions):
                                    existing_station_idx.add(i)
                            for idx in nonblank_idxs:
                                if idx not in existing_station_idx and idx not in idx_to_type:
                                    try:
                                        x_mp = float(dist_plot[idx])
                                        y_el = float(elev_plot[idx])
                                        label = str(st_series.iloc[idx])
                                        station_positions.append(
                                            (x_mp, y_el, label))
                                        mask_valves[idx] = True
                                    except Exception:
                                        pass
                    except Exception:
                        pass
            except Exception:
                pass

        # Check first and last points for stations if they have data
        try:
            st_series_clean = df_current.get('Station')
            if st_series_clean is not None:
                st_series_clean = st_series_clean.astype(
                    object).where(~pd.isna(st_series_clean), '')
                st_series_clean = st_series_clean.astype(
                    str).replace({'nan': ''})
                # Check first point for station
                first_station = st_series_clean.iloc[0].strip()
                if first_station:
                    mask_valves[0] = True
                    if show_valves:  # Only add to display if valves are being shown
                        x_first = float(dist_plot[0])
                        y_first = float(elev_plot[0])
                        # Check if first point already in station_positions
                        already_added = any(
                            abs(x - x_first) < 1e-6 for x, y, label in station_positions)
                        if not already_added:
                            station_positions.append(
                                (x_first, y_first, first_station))

                # Check last point for station
                if len(st_series_clean) > 1:  # Avoid duplicate if only one point
                    last_station = st_series_clean.iloc[-1].strip()
                    if last_station:
                        mask_valves[-1] = True
                        if show_valves:  # Only add to display if valves are being shown
                            x_last = float(dist_plot[-1])
                            y_last = float(elev_plot[-1])
                            # Check if last point already in station_positions
                            already_added = any(
                                abs(x - x_last) < 1e-6 for x, y, label in station_positions)
                            if not already_added:
                                station_positions.append(
                                    (x_last, y_last, last_station))
        except Exception:
            pass

        # Check what triggered this callback
        triggered_id = None
        if ctx and ctx.triggered:
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # Always perform RDP reduction (needed for save functionality and valve mask)
        reduced_df, flags = simplify_dataframe_rdp(
            df_current, epsilon=epsilon_abs, extra_keep_mask=mask_valves)
        top_devs = compute_top_n_deviations(df_current, flags, n=3)

        # Theme
        if dark_mode:
            page_class = DARK_CLASS
            legend_bgcolor = 'rgba(30,41,59,0.85)'
            legend_font_color = 'white'
        else:
            page_class = LIGHT_CLASS
            legend_bgcolor = 'rgba(255,255,255,0.85)'
            legend_font_color = 'black'

        fig = go.Figure()
        fig.update_layout(template=template)
        
        # Always add original trace
        fig.add_trace(go.Scatter(
            x=df_current['Milepost'], y=df_current['Elevation'],
            mode='lines', name='Original', line=dict(width=1)
        ))
        
        # Show reduced trace if reduce button has been clicked (preserve state when loading new data)
        show_reduced = reduce_clicks and reduce_clicks > 0
        if show_reduced:
            fig.add_trace(go.Scatter(
                x=reduced_df['Milepost'], y=reduced_df['Elevation'],
                mode='lines', name='Reduced', line=dict(width=2)
            ))

        # Add MBS profile if available
        if isinstance(mbs_data, dict) and mbs_data.get('loaded'):
            mbs_profile = mbs_data.get('data', [])
            if mbs_profile:
                mbs_df = pd.DataFrame(mbs_profile)
                if not mbs_df.empty and 'DistanceMeters' in mbs_df.columns and 'ElevationMeters' in mbs_df.columns:
                    mbs_df['Milepost'] = mbs_df['DistanceMeters'] * DIST_FACTOR
                    mbs_df['Elevation'] = mbs_df['ElevationMeters'] * ELEV_FACTOR
                    fig.add_trace(go.Scatter(
                        x=mbs_df['Milepost'], y=mbs_df['Elevation'],
                        mode='lines', name='MBS Profile', line=dict(color='orange', width=2, dash='dash')
                    ))

        # Feature icons (valves + stations + dividers) - using SVG images like LDUTC
        n_valves = int(len(valve_positions_gate) + len(valve_positions_check))
        n_stations = int(len(station_positions))
        n_dividers = int(len(divider_positions))
        n_features = n_valves + n_stations + n_dividers
        if n_features > 0:
            try:
                # Use current zoom level if available
                x_range = float(df_current['Milepost'].max(
                ) - df_current['Milepost'].min() or 1.0)
                y_range = float(df_current['Elevation'].max(
                ) - df_current['Elevation'].min() or 1.0)

                # Determine visual size scale for SVG icons
                if n_features > 300:
                    frac_y, frac_x = 0.030, 0.008
                elif n_features > 150:
                    frac_y, frac_x = 0.042, 0.011
                elif n_features > 60:
                    frac_y, frac_x = 0.054, 0.014
                else:
                    frac_y, frac_x = 0.070, 0.018

                _valve_icon_scale = 1.75
                _station_icon_scale = 2.5  # Make stations larger than valves
                sizey = max(y_range * frac_y * _valve_icon_scale, 1e-9)
                sizex = max(x_range * frac_x * _valve_icon_scale, 1e-9)
                # Station sizing - larger than valve icons
                station_sizey = max(y_range * frac_y *
                                    _station_icon_scale, 1e-9)
                station_sizex = max(x_range * frac_x *
                                    _station_icon_scale, 1e-9)

                # Build layout images for valves and stations
                layout_images = list(
                    fig.layout.images) if fig.layout.images else []

                # Add gate valve SVGs
                for mp, elev in valve_positions_gate:
                    layout_images.append(dict(
                        source='/assets/Gate_valve.svg',
                        xref='x', yref='y',
                        x=float(mp), y=float(elev),
                        sizex=sizex, sizey=sizey,
                        xanchor='center', yanchor='middle',
                        sizing='contain', layer='above', opacity=0.95
                    ))

                # Add check valve SVGs
                for mp, elev in valve_positions_check:
                    layout_images.append(dict(
                        source='/assets/Check_Valve.svg',
                        xref='x', yref='y',
                        x=float(mp), y=float(elev),
                        sizex=sizex, sizey=sizey,
                        xanchor='center', yanchor='middle',
                        sizing='contain', layer='above', opacity=0.95
                    ))

                # Station SVG with theme-based fill color
                try:
                    station_svg_path = os.path.join(ASSETS_DIR, 'station.svg')
                    with open(station_svg_path, 'r', encoding='utf-8') as fsvg:
                        station_svg_text = fsvg.read()
                    fill_hex = '#FFFFFF' if dark_mode else '#000000'
                    # Inject a style to force-fill all shapes
                    insert_idx = station_svg_text.find('>')
                    if insert_idx != -1:
                        style_tag = f"<style><![CDATA[* {{ fill: {fill_hex} !important; }}]]></style>"
                        if '<style' not in station_svg_text[:insert_idx+1]:
                            station_svg_text = station_svg_text[:insert_idx +
                                                                1] + style_tag + station_svg_text[insert_idx+1:]
                        else:
                            station_svg_text = station_svg_text[:insert_idx +
                                                                1] + style_tag + station_svg_text[insert_idx+1:]
                    station_svg_b64 = base64.b64encode(
                        station_svg_text.encode('utf-8')).decode('ascii')
                    station_source = f"data:image/svg+xml;base64,{station_svg_b64}"
                except Exception:
                    # Fallback to default asset path if anything goes wrong
                    station_source = '/assets/station.svg'

                # Add station SVGs
                for mp, elev, _label in station_positions:
                    layout_images.append(dict(
                        source=station_source,
                        xref='x', yref='y',
                        x=float(mp), y=float(elev),
                        sizex=station_sizex, sizey=station_sizey,
                        xanchor='center', yanchor='middle',
                        sizing='contain', layer='above', opacity=0.95
                    ))

                # Add divider SVGs for pipe size changes
                for mp, elev, prev_size, curr_size, idx in divider_positions:
                    layout_images.append(dict(
                        source='/assets/divider.svg',
                        xref='x', yref='y',
                        x=float(mp), y=float(elev),
                        sizex=sizex, sizey=sizey,
                        xanchor='center', yanchor='middle',
                        sizing='contain', layer='above', opacity=0.95
                    ))

                if layout_images:
                    fig.update_layout(images=layout_images)

                # Add arrows and annotations for valve identification
                if dark_mode:
                    arrow_color_gate = 'deepskyblue'
                    arrow_color_check = 'orange'
                else:
                    arrow_color_gate = 'royalblue'
                    arrow_color_check = 'darkorange'

                if n_features > 300:
                    arrow_len = 32
                    arrow_width = 1
                elif n_features > 150:
                    arrow_len = 34
                    arrow_width = 1.2
                elif n_features > 60:
                    arrow_len = 36
                    arrow_width = 1.4
                else:
                    arrow_len = 38
                    arrow_width = 1.6

                annos = list(
                    fig.layout.annotations) if fig.layout.annotations else []

                # Add arrows for gate valves
                for mp, elev in valve_positions_gate:
                    annos.append(dict(
                        x=float(mp), y=float(elev),
                        xref='x', yref='y',
                        text='', showarrow=True,
                        ax=0, ay=-arrow_len,
                        arrowhead=3, arrowwidth=arrow_width,
                        arrowcolor=arrow_color_gate
                    ))

                # Add arrows for check valves
                for mp, elev in valve_positions_check:
                    annos.append(dict(
                        x=float(mp), y=float(elev),
                        xref='x', yref='y',
                        text='', showarrow=True,
                        ax=0, ay=-arrow_len,
                        arrowhead=3, arrowwidth=arrow_width,
                        arrowcolor=arrow_color_check
                    ))

                # Add station labels
                label_offset = sizey * 0.8
                for mp, elev, label in station_positions:
                    if not label:
                        continue
                    annos.append(dict(
                        x=float(mp), y=float(elev) + float(label_offset),
                        xref='x', yref='y',
                        text=str(label),
                        showarrow=False,
                        xanchor='center', yanchor='bottom',
                        font=dict(family='Arial Black', size=12)
                    ))

                if annos:
                    fig.update_layout(annotations=annos)

            except Exception:
                pass

        # Add divider annotations for pipe size changes
        if divider_positions:
            # Get existing annotations or create new list
            divider_annos = list(
                fig.layout.annotations) if fig.layout.annotations else []

            for mp, elev, prev_size, curr_size, idx in divider_positions:
                # Left side circle for previous pipe size (fixed pixel offset)
                if not pd.isna(prev_size):
                    divider_annos.append(dict(
                        x=float(mp),
                        y=float(elev),
                        xref='x', yref='y',
                        text=f"⭕{prev_size:.1f}\"",
                        showarrow=False,
                        xanchor='right', yanchor='middle',
                        font=dict(family='Arial', size=10, color='blue'),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='blue',
                        borderwidth=1,
                        ax=-25,  # Fixed pixel offset to the left
                        ay=0     # No vertical offset
                    ))

                # Right side circle for current pipe size (fixed pixel offset)
                if not pd.isna(curr_size):
                    divider_annos.append(dict(
                        x=float(mp),
                        y=float(elev),
                        xref='x', yref='y',
                        text=f"⭕{curr_size:.1f}\"",
                        showarrow=False,
                        xanchor='left', yanchor='middle',
                        font=dict(family='Arial', size=10, color='green'),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='green',
                        borderwidth=1,
                        ax=25,   # Fixed pixel offset to the right
                        ay=0     # No vertical offset
                    ))

            if divider_annos:
                fig.update_layout(annotations=divider_annos)

        # Only show deviations when reduced profile is displayed
        if top_devs and show_reduced:
            kept_idx = np.where(flags != 0)[0]
            # High-contrast colors per theme for top deviations
            if dark_mode:
                deviation_color = '#ffc107'  # Bootstrap warning yellow
                deviation_fill = 'rgba(255, 193, 7, 0.22)'
                deviation_text_color = '#ffffff'  # White text for contrast on dark background
            else:
                deviation_color = '#ffc107'  # Bootstrap warning yellow
                deviation_fill = 'rgba(255, 193, 7, 0.12)'
                deviation_text_color = '#000000'
            for i, (dev, idx) in enumerate(top_devs, 1):
                k = int(np.searchsorted(kept_idx, idx, side='right') - 1)
                if k < 0 or k >= len(kept_idx) - 1:
                    continue
                start = int(kept_idx[k])
                end = int(kept_idx[k + 1])
                seg_slice = slice(start, end + 1)
                xs = df_current.loc[seg_slice, 'Milepost']
                ys = df_current.loc[seg_slice, 'Elevation']
                x0, x1 = float(xs.min()), float(xs.max())
                y0, y1 = float(ys.min()), float(ys.max())
                poly_x = [x0, x1, x1, x0, x0]
                poly_y = [y0, y0, y1, y1, y0]
                fig.add_trace(go.Scatter(x=poly_x, y=poly_y, mode='lines', fill='toself', name=f'Deviation {i}', legendgroup=f'dev{i}',
                                         line=dict(color=deviation_color, width=3), fillcolor=deviation_fill, hoverinfo='skip'))
                fig.add_trace(go.Scatter(x=[(x0 + x1) / 2.0], y=[y1], mode='text', text=[str(i)], textposition='top center',
                                         textfont=dict(color=deviation_text_color, size=16, family='Arial Black'), name=f'Deviation {i} label', legendgroup=f'dev{i}', showlegend=False, hoverinfo='skip'))

        fig.update_layout(margin=dict(l=30, r=30, t=40, b=20), autosize=True, template=template,
                          xaxis_title=f'Distance ({dist_label})', yaxis_title=f'Elevation ({elev_label})',
                          legend=dict(orientation='h', yanchor='top', y=1.02, xanchor='center', x=0.5,
                                      bgcolor=legend_bgcolor, font=dict(color=legend_font_color), bordercolor='rgba(0,0,0,0.1)',
                                      borderwidth=1, itemclick='toggle', itemdoubleclick=False, groupclick='togglegroup'),
                          dragmode='zoom')
        fig.update_layout(uirevision='elev-graph')

        # Update stats based on what's being displayed
        output_points = len(reduced_df) if show_reduced else len(df_current)
        deviation_text = "Top 3 deviations: " + ', '.join(f"{dev:.4f} {elev_label}" for dev, _ in top_devs) if (top_devs and show_reduced) else "Top 3 deviations: —"
        
        stats = dmc.Group([
            dmc.Badge(f"Input Points: {len(df_current)}",
                      color="blue", className="mx-1", variant="dot"),
            dmc.Badge(f"Output Points: {output_points}",
                      color="green", className="mx-1", variant="dot"),
            dmc.Badge(deviation_text,
                      color="yellow", className="mx-1", variant="dot"),
        ], className="mb-2", justify="center")

        if dash.callback_context.triggered and dash.callback_context.triggered[0]['prop_id'].split('.')[0] == 'save-btn':
            dist_header = {'km': 'Kilometers',
                           'mi': 'Miles'}.get(dist_unit, 'Miles')
            elev_header = {'m': 'Meters', 'ft': 'Feet'}.get(elev_unit, 'Feet')
            header_line = f"/* Distance[{dist_header}],Elevation[{elev_header}]\n"
            has_features = bool(
                valve_positions_gate or valve_positions_check or station_positions or divider_positions)
            if not has_features:
                out_df = reduced_df.copy()

                # Treat entire reduced profile as a single TL_ segment
                segments_single = []
                if len(out_df) > 1:
                    segments_single.append((0, len(out_df) - 1, out_df))

                def _single_tl_zip_writer(buf: io.BufferedIOBase):
                    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        # Write the TL_*.csv for the full segment
                        try:
                            if segments_single:
                                seg_df = segments_single[0][2]
                                mp_vals = seg_df['Milepost'].to_numpy(
                                    dtype=float)
                                mp_min = mp_vals[0] if len(
                                    mp_vals) > 0 else 0.0
                                # 5 decimal places for milepost
                                mp_scaled = np.round(mp_vals - mp_min, 5)
                                # Format elevation with 3 decimal places
                                elevation_formatted = np.round(
                                    seg_df['Elevation'].to_numpy(dtype=float), 3)
                                export_df = pd.DataFrame(
                                    {'Distance': mp_scaled, 'Elevation': elevation_formatted})

                                # Filename using selected distance units
                                distance_val = float(
                                    seg_df['Milepost'].iloc[0])

                                def _format_distance_for_name(dist_val: float, unit: str) -> str:
                                    try:
                                        s = f"{dist_val:.3f}"
                                    except Exception:
                                        s = str(dist_val)
                                    return s.replace('.', '')
                                fname = f"TL_{_format_distance_for_name(distance_val, dist_unit)}.csv"

                                s_io = io.StringIO()
                                s_io.write(header_line)
                                export_df.to_csv(
                                    s_io, index=False, header=False)
                                zf.writestr(fname, s_io.getvalue())
                        except Exception:
                            # Silenced non-critical warning
                            pass

                        # Add pipes.csv computed from the original profile for this segment
                        try:
                            pipes_df = create_pipes_dataframe(
                                df_current, out_df, segments_single, dist_unit)
                            if not pipes_df.empty:
                                pipes_io = io.StringIO()
                                pipes_df.to_csv(pipes_io, index=False)
                                zf.writestr('pipes.csv', pipes_io.getvalue())
                            else:
                                empty_pipes_io = io.StringIO()
                                empty_pipes_df = pd.DataFrame(
                                    columns=get_pipes_csv_headers(dist_unit))
                                empty_pipes_df.to_csv(
                                    empty_pipes_io, index=False)
                                zf.writestr(
                                    'pipes.csv', empty_pipes_io.getvalue())
                        except Exception:
                            # Silenced non-critical warning
                            error_io = io.StringIO()
                            error_io.write("Error creating pipes.csv\n")
                            error_io.write(
                                "Error occurred while creating pipes.csv\n")
                            zf.writestr('pipes.csv', error_io.getvalue())

                        # wt.csv intentionally removed

                return dash.no_update, dash.no_update, dcc.send_bytes(_single_tl_zip_writer, filename='Pipeline_Data.zip'), dash.no_update

            valve_orig_idxs = []
            try:
                dists_m = df_current['DistanceMeters'].to_numpy(dtype=float)

                # Collect all markers with their types and positions
                all_markers = []

                # Add selected valve/station rows
                for r in (selected_rows or []):
                    feats = str((r or {}).get('Features', ''))
                    st_name = str((r or {}).get('Station') or '').strip()

                    # Try to get user-edited distance value from DistanceMeter column
                    # This represents the potentially edited value in the grid
                    dm = None
                    if 'DistanceMeter' in r and r['DistanceMeter'] is not None:
                        # Convert user-edited DistanceMeter back to meters based on current unit
                        try:
                            user_dist = float(r['DistanceMeter'])
                            if dist_unit == 'km':
                                dm = user_dist * 1000.0  # Convert km to m
                            elif dist_unit == 'mi':
                                dm = user_dist / 0.000621371  # Convert miles to m
                            else:  # meters
                                dm = user_dist
                        except (TypeError, ValueError):
                            dm = None

                    # Fallback to original DistanceMeters if no edited values found
                    if dm is None:
                        dm = r.get('DistanceMeters')
                        try:
                            dm = float(dm)
                        except (TypeError, ValueError):
                            dm = None

                    if dm is None or dists_m.size == 0:
                        continue
                    is_valve = ("GATE" in feats.upper()) or (
                        "CHECK" in feats.upper())
                    is_station = bool(st_name)
                    if not (is_valve or is_station):
                        continue
                    idx = int(np.nanargmin(np.abs(dists_m - dm)))

                    # Priority: 1=station (highest), 2=divider, 3=valve (lowest)
                    priority = 1 if is_station else 3
                    all_markers.append(
                        (idx, dm, priority, 'station' if is_station else 'valve'))

                # Add divider positions (pipe size changes)
                for mp, elev, prev_size, curr_size, idx in divider_positions:
                    dm = df_current['DistanceMeters'].iloc[idx]
                    # Priority 2 for dividers
                    all_markers.append((idx, dm, 2, 'divider'))

                # Smart consolidation: ensure minimum 1km separation, prioritize by type
                def consolidate_markers(markers, min_distance_m=1000):
                    """Consolidate markers ensuring minimum distance and priority."""
                    if not markers:
                        return []

                    # Sort by position
                    # Sort by distance in meters
                    markers.sort(key=lambda x: x[1])
                    consolidated = []

                    i = 0
                    while i < len(markers):
                        current_marker = markers[i]
                        current_pos = current_marker[1]

                        # Find all markers within min_distance of current marker
                        nearby_markers = [current_marker]
                        j = i + 1
                        while j < len(markers) and markers[j][1] - current_pos < min_distance_m:
                            nearby_markers.append(markers[j])
                            j += 1

                        # Select the highest priority marker from the nearby group
                        # Lower priority number = higher priority
                        best_marker = min(nearby_markers, key=lambda x: x[2])
                        consolidated.append(best_marker)

                        # Skip all processed markers
                        i = j

                    return consolidated

                consolidated_markers = consolidate_markers(all_markers)
                valve_orig_idxs = sorted([marker[0]
                                         for marker in consolidated_markers])

            except Exception:
                valve_orig_idxs = []

            reduced_idx_map = {int(oid): i for i, oid in enumerate(
                reduced_df['OrigRowID'].astype(int).tolist())}
            breakpoint_reduced_idxs = sorted(
                i for oid, i in reduced_idx_map.items() if oid in set(valve_orig_idxs))
            # Exclude first and last points from split breakpoints
            if len(reduced_df) > 0:
                first_idx = 0
                last_idx = len(reduced_df) - 1
                breakpoint_reduced_idxs = [i for i in breakpoint_reduced_idxs if i not in (
                    first_idx, last_idx) and 0 <= i <= last_idx]
            if not breakpoint_reduced_idxs:
                out_df = reduced_df.copy()
                # Use the converted units for export (Milepost and Elevation are already in user's selected units)
                export_df = pd.DataFrame(
                    {'Distance': out_df['Milepost'], 'Elevation': out_df['Elevation']})

                # Create a zip with both elevation data and pipes.csv
                def _no_breakpoints_zip_writer(buf: io.BufferedIOBase):
                    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        # Treat entire reduced profile as a single TL_ segment and write it
                        segments_single = []
                        if len(out_df) > 1:
                            segments_single.append(
                                (0, len(out_df) - 1, out_df))

                        try:
                            if segments_single:
                                seg_df = segments_single[0][2]
                                mp_vals = seg_df['Milepost'].to_numpy(
                                    dtype=float)
                                mp_min = mp_vals[0] if len(
                                    mp_vals) > 0 else 0.0
                                # 5 decimal places for milepost
                                mp_scaled = np.round(mp_vals - mp_min, 5)
                                # Format elevation with 3 decimal places
                                elevation_formatted = np.round(
                                    seg_df['Elevation'].to_numpy(dtype=float), 3)
                                export_df = pd.DataFrame(
                                    {'Distance': mp_scaled, 'Elevation': elevation_formatted})
                                # Filename

                                def _format_distance_for_name(dist_val: float, unit: str) -> str:
                                    try:
                                        s = f"{dist_val:.3f}"
                                    except Exception:
                                        s = str(dist_val)
                                    return s.replace('.', '')
                                distance_val = float(
                                    seg_df['Milepost'].iloc[0])
                                fname = f"TL_{_format_distance_for_name(distance_val, dist_unit)}.csv"

                                s_io = io.StringIO()
                                s_io.write(header_line)
                                export_df.to_csv(
                                    s_io, index=False, header=False)
                                zf.writestr(fname, s_io.getvalue())
                        except Exception:
                            # Silenced non-critical warning
                            pass

                        # Add pipes.csv
                        try:
                            pipes_df = create_pipes_dataframe(
                                df_current, out_df, segments_single, dist_unit)
                            if not pipes_df.empty:
                                pipes_io = io.StringIO()
                                pipes_df.to_csv(pipes_io, index=False)
                                zf.writestr('pipes.csv', pipes_io.getvalue())
                            else:
                                # Add empty pipes.csv with headers if no data
                                empty_pipes_io = io.StringIO()
                                empty_pipes_df = pd.DataFrame(
                                    columns=get_pipes_csv_headers(dist_unit))
                                empty_pipes_df.to_csv(
                                    empty_pipes_io, index=False)
                                zf.writestr(
                                    'pipes.csv', empty_pipes_io.getvalue())
                        except Exception:
                            # Silenced non-critical warning
                            # Add error message in pipes.csv
                            error_io = io.StringIO()
                            error_io.write("Error creating pipes.csv\n")
                            error_io.write(
                                "Error occurred while creating pipes.csv\n")
                            zf.writestr('pipes.csv', error_io.getvalue())

                        # wt.csv intentionally removed

                # Do not refresh the graph or stats or page class on save
                return dash.no_update, dash.no_update, dcc.send_bytes(_no_breakpoints_zip_writer, filename='Pipeline_Data.zip'), dash.no_update

            # Create segments between breakpoints for valve-separated export
            segments = []
            start_idx = 0
            for bp in breakpoint_reduced_idxs:
                if bp <= start_idx:
                    continue
                seg_df = reduced_df.iloc[start_idx:bp+1].copy()
                if len(seg_df) > 1:
                    segments.append((start_idx, bp, seg_df))
                start_idx = bp
            if start_idx < len(reduced_df) - 1:
                tail_df = reduced_df.iloc[start_idx:].copy()
                if len(tail_df) > 1:
                    segments.append((start_idx, len(reduced_df) - 1, tail_df))

            # For filename generation, use user's selected distance unit values
            def _format_distance_for_name(dist_val: float, unit: str) -> str:
                try:
                    s = f"{dist_val:.3f}"
                except Exception:
                    s = str(dist_val)
                return s.replace('.', '')

            def _zip_writer(buf: io.BufferedIOBase):
                with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                    # Create and add pipes.csv
                    try:
                        pipes_df = create_pipes_dataframe(
                            df_current, reduced_df, segments, dist_unit)
                        if not pipes_df.empty:
                            pipes_io = io.StringIO()
                            pipes_df.to_csv(pipes_io, index=False)
                            zf.writestr('pipes.csv', pipes_io.getvalue())
                        else:
                            # Add empty pipes.csv with headers if no data
                            empty_pipes_io = io.StringIO()
                            empty_pipes_df = pd.DataFrame(
                                columns=get_pipes_csv_headers(dist_unit))
                            empty_pipes_df.to_csv(empty_pipes_io, index=False)
                            zf.writestr('pipes.csv', empty_pipes_io.getvalue())
                    except Exception:
                        # Silenced non-critical warning
                        # Add error message in pipes.csv
                        error_io = io.StringIO()
                        error_io.write("Error creating pipes.csv\n")
                        error_io.write(
                            "Error occurred while creating pipes.csv\n")
                        zf.writestr('pipes.csv', error_io.getvalue())

                    # wt.csv intentionally removed

                    # Add elevation profile segments
                    for start_idx_seg, end_idx, seg_df in segments:
                        # Use user's selected distance unit for filename with TL_ prefix
                        distance_val = float(seg_df['Milepost'].iloc[0])
                        fname = f"TL_{_format_distance_for_name(distance_val, dist_unit)}.csv"

                        # Export data in user's selected units (Milepost and Elevation are already converted)
                        mp_vals = seg_df['Milepost'].to_numpy(dtype=float)
                        mp_min = mp_vals[0] if len(mp_vals) > 0 else 0.0
                        # 5 decimal places for milepost
                        mp_scaled = np.round(mp_vals - mp_min, 5)
                        # Format elevation with 3 decimal places
                        elevation_formatted = np.round(
                            seg_df['Elevation'].to_numpy(dtype=float), 3)
                        export_df = pd.DataFrame(
                            {'Distance': mp_scaled, 'Elevation': elevation_formatted})
                        s_io = io.StringIO()
                        s_io.write(header_line)
                        export_df.to_csv(s_io, index=False, header=False)
                        zf.writestr(fname, s_io.getvalue())

            # Do not refresh the graph or stats or page class on save
            return dash.no_update, dash.no_update, dcc.send_bytes(_zip_writer, filename='Reduced_Profiles_By_Valves.zip'), dash.no_update

        return fig, stats, dash.no_update, page_class
    except Exception as e:
        # Use template from theme data or default to mantine_light
        template = theme_data.get('template', 'mantine_light') if theme_data else 'mantine_light'
        page_class = DARK_CLASS if template == 'mantine_dark' else LIGHT_CLASS
        fig = go.Figure()
        fig.update_layout(template=template, margin=dict(
            l=30, r=30, t=40, b=20), xaxis_title='Distance', yaxis_title='Elevation')
        stats = dmc.Group([dmc.Badge(
            "Error", color="red", className="mx-1", variant="dot")], className="mb-2", justify="center")
        return fig, stats, dash.no_update, page_class


# Grid update callback
@dash.callback(
    [Output('results-grid', 'rowData'), Output('results-grid', 'columnDefs'),
     Output('results-grid', 'filterModel'), Output('results-grid', 'columnSize'),
     Output('graph-data-store', 'data')],
    [Input('load-line-btn', 'n_clicks'), Input('unit-store', 'data')],
    [State('line-dropdown', 'value'), State('results-grid', 'rowData'), State('graph-data-store', 'data'),
     State('distance-unit-dd', 'value')]
)
def update_results_grid(load_clicks, unit_data, line_value, current_rows, full_store_rows, dd_dist_unit):
    try:
        ctx = dash.callback_context
        trig = ctx.triggered[0]['prop_id'].split(
            '.')[0] if ctx.triggered else None

        # Determine source dataframe based on trigger
        df = pd.DataFrame()
        if trig == 'load-line-btn':
            if not line_value:
                return [], [], {}, 'sizeToFit', dash.no_update
            # Try in-process cache first
            line_key = str(line_value).strip()
            t0 = time.perf_counter()
            global _profile_cache
            cache_hit = False
            if line_key in _profile_cache:
                cache_hit = True
                df = _profile_cache[line_key].copy()
            else:
                # Use simple OneSource service
                service = get_onesource_service()
                df_api = service.get_elevation_profile(line_key)
                if not df_api.empty:
                    # Map the repository columns to UI expected columns (matching working repository logic)
                    df = pd.DataFrame({
                        'DistanceMeters': pd.to_numeric(df_api.get('CorrectedMilepost'), errors='coerce').round(5),
                        'ElevationMeters': pd.to_numeric(df_api.get('ILIElevationMeters'), errors='coerce'),
                        'Features': df_api.get('Features').astype(object) if 'Features' in df_api.columns else pd.Series([''] * len(df_api)),
                        'Station': df_api.get('Station').astype(object) if 'Station' in df_api.columns else pd.Series([''] * len(df_api)),
                        'ILILatitude': df_api.get('ILILatitude') if 'ILILatitude' in df_api.columns else pd.Series([None] * len(df_api)),
                        'ILILongitude': df_api.get('ILILongitude') if 'ILILongitude' in df_api.columns else pd.Series([None] * len(df_api)),
                        'NominalPipeSizeInches': pd.to_numeric(df_api.get('NominalPipeSizeInches'), errors='coerce') if 'NominalPipeSizeInches' in df_api.columns else pd.Series([None] * len(df_api)),
                        'NominalWallThicknessMillimeters': pd.to_numeric(df_api.get('NominalWallThicknessMillimeters'), errors='coerce') if 'NominalWallThicknessMillimeters' in df_api.columns else pd.Series([None] * len(df_api)),
                    })
                    df = df.dropna(
                        subset=['DistanceMeters', 'ElevationMeters']).reset_index(drop=True)
                    if not df.empty:
                        min_dist = df['DistanceMeters'].min()
                        if min_dist < 0:
                            df['DistanceMeters'] = df['DistanceMeters'] - min_dist
                    df['RowId'] = df.index.astype(int)
                    if 'Features' in df.columns:
                        import re

                        def _clean_features(val):
                            if pd.isna(val):
                                return ''
                            s = str(val).strip()
                            s_up = s.upper()
                            if ('CHECK' in s_up) and ('VALVE' in s_up):
                                return 'CHECK VALVE'
                            if ('GATE' in s_up) and ('VALVE' in s_up):
                                return 'GATE VALVE'
                            tokens = [t.strip() for t in re.split(
                                r'[\,\|;/]+', s) if t and t.strip()]
                            seen = set()
                            out = []
                            for t in tokens:
                                key = t.lower()
                                if key not in seen:
                                    seen.add(key)
                                    out.append(t)
                            return '; '.join(out)
                        df['Features'] = df['Features'].apply(
                            _clean_features).astype(object)
                    if 'Station' in df.columns:
                        df['Station'] = df['Station'].where(
                            ~pd.isna(df['Station']), '').astype(str).str.strip().astype(object)
                    # Save to cache
                    try:
                        _profile_cache[line_key] = df.copy()
                    except Exception:
                        pass
            t1 = time.perf_counter()
            # Debug print removed
        else:
            # No fresh load; use client cache. This makes unit-only changes very fast.
            df = pd.DataFrame(full_store_rows or [])

        if df.empty:
            return [], [], {}, 'sizeToFit', (df.to_dict('records') if trig == 'load-line-btn' else dash.no_update)

        # Minimize payload to client for graph-data-store to reduce JSON time
        needed_cols = ['DistanceMeters', 'ElevationMeters',
                       'Features', 'Station', 'RowId', 'ILILatitude', 'ILILongitude', 'NominalPipeSizeInches', 'NominalWallThicknessMillimeters']
        df_full = df[[c for c in needed_cols if c in df.columns]].copy()
        for c in ['Features', 'Station']:
            if c in df_full.columns:
                df_full[c] = df_full[c].astype(object)

        mask_valve = df.get('Features', pd.Series(index=df.index, dtype=object)).astype(str).str.contains(
            'valve', case=False, na=False) if ('Features' in df.columns) else pd.Series([False]*len(df))
        if 'Station' in df.columns:
            st_series = df['Station']
            if not pd.api.types.is_string_dtype(st_series):
                st_series = st_series.astype(
                    object).where(~st_series.isna(), '')
                st_series = st_series.astype(str)
                st_series = st_series.replace({'nan': ''})
            mask_station = st_series.astype(str).str.strip().ne('')
        else:
            mask_station = pd.Series([False]*len(df))
        mask_valve = mask_valve & (~mask_station)
        mask_grid = (mask_valve | mask_station) if len(
            df) else pd.Series([], dtype=bool)
        df_grid = df.loc[mask_grid].reset_index(
            drop=True) if not df.empty else df.iloc[0:0].copy()

        df_grid = df_grid.copy()
        if 'Features' in df_grid.columns:
            df_grid['Features'] = df_grid['Features'].astype(str).str.strip().astype(object)
        if 'Station' in df_grid.columns:
            df_grid['Station'] = df_grid['Station'].astype(str).str.strip().astype(object)

        if trig == 'load-line-btn':
            dist_unit = (dd_dist_unit or 'mi')
        else:
            dist_unit = ((unit_data or {}).get('distance') or 'mi')

        # Apply unit conversions to Distance column
        if dist_unit == 'km':
            df_grid['DistanceMeter'] = pd.to_numeric(
                df_grid['DistanceMeters'], errors='coerce').div(1000.0).round(5)
            dist_hdr = 'Distance (km)'
        elif dist_unit == 'mi':
            df_grid['DistanceMeter'] = pd.to_numeric(
                df_grid['DistanceMeters'], errors='coerce').mul(0.000621371).round(5)
            dist_hdr = 'Distance (mi)'
        else:
            df_grid['DistanceMeter'] = pd.to_numeric(
                df_grid['DistanceMeters'], errors='coerce').round(5)
            dist_hdr = 'Distance (m)'

        row_data = df_grid.to_dict('records')

        checkbox_col = {
            'headerName': 'Include',
            'headerTooltip': 'Include',
            'checkboxSelection': True,
            'headerCheckboxSelection': True,
            'suppressMenu': True,
            'sortable': False,
            'filter': False,
            'resizable': True,
            'pinned': 'left',
            'lockPosition': True,
            'suppressAutoSize': False,
            'minWidth': 80,
            'width': 80,
            'cellClass': 'include-col',
            'headerClass': 'include-col-header',
            'cellStyle': {
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'center',
                'padding': '0'
            },
            'editable': False
        }
        dm_col = {
            'headerName': dist_hdr,
            'field': 'DistanceMeter',
            'type': 'rightAligned',
            'filter': 'agNumberColumnFilter',
            'valueFormatter': {'function': 'return (value == null || isNaN(value) ? "" : Number(value).toFixed(3));'},
            'minWidth': 120,
            'width': 140,
            'resizable': True,
            'editable': True
        }
        station_col = {
            'headerName': 'Station',
            'field': 'Station',
            'filter': 'agTextColumnFilter',
            'editable': True,
            'minWidth': 120,
            'width': 140,
            'resizable': True
        }
        features_col = {
            'headerName': 'Features',
            'field': 'Features',
            'filter': 'agTextColumnFilter',
            'minWidth': 140,
            'width': 160,
            'resizable': True
        }
        # Column order: Include, Distance, Station, Features
        col_defs = [checkbox_col, dm_col, station_col, features_col]

        filter_model = {}

        # Only update the graph data store on fresh load, not when adding rows
        # This preserves the complete original dataset while allowing grid edits
        full_store_out = df_full.to_dict(
            'records') if trig == 'load-line-btn' else dash.no_update
        return row_data, col_defs, filter_model, 'autoSize', full_store_out
    except Exception:
        return [], [], {}, 'sizeToFit', dash.no_update


# --------------------------------
# Graph Click Handler for ArcGIS Map Integration
# --------------------------------

# Client-side callback to open ArcGIS map on single click
dash.clientside_callback(
    """
    function(click_data, cached_rows) {
        if (!click_data || !cached_rows || cached_rows.length === 0) {
            return window.dash_clientside.no_update;
        }
        
        try {
            // Get clicked coordinates
            const clicked_x = click_data.points[0].x;  // Distance (milepost)
            
            // Find nearest point by distance
            let min_distance = Infinity;
            let nearest_point = null;
            let valid_coords_found = false;
            
            // First pass: try to find the exact nearest point with valid coordinates
            cached_rows.forEach((row) => {
                // Skip if no valid coordinates
                if (!row.ILILatitude || !row.ILILongitude || 
                    isNaN(parseFloat(row.ILILatitude)) || isNaN(parseFloat(row.ILILongitude))) {
                    return;
                }
                
                let point_distance;
                
                // Use Milepost if available, otherwise convert from DistanceMeters
                if (row.Milepost !== undefined && row.Milepost !== null) {
                    point_distance = Math.abs(row.Milepost - clicked_x);
                } else if (row.DistanceMeters !== undefined && row.DistanceMeters !== null) {
                    // Convert DistanceMeters to miles
                    const milepost = row.DistanceMeters * 0.000621371;
                    point_distance = Math.abs(milepost - clicked_x);
                } else {
                    return;  // Skip this point if no distance data
                }
                
                if (point_distance < min_distance) {
                    min_distance = point_distance;
                    nearest_point = row;
                    valid_coords_found = true;
                }
            });
            
            // If no point with valid coordinates found, show a message
            if (!valid_coords_found || !nearest_point) {
                console.log("[elevation:click] No valid coordinates found for any point near the clicked location");
                alert("No location data available for this point. Please try clicking on a different area of the elevation profile.");
                return window.dash_clientside.no_update;
            }
            
            const latitude = parseFloat(nearest_point.ILILatitude);
            const longitude = parseFloat(nearest_point.ILILongitude);
            
            // Validate coordinates (additional validation)
            if (isNaN(latitude) || isNaN(longitude) || 
                Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
                console.log(`[elevation:click] Invalid coordinates: lat=${latitude}, lon=${longitude}`);
                alert("Invalid location data for this point. Please try clicking on a different area of the elevation profile.");
                return window.dash_clientside.no_update;
            }
            
            // Build ArcGIS URL
            const base_url = "https://emap.enbridge.com/DesktopViewer/";
            const app_id = "559a58c2e07e49568ce1427ce49fddb7";
            const arcgis_url = `${base_url}?appid=${app_id}&center=${longitude},${latitude}&level=16`;
            
            console.log(`[elevation:click] Opening ArcGIS map at lat=${latitude}, lon=${longitude}`);
            console.log(`[elevation:click] URL: ${arcgis_url}`);
            
            // Open in new tab
            window.open(arcgis_url, '_blank');
            
        } catch (error) {
            console.error("[elevation:click] Error handling graph click:", error);
            alert("Error processing location data. Please try again.");
        }
        
        return window.dash_clientside.no_update;
    }
    """,
    Output('page-container', 'style', allow_duplicate=True),
    [Input('comparison-graph', 'clickData')],
    [State('graph-data-store', 'data')],
    prevent_initial_call=True
)
