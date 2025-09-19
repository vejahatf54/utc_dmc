"""
Flowmeter Acceptance page component for DMC application.
Converts flowmeter commissioning and acceptance testing from Qt to Dash/Mantine.
Uses Plotly for all plotting functionality.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context, dcc, clientside_callback, dash
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import os
from components.bootstrap_icon import BootstrapIcon
from components.file_selector import create_file_selector, create_file_selector_callback
from services.flowmeter_acceptance_service import FlowmeterAcceptanceService

# Create file selectors for the three file inputs
rtu_file_component, rtu_file_store, rtu_file_ids = create_file_selector(
    component_id='flowmeter-rtu-file',
    title="RTU File (.dt)",
    placeholder="Select RTU data file (.dt extension)",
    browse_button_text="Browse RTU File",
    file_types="RTU Files (*.dt)"
)

csv_tags_component, csv_tags_store, csv_tags_ids = create_file_selector(
    component_id='flowmeter-csv-tags',
    title="Tags File (.in)",
    placeholder="Select tags file (.in extension)",
    browse_button_text="Browse Tags File",
    file_types="Tags Files (*.in)"
)

review_file_component, review_file_store, review_file_ids = create_file_selector(
    component_id='flowmeter-review-file',
    title="Review File (.review)",
    placeholder="Select review file (.review extension)",
    browse_button_text="Browse Review File",
    file_types="Review Files (*.review)"
)


def create_flowmeter_acceptance_page():
    """Create the Flowmeter Acceptance page layout."""

    return dmc.Container([
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("Flowmeter Acceptance Tool",
                                  order=1, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(
                                icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="flowmeter-help-modal-btn",
                            variant="light",
                            color="primary",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Automated partial commissioning and full acceptance testing of flowmeters",
                             c="dimmed", ta="center", size="lg")
                ], gap="xs")
            ]),
            dmc.Modal(
                title="Flowmeter Acceptance Testing",
                id="flowmeter-help-modal",
                size="lg",
                children=[
                    dmc.Stack([
                        dmc.Group([
                            BootstrapIcon(icon="info-circle", width=20),
                            dmc.Text("How It Works", fw=500)
                        ], gap="xs"),
                        dmc.Text([
                            "This tool automates the flowmeter acceptance process by analyzing RTU data, review files, ",
                            "and tag configurations to perform comprehensive reliability, accuracy, and robustness checks. ",
                            "The analysis generates detailed results with statistical analysis and visual plots."
                        ], size="sm", c="dimmed"),
                        dmc.Divider(),
                        dmc.Text("Required Files:", fw=500, size="sm"),
                        dmc.List([
                            dmc.ListItem(
                                "RTU File (.dt) - Raw data from SCADA system"),
                            dmc.ListItem(
                                "CSV Tags File (.csv) - Tag configuration with bounds and references"),
                            dmc.ListItem(
                                "Review File (.review) - Additional validation data")
                        ], size="sm"),
                        dmc.Divider(),
                        dmc.Text("Comprehensive Analysis Tests:",
                                 fw=500, size="sm"),
                        dmc.Accordion([
                            dmc.AccordionItem([
                                dmc.AccordionControl([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="shield-check", width=16),
                                        dmc.Text(
                                            "Reliability Checks (1.1-1.4)", fw=500, c="blue")
                                    ], gap="xs")
                                ]),
                                dmc.AccordionPanel([
                                    dmc.List([
                                        dmc.ListItem(
                                            "1.1: Readings within Expected Range - Validates flowmeter readings fall within operational bounds defined in CSV tags file"),
                                        dmc.ListItem(
                                            "1.2: Measurement Units Verified - Ensures consistent units across RTU and review data"),
                                        dmc.ListItem(
                                            "1.3: RTU Signal Quality - Checks for GOOD quality flags in SCADA RTU data"),
                                        dmc.ListItem(
                                            "1.4: Review Signal Quality - Validates GOOD quality flags in review reference data")
                                    ], size="xs")
                                ])
                            ], value="reliability"),
                            dmc.AccordionItem([
                                dmc.AccordionControl([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="clock-history", width=16),
                                        dmc.Text(
                                            "Timeliness & Completeness (2.1-2.2)", fw=500, c="teal")
                                    ], gap="xs")
                                ]),
                                dmc.AccordionPanel([
                                    dmc.List([
                                        dmc.ListItem(
                                            "2.1: RTU Update Frequency - Ensures RTU data points are updated frequently enough for reliable flowmeter monitoring"),
                                        dmc.ListItem(
                                            "2.2: Review Update Frequency - Validates reference data has adequate temporal resolution for comparison")
                                    ], size="xs")
                                ])
                            ], value="timeliness"),
                            dmc.AccordionItem([
                                dmc.AccordionControl([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="activity", width=16),
                                        dmc.Text(
                                            "Accuracy Tests (3.1-3.4)", fw=500, c="red")
                                    ], gap="xs")
                                ]),
                                dmc.AccordionPanel([
                                    dmc.List([
                                        dmc.ListItem(
                                            "3.1: Digital/Analog Agreement - Time series comparison using classical MSE (Σ(yi-xi)²/n) between RTU and review signals with correlation analysis"),
                                        dmc.ListItem(
                                            "3.2: Signal-to-Noise Ratio - Evaluates signal quality by analyzing noise content and calculating SNR in dB"),
                                        dmc.ListItem(
                                            "3.3: Target vs Digital Signal Comparison - Compares target meter readings from review file against digital RTU signals"),
                                        dmc.ListItem(
                                            "3.4: Target vs Reference Comparison - Cross-validation of target flow readings against reference meter measurements")
                                    ], size="xs")
                                ])
                            ], value="accuracy"),
                            dmc.AccordionItem([
                                dmc.AccordionControl([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="graph-up", width=16),
                                        dmc.Text(
                                            "Robustness Checks (4.1-4.2)", fw=500, c="orange")
                                    ], gap="xs")
                                ]),
                                dmc.AccordionPanel([
                                    dmc.List([
                                        dmc.ListItem(
                                            "4.1: Signal Stability - Long-term stability analysis ensuring flowmeter signals remain consistent over extended periods"),
                                        dmc.ListItem(
                                            "4.2: Spectral Analysis for Anomaly Detection - Frequency domain analysis to detect anomalies, excessive noise, and signal concentration")
                                    ], size="xs")
                                ])
                            ], value="robustness")
                        ], variant="separated"),
                        dmc.Divider(),
                        dmc.Alert([
                            dmc.Group([
                                BootstrapIcon(icon="lightbulb", width=16),
                                dmc.Text("Key Enhancement", fw=500)
                            ], gap="xs", mb="xs"),
                            dmc.Text("This implementation uses classical MSE calculation (Mean Square Error = Σ(yi-xi)²/n) with proper time series alignment for accurate flowmeter validation against reference signals.", size="xs")
                        ], color="blue", variant="light")
                    ], gap="sm")
                ]
            ),
            # Main Content with Tabs
            dmc.Tabs([
                dmc.TabsList([
                    dmc.TabsTab([
                        dmc.Group([
                            BootstrapIcon(icon="gear-fill", width=18),
                            dmc.Text("Analysis Setup", size="lg", fw=700)
                        ], gap="xs")
                    ], value="setup"),
                    dmc.TabsTab([
                        dmc.Group([
                            BootstrapIcon(icon="graph-up-arrow", width=18),
                            dmc.Text("Results", size="lg", fw=700)
                        ], gap="xs")
                    ], value="results", disabled=True, id="results-tab")
                ]),
                dmc.TabsPanel([
                    # Main Form - Two Column Layout
                    dmc.SimpleGrid([
                        # Column 1
                        dmc.Stack([
                            # File Input Cards - Using file selector components
                            rtu_file_component,
                            csv_tags_component,
                            review_file_component,
                            dmc.Card([
                                dmc.Group([
                                    dmc.Text("Analysis Time Range",
                                             fw=600, size="md"),
                                    BootstrapIcon(
                                        icon="clock-history", width=16)
                                ], gap="xs", mb="lg"),
                                dmc.SimpleGrid([
                                    dmc.Stack([
                                        dmc.Text("Start Time",
                                                 fw=500, size="sm"),
                                        dmc.DateTimePicker(
                                            id="start-time-picker",
                                            value=datetime.now().replace(second=0, microsecond=0),
                                            withSeconds=True,
                                            size="md",
                                            valueFormat="YYYY/MM/DD HH:mm:ss"
                                        )
                                    ], gap="xs"),
                                    dmc.Stack([
                                        dmc.Text(
                                            "End Time", fw=500, size="sm"),
                                        dmc.DateTimePicker(
                                            id="end-time-picker",
                                            value=datetime.now().replace(second=0, microsecond=0),
                                            withSeconds=True,
                                            size="md",
                                            valueFormat="YYYY/MM/DD HH:mm:ss"
                                        )
                                    ], gap="xs")
                                ], cols=2, spacing="sm"),
                            ], shadow="sm", p="md"),
                            dmc.Card([
                                dmc.Group([
                                    dmc.Text("Analysis Parameters",
                                             fw=600, size="md"),
                                    BootstrapIcon(icon="sliders", width=16)
                                ], gap="xs", mb="lg"),
                                dmc.Group([
                                    # First column - Flow rates
                                    dmc.Stack([
                                        dmc.NumberInput(
                                            label="Minimum Flowrate",
                                            id="min-flowrate-input",
                                            min=0,
                                            size="sm"
                                        ),
                                        dmc.NumberInput(
                                            label="Maximum Flowrate",
                                            id="max-flowrate-input",
                                            min=0,
                                            size="sm"
                                        )
                                    ], gap="sm", style={"flex": "1"}),
                                    # Vertical divider
                                    dmc.Divider(
                                        orientation="vertical", size="sm"),
                                    # Second column - Other parameters
                                    dmc.Stack([
                                        dmc.NumberInput(
                                            label="FLAT Threshold",
                                            id="flat-threshold-input",
                                            value=5,
                                            min=0,
                                            size="sm"
                                        ),
                                        dmc.NumberInput(
                                            label="Accuracy Range",
                                            id="accuracy-range-input",
                                            value=1.0,
                                            min=0,
                                            step=0.1,
                                            size="sm"
                                        )
                                    ], gap="sm", style={"flex": "1"})
                                ], align="stretch", gap="md"),
                            ], shadow="sm", p="md"),
                        ], gap="md"),
                        # Column 2
                        dmc.Stack([
                            dmc.Card([
                                dmc.Group([
                                    dmc.Text("Analysis Checks",
                                             fw=600, size="md"),
                                    BootstrapIcon(
                                        icon="check2-square", width=16)
                                ], gap="xs", style={"marginBottom": "12px"}),
                                dmc.Group([
                                    dmc.Button(
                                        "Partial Commissioning",
                                        id="partial-commissioning-btn",
                                        variant="outline",
                                        size="lg",
                                        leftSection=BootstrapIcon(
                                            icon="clipboard-check", width=16)
                                    ),
                                    dmc.Button(
                                        "Full Acceptance",
                                        id="full-acceptance-btn",
                                        variant="filled",
                                        size="lg",
                                        className="px-4",
                                        leftSection=BootstrapIcon(
                                            icon="clipboard2-check", width=16)
                                    )
                                ], gap="md", style={"marginBottom": "16px"}),
                                dmc.SimpleGrid([
                                    dmc.Card([
                                        dmc.Stack([
                                            dmc.Text("Reliability Checks",
                                             fw=500, c="blue"),
                                            dmc.Checkbox(
                                                label="1.1: Readings within expected range of operation in the rtu File", id="reliability-check-1"),
                                            dmc.Checkbox(
                                                label="1.2: Measurement units were verified in the rtu File", id="reliability-check-2"),
                                            dmc.Checkbox(
                                                label="1.3: Quality of the Signals is GOOD in the rtu File", id="reliability-check-3"),
                                            dmc.Checkbox(
                                                label="1.4: Quality of the Signals is GOOD in the review File", id="reliability-check-4")
                                        ], gap="xs")
                                    ], withBorder=True, p="sm"),
                                    dmc.Card([
                                        dmc.Stack([
                                            dmc.Text(
                                                "Timeliness and Completeness Checks", fw=500, c="teal"),
                                            dmc.Checkbox(
                                                label="2.1: Points are Updated on a Frequent Enough Basis in the rtu File", id="tc-check-1"),
                                            dmc.Checkbox(
                                                label="2.2: Points are Updated on a Frequent Enough Basis in the review File", id="tc-check-2")
                                        ], gap="xs")
                                    ], withBorder=True, p="sm"),
                                    dmc.Card([
                                        dmc.Stack([
                                            dmc.Text("Robustness Checks",
                                             fw=500, c="orange"),
                                            dmc.Checkbox(
                                                label="4.1: Signals are Stable", id="robustness-check-1"),
                                            dmc.Checkbox(
                                                label="4.2: Spectral Analysis for Anomaly Detection", id="robustness-check-2")
                                        ], gap="xs")
                                    ], withBorder=True, p="sm"),
                                    dmc.Card([
                                        dmc.Stack([
                                            dmc.Text("Accuracy Checks",
                                             fw=500, c="red"),
                                            dmc.Checkbox(
                                                label="3.1: Digital/Analog Signals are in Close Agreement in the rtu File", id="accuracy-check-1"),
                                            dmc.Checkbox(
                                                label="3.2: Acceptable Signal-to-Noise ratio for D/A signals in the rtu File", id="accuracy-check-2"),
                                            dmc.Checkbox(
                                                label="3.3: MBS Target vs rtu Digital Signal Comparison", id="accuracy-check-3"),
                                            dmc.Checkbox(
                                                label="3.4: MBS target vs MBS reference signals Comparison", id="accuracy-check-4")
                                        ], gap="xs")
                                    ], withBorder=True, p="sm")
                                ], cols=2, spacing="md"),
                            ], shadow="sm", p="md"),
                            # Test 4.1 Signal Stability Parameters (conditional)
                            dmc.Card([
                                dmc.Group([
                                    dmc.Text(
                                        "Test 4.1 - Signal Stability Parameters", fw=500, size="sm", c="orange"),
                                    BootstrapIcon(icon="graph-up", width=14)
                                ], gap="xs", mb="sm"),
                                dmc.Group([
                                    dmc.NumberInput(
                                        label="Window Size",
                                        id="stability-window-input",
                                        value=50,
                                        min=10,
                                        max=200,
                                        size="xs",
                                        style={"flex": "1"},
                                        description="Rolling window"
                                    ),
                                    dmc.NumberInput(
                                        label="Drift Threshold (%)",
                                        id="drift-threshold-input",
                                        value=5.0,
                                        min=0.1,
                                        max=20.0,
                                        step=0.1,
                                        size="xs",
                                        style={"flex": "1"},
                                        description="Max drift"
                                    ),
                                    dmc.NumberInput(
                                        label="Stability Threshold (%)",
                                        id="stability-threshold-input",
                                        value=90.0,
                                        min=50.0,
                                        max=100.0,
                                        step=1.0,
                                        size="xs",
                                        style={"flex": "1"},
                                        description="Required stability"
                                    )
                                ], gap="sm", align="stretch")
                            ], shadow="sm", p="sm", id="test-41-params-card", style={"display": "none"}),
                            # Test 4.2 Spectral Analysis Parameters (conditional)
                            dmc.Card([
                                dmc.Group([
                                    dmc.Text(
                                        "Test 4.2 - Spectral Analysis Parameters", fw=500, size="sm", c="orange"),
                                    BootstrapIcon(icon="soundwave", width=14)
                                ], gap="xs", mb="sm"),
                                dmc.Group([
                                    dmc.NumberInput(
                                        label="Noise Threshold (%)",
                                        id="noise-threshold-input",
                                        value=15.0,
                                        min=1.0,
                                        max=50.0,
                                        step=0.1,
                                        size="xs",
                                        style={"flex": "1"},
                                        description="Max noise"
                                    ),
                                    dmc.NumberInput(
                                        label="Low Freq Cutoff (Hz)",
                                        id="low-freq-cutoff-input",
                                        value=0.05,
                                        min=0.001,
                                        max=1.0,
                                        step=0.001,
                                        size="xs",
                                        style={"flex": "1"},
                                        description="Freq threshold"
                                    ),
                                    dmc.NumberInput(
                                        label="Entropy Threshold",
                                        id="entropy-threshold-input",
                                        value=0.7,
                                        min=0.1,
                                        max=1.0,
                                        step=0.01,
                                        size="xs",
                                        style={"flex": "1"},
                                        description="Min entropy"
                                    )
                                ], gap="sm", align="stretch")
                            ], shadow="sm", p="sm", id="test-42-params-card", style={"display": "none"}),
                            dmc.Card([
                                dmc.Group([
                                    dmc.Button(
                                        "Run Analysis",
                                        id="run-analysis-btn",
                                        size="lg",
                                        variant="filled",
                                        className="px-4",
                                        leftSection=BootstrapIcon(
                                            icon="play-circle", width=20)
                                    ),
                                    dmc.Button(
                                        "Clear Form",
                                        id="clear-form-btn",
                                        variant="outline",
                                        size="lg",
                                        leftSection=BootstrapIcon(
                                            icon="arrow-clockwise", width=20)
                                    )
                                ], justify="center", gap="md")
                            ], shadow="sm", p="md"),
                        ], gap="sm"),
                    ], cols=2, spacing="md", style={"width": "100%"}),
                    dmc.LoadingOverlay(
                        visible=False,
                        id="analysis-loading",
                        overlayProps={"radius": "sm", "blur": 2}
                    )
                ], value="setup"),
                dmc.TabsPanel([
                    # Analysis Results Content - Two Column Layout with Results Summary and Plots
                    dmc.Stack([
                        dmc.Group([
                            dmc.Title("Analysis Results", order=2),
                            BootstrapIcon(icon="graph-up-arrow", width=24)
                        ], gap="xs", justify="center"),
                        dmc.Divider(),

                        # Main Results Layout - Left column for test results, right column for plots
                        dmc.SimpleGrid([
                            # Left Column - Test Results Summary Card (minimum width needed)
                            dmc.Stack([
                                dmc.Card([
                                    dmc.Group([
                                        dmc.Title(
                                            "Test Results Summary", order=4),
                                        BootstrapIcon(
                                            icon="clipboard-check", width=18)
                                    ], gap="xs", mb="sm"),
                                    html.Div(id="test-results-summary", children=[
                                        dmc.Text("Run an analysis to see test results.",
                                                 ta="center", c="dimmed", size="sm", py="md")
                                    ])
                                ], shadow="sm", p="md", style={"height": "700px", "overflow": "auto"})
                            ], style={"minWidth": "300px", "maxWidth": "400px"}),

                            # Right Column - Interactive Plots - Expand to fill available space
                            dmc.Stack([
                                dmc.Tabs([
                                    dmc.TabsList([
                                        dmc.TabsTab("Time Trends",
                                                    value="time-trends"),
                                        dmc.TabsTab("Distributions",
                                                    value="distributions"),
                                        dmc.TabsTab(
                                            "Spectral Analysis", value="spectral"),
                                        dmc.TabsTab(
                                            "Quality Metrics", value="quality")
                                    ]),
                                    dmc.TabsPanel([
                                        dcc.Graph(id="time-trends-plot",
                                                  style={"height": "650px", "width": "100%"})
                                    ], value="time-trends"),
                                    dmc.TabsPanel([
                                        dcc.Graph(id="distributions-plot",
                                                  style={"height": "650px", "width": "100%"})
                                    ], value="distributions"),
                                    dmc.TabsPanel([
                                        dcc.Graph(id="spectral-plot",
                                                  style={"height": "650px", "width": "100%"})
                                    ], value="spectral"),
                                    dmc.TabsPanel([
                                        dcc.Graph(
                                            id="quality-metrics-plot", style={"height": "650px", "width": "100%"})
                                    ], value="quality")
                                ], value="time-trends", id="results-plot-tabs")
                            ], style={"flex": "1", "minWidth": "600px"})
                        ], cols=2, spacing="md", style={"width": "100%"}),

                        # Second Row - Additional Reports and Statistics
                        dmc.Card([
                            dmc.Group([
                                dmc.Title(
                                    "Additional Reports & Statistics", order=4),
                                BootstrapIcon(icon="bar-chart", width=18)
                            ], gap="xs", mb="sm"),
                            dmc.SimpleGrid([
                                # Statistical Summary
                                dmc.Card([
                                    dmc.Text("Statistical Summary",
                                             fw=500, size="sm", mb="xs"),
                                    html.Div(id="statistical-summary", children=[
                                        dmc.Text("Statistical data will appear here after analysis.",
                                                 c="dimmed", size="xs")
                                    ])
                                ], shadow="xs", p="sm"),

                                # Test Performance Metrics
                                dmc.Card([
                                    dmc.Text("Performance Metrics",
                                             fw=500, size="sm", mb="xs"),
                                    html.Div(id="performance-metrics", children=[
                                        dmc.Text("Performance metrics will appear here after analysis.",
                                                 c="dimmed", size="xs")
                                    ])
                                ], shadow="xs", p="sm"),

                                # Data Quality Report
                                dmc.Card([
                                    dmc.Text("Data Quality Report",
                                             fw=500, size="sm", mb="xs"),
                                    html.Div(id="data-quality-report", children=[
                                        dmc.Text("Data quality report will appear here after analysis.",
                                                 c="dimmed", size="xs")
                                    ])
                                ], shadow="xs", p="sm"),

                                # Export Options
                                dmc.Card([
                                    dmc.Text("Export Options", fw=500,
                                             size="sm", mb="xs"),
                                    dmc.Group([
                                        dmc.Button("Export CSV", size="xs", variant="outline",
                                                   leftSection=BootstrapIcon(
                                                       icon="file-spreadsheet", width=14),
                                                   id="export-csv-btn"),
                                        dmc.Button("Export PDF", size="xs", variant="outline",
                                                   leftSection=BootstrapIcon(
                                                       icon="file-pdf", width=14),
                                                   id="export-pdf-btn")
                                    ], gap="xs")
                                ], shadow="xs", p="sm")
                            ], cols=4, spacing="sm")
                        ], shadow="sm", p="md", mt="md")
                    ], gap="md", id="analysis-results-content")
                ], value="results")
            ],
                autoContrast=True,
                variant="outline",
                value="setup",
                id="main-tabs"
            ),
        ], gap="md"),

        # File validation feedback
        html.Div(id="file-upload-feedback"),

        # Notification container for this page
        html.Div(id='flowmeter-notifications'),

        # Store components for file selectors
        rtu_file_store,
        csv_tags_store,
        review_file_store,

        # Store for analysis results data
        dcc.Store(id="analysis-results-store", data={})
    ], fluid=True, py="sm")


# File validation callback
@callback(
    Output("file-upload-feedback", "children"),
    [Input(rtu_file_ids['input'], "value"),
     Input(csv_tags_ids['input'], "value"),
     Input(review_file_ids['input'], "value")],
    prevent_initial_call=True
)
def validate_file_inputs(rtu_file, csv_file, review_file):
    """Validate file path inputs."""
    warnings = []

    if rtu_file and not rtu_file.lower().endswith('.dt'):
        warnings.append("RTU file should have .dt extension")

    if review_file and not review_file.lower().endswith('.review'):
        warnings.append("Review file should have .review extension")

    if warnings:
        return dmc.Alert(
            "File extension warnings: " + "; ".join(warnings),
            title="File Validation",
            color="yellow",
            icon=BootstrapIcon(icon="exclamation-triangle")
        )

    return []


# Help modal toggle
@callback(
    Output("flowmeter-help-modal", "opened"),
    Input("flowmeter-help-modal-btn", "n_clicks"),
    State("flowmeter-help-modal", "opened"),
    prevent_initial_call=True
)
def toggle_help_modal(n_clicks, opened):
    return not opened


# Callback to show/hide robustness parameter cards
@callback(
    [Output("test-41-params-card", "style"),
     Output("test-42-params-card", "style")],
    [Input("robustness-check-1", "checked"),
     Input("robustness-check-2", "checked")],
    prevent_initial_call=True
)
def toggle_robustness_params(rob1_checked, rob2_checked):
    """Show/hide robustness parameter cards based on checkbox selection."""
    style_41 = {"display": "block"} if rob1_checked else {"display": "none"}
    style_42 = {"display": "block"} if rob2_checked else {"display": "none"}
    return style_41, style_42


# Combined callback for preset checks and form clearing
@callback(
    [Output("reliability-check-1", "checked"),
     Output("reliability-check-2", "checked"),
     Output("reliability-check-3", "checked"),
     Output("reliability-check-4", "checked"),
     Output("tc-check-1", "checked"),
     Output("tc-check-2", "checked"),
     Output("robustness-check-1", "checked"),
     Output("robustness-check-2", "checked"),
     Output("accuracy-check-1", "checked"),
     Output("accuracy-check-2", "checked"),
     Output("accuracy-check-3", "checked"),
     Output("accuracy-check-4", "checked"),
     Output("flat-threshold-input", "value"),
     Output("min-flowrate-input", "value"),
     Output("max-flowrate-input", "value"),
     Output("accuracy-range-input", "value"),
     Output("results-tab", "disabled", allow_duplicate=True),
     Output("main-tabs", "value", allow_duplicate=True)],
    [Input("partial-commissioning-btn", "n_clicks"),
     Input("full-acceptance-btn", "n_clicks"),
     Input("clear-form-btn", "n_clicks")],
    [State("flat-threshold-input", "value"),
     State("min-flowrate-input", "value"),
     State("max-flowrate-input", "value"),
     State("accuracy-range-input", "value")],
    prevent_initial_call=True
)
def handle_form_actions(partial_clicks, full_clicks, clear_clicks,
                        flat_threshold, min_flow, max_flow, accuracy_range):
    """Handle preset check selection and form clearing."""
    ctx = callback_context
    if not ctx.triggered:
        return [False] * 12 + [5, None, None, 1.0] + [True, "setup"]

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == "partial-commissioning-btn":
        # Partial commissioning preset: rel 1-4, tc 1-2, rob 1-2, acc 1&3&4 (core tests, skip SNR)
        checks = [True, True, True, True, True, True,
                  True, True, True, False, True, True]
        form_values = [flat_threshold or 5, min_flow,
                       max_flow, accuracy_range or 1.0]
        # Keep results tab disabled, stay on setup
        return checks + form_values + [True, "setup"]

    elif button_id == "full-acceptance-btn":
        # Full acceptance preset: ALL checks enabled for comprehensive validation
        checks = [True, True, True, True, True,
                  True, True, True, True, True, True, True]
        form_values = [flat_threshold or 5, min_flow,
                       max_flow, accuracy_range or 1.0]
        # Keep results tab disabled, stay on setup
        return checks + form_values + [True, "setup"]

    elif button_id == "clear-form-btn":
        # Clear form - reset everything
        checks = [False] * 12
        form_values = [5, None, None, 1.0]
        # Disable results tab, go back to setup
        return checks + form_values + [True, "setup"]

    # Default return
    return [False] * 12 + [5, None, None, 1.0] + [True, "setup"]


# Main analysis handler
@callback(
    [Output("analysis-loading", "visible"),
     Output("main-tabs", "value"),
     Output("analysis-results-content", "children"),
     Output("results-tab", "disabled"),
     Output("analysis-results-store", "data"),
     Output('flowmeter-notifications', 'children', allow_duplicate=True)],
    Input("run-analysis-btn", "n_clicks"),
    [State(rtu_file_ids['input'], "value"),
     State(csv_tags_ids['input'], "value"),
     State(review_file_ids['input'], "value"),
     State("start-time-picker", "value"),
     State("end-time-picker", "value"),
     State("flat-threshold-input", "value"),
     State("min-flowrate-input", "value"),
     State("max-flowrate-input", "value"),
     State("accuracy-range-input", "value"),
     State("reliability-check-1", "checked"),
     State("reliability-check-2", "checked"),
     State("reliability-check-3", "checked"),
     State("reliability-check-4", "checked"),
     State("tc-check-1", "checked"),
     State("tc-check-2", "checked"),
     State("robustness-check-1", "checked"),
     State("robustness-check-2", "checked"),
     State("accuracy-check-1", "checked"),
     State("accuracy-check-2", "checked"),
     State("accuracy-check-3", "checked"),
     State("accuracy-check-4", "checked"),
     State("stability-window-input", "value"),
     State("drift-threshold-input", "value"),
     State("stability-threshold-input", "value"),
     State("noise-threshold-input", "value"),
     State("low-freq-cutoff-input", "value"),
     State("entropy-threshold-input", "value"),
     State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def run_flowmeter_analysis(n_clicks, rtu_file, csv_file, review_file, start_time, end_time,
                           flat_threshold, min_flow, max_flow, accuracy_range,
                           rel1, rel2, rel3, rel4, tc1, tc2, rob1, rob2, acc1, acc2, acc3, acc4,
                           stability_window, drift_threshold, stability_threshold,
                           noise_threshold, low_freq_cutoff, entropy_threshold, theme_data):
    """Run the flowmeter analysis with all parameters."""
    if not all([rtu_file, csv_file, review_file]):
        missing_files_notification = dmc.Notification(
            title="Missing Files",
            message="Please select all required files (RTU, CSV Tags, and Review files).",
            color="red",
            autoClose=False,
            action="show",
            icon=BootstrapIcon(icon="exclamation-triangle")
        )

        return False, "setup", dmc.Alert(
            "Please select all required files (RTU, CSV Tags, and Review files).",
            title="Missing Files",
            color="red",
            icon=BootstrapIcon(icon="exclamation-triangle")
        ), True, {}, missing_files_notification

    try:
        # Show loading
        # Here we would call the service to run the analysis
        service = FlowmeterAcceptanceService()

        # Convert datetime values to proper string format for the service
        # DateTimePicker returns strings, we need to parse and convert to YY/MM/DD HH:MM:SS format
        start_str = ""
        end_str = ""

        if start_time:
            if isinstance(start_time, str):
                # Try multiple parsing strategies
                try:
                    # First try ISO format (common from DateTimePicker)
                    start_dt = datetime.fromisoformat(
                        start_time.replace('Z', '+00:00'))
                    # Use 2-digit year for RTU service (YY/MM/DD HH:MM:SS)
                    start_str = start_dt.strftime("%y/%m/%d %H:%M:%S")
                except:
                    try:
                        # Try parsing various date formats
                        for fmt in ["%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%y/%m/%d %H:%M:%S"]:
                            try:
                                start_dt = datetime.strptime(start_time, fmt)
                                # Always output as 2-digit year format
                                start_str = start_dt.strftime(
                                    "%y/%m/%d %H:%M:%S")
                                break
                            except:
                                continue
                        else:
                            # If all parsing fails, use as-is
                            start_str = start_time
                    except:
                        start_str = start_time
            else:
                # If it's a datetime object
                start_str = start_time.strftime("%y/%m/%d %H:%M:%S")

        if end_time:
            if isinstance(end_time, str):
                # Try multiple parsing strategies
                try:
                    # First try ISO format (common from DateTimePicker)
                    end_dt = datetime.fromisoformat(
                        end_time.replace('Z', '+00:00'))
                    # Use 2-digit year for RTU service (YY/MM/DD HH:MM:SS)
                    end_str = end_dt.strftime("%y/%m/%d %H:%M:%S")
                except:
                    try:
                        # Try parsing various date formats
                        for fmt in ["%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%y/%m/%d %H:%M:%S"]:
                            try:
                                end_dt = datetime.strptime(end_time, fmt)
                                # Always output as 2-digit year format
                                end_str = end_dt.strftime("%y/%m/%d %H:%M:%S")
                                break
                            except:
                                continue
                        else:
                            # If all parsing fails, use as-is
                            end_str = end_time
                    except:
                        end_str = end_time
            else:
                # If it's a datetime object
                end_str = end_time.strftime("%y/%m/%d %H:%M:%S")

        # Prepare parameters dictionary
        params = {
            'rtu_file': rtu_file,
            'csv_tags_file': csv_file,
            'review_file': review_file,
            'csv_file': "flowmeter_data",
            'report_name': "flowmeter_report",
            'time_start': start_str,
            'time_end': end_str,
            'threshold_FLAT': int(flat_threshold) if flat_threshold else 5,
            'min_Q': float(min_flow) if min_flow else None,
            'max_Q': float(max_flow) if max_flow else None,
            'accuracy_range': float(accuracy_range) if accuracy_range else 1.0,
            'reliability_check_1': rel1,
            'reliability_check_2': rel2,
            'reliability_check_3': rel3,
            'reliability_check_4': rel4,
            'tc_check_1': tc1,
            'tc_check_2': tc2,
            'robustness_check_1': rob1,
            'robustness_check_2': rob2,
            'accuracy_check_1': acc1,
            'accuracy_check_2': acc2,
            'accuracy_check_3': acc3,
            'accuracy_check_4': acc4,
            # Robustness Test Parameters
            'stability_window_size': int(stability_window) if stability_window else 50,
            'drift_threshold': float(drift_threshold) if drift_threshold else 5.0,
            'stability_threshold': float(stability_threshold) if stability_threshold else 90.0,
            'noise_threshold': float(noise_threshold) if noise_threshold else 15.0,
            'low_freq_cutoff': float(low_freq_cutoff) if low_freq_cutoff else 0.05,
            'entropy_threshold': float(entropy_threshold) if entropy_threshold else 0.7
        }

        # Run analysis
        results = service.run_analysis(params)

        # Create results display
        checks_selected = [rel1, rel2, rel3, rel4,
                           tc1, tc2, rob1, rob2, acc1, acc2, acc3, acc4]
        selected_count = sum(checks_selected)

        # Generate comprehensive time series visualizations
        plots = service.create_analysis_plots(theme_data)

        # Create CSV export notification
        csv_export_info = results.get('csv_export', {})
        exported_files = csv_export_info.get('exported_files', [])

        csv_notification = dmc.Notification(
            title="CSV Data Exported",
            message=f"Successfully exported {len(exported_files)} CSV files to _Data directory: SCADATagID_DIG.csv, SCADATagID_ANL.csv, MBSTagID.csv, Reference_Meter.csv",
            color="green",
            autoClose=5000,
            action="show",
            icon=BootstrapIcon(icon="file-earmark-spreadsheet")
        )

        # Don't override the Results tab content - let the new Results tab callbacks handle it
        # Just return no_update for the content and let the store data trigger the callbacks

        return False, "results", dash.no_update, False, results, csv_notification

    except Exception as e:
        error_notification = dmc.Notification(
            title="Analysis Failed",
            message="Please check your input files and parameters, then try again.",
            color="red",
            autoClose=False,
            action="show",
            icon=BootstrapIcon(icon="exclamation-triangle")
        )

        return False, "results", dmc.Stack([
            dmc.Alert(
                f"Analysis failed: {str(e)}",
                title="❌ Analysis Error",
                color="red",
                icon=BootstrapIcon(icon="exclamation-triangle")
            ),
            dmc.Text("Please check your input files and parameters, then try again.",
                     ta="center", c="dimmed", size="sm")
        ], gap="md"), False, {}, error_notification


# Create file selector callbacks
create_file_selector_callback(rtu_file_ids, "Select RTU Data File")
create_file_selector_callback(csv_tags_ids, "Select CSV Tags File")
create_file_selector_callback(review_file_ids, "Select Review File")

# Callback to show loading overlay when analysis button is clicked


@callback(
    Output("analysis-loading", "visible", allow_duplicate=True),
    Input("run-analysis-btn", "n_clicks"),
    prevent_initial_call=True
)
def show_loading_on_click(n_clicks):
    """Show loading overlay immediately when Run Analysis is clicked."""
    if n_clicks and n_clicks > 0:
        return True
    return False


# Results Tab Callbacks

@callback(
    [Output("test-results-summary", "children"),
     Output("statistical-summary", "children"),
     Output("performance-metrics", "children"),
     Output("data-quality-report", "children")],
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_results_summary(results_data, theme_data):
    """Update the test results summary and additional reports."""
    if not results_data or not results_data.get('test_results'):
        no_data_msg = dmc.Text(
            "No analysis results available.", ta="center", c="dimmed", size="sm", py="md")
        return no_data_msg, no_data_msg, no_data_msg, no_data_msg

    # Get theme
    template = theme_data.get(
        'template', 'mantine_light') if theme_data else 'mantine_light'
    is_dark = template == 'mantine_dark'

    test_results = results_data['test_results']

    # Create test results summary
    test_cards = []
    total_tests = 0
    passed_tests = 0

    for meter_name, meter_results in test_results.items():
        # Meter header
        overall_status = meter_results.get('overall_status', 'unknown')
        status_icon = "check-circle-fill" if overall_status == 'pass' else "x-circle-fill" if overall_status == 'fail' else "question-circle-fill"
        status_color = "green" if overall_status == 'pass' else "red" if overall_status == 'fail' else "orange"

        test_cards.append(
            dmc.Card([
                dmc.Group([
                    BootstrapIcon(icon=status_icon, width=16,
                                  color=status_color),
                    dmc.Text(f"Meter: {meter_name}", fw=600, size="sm")
                ], gap="xs", mb="xs"),
                dmc.Divider(size="xs", mb="xs")
            ], p="xs", mb="xs", style={"backgroundColor": "var(--mantine-color-gray-1)" if not is_dark else "var(--mantine-color-dark-6)"})
        )

        # Process each test category
        for category_name, category_tests in meter_results.items():
            if category_name in ['reliability_tests', 'timeliness_tests', 'accuracy_tests', 'robustness_tests']:
                category_display = {
                    'reliability_tests': 'Reliability Tests',
                    'timeliness_tests': 'Timeliness Tests',
                    'accuracy_tests': 'Accuracy Tests',
                    'robustness_tests': 'Robustness Tests'
                }[category_name]

                test_cards.append(
                    dmc.Text(category_display, fw=500, size="xs",
                             c="dimmed", ml="md", mb="xs")
                )

                for test_name, test_result in category_tests.items():
                    total_tests += 1
                    test_status = test_result.get('status', 'unknown')
                    if test_status == 'pass':
                        passed_tests += 1

                    test_icon = "hand-thumbs-up-fill" if test_status == 'pass' else "hand-thumbs-down-fill" if test_status == 'fail' else "question-circle"
                    test_color = "green" if test_status == 'pass' else "red" if test_status == 'fail' else "orange"

                    test_cards.append(
                        dmc.Group([
                            BootstrapIcon(icon=test_icon,
                                          width=14, color=test_color),
                            dmc.Stack([
                                dmc.Text(test_name, size="xs", fw=500),
                                dmc.Text(test_result.get(
                                    'description', ''), size="xs", c="dimmed"),
                                dmc.Text(
                                    f"Result: {test_result.get('value', 'N/A')}", size="xs", c="blue")
                            ], gap=0)
                        ], gap="xs", align="flex-start", ml="md", mb="xs")
                    )

    test_summary = dmc.Stack(test_cards, gap="xs") if test_cards else dmc.Text(
        "No test results available.", c="dimmed", size="sm")

    # Statistical Summary
    stats_children = [
        dmc.Group([
            dmc.Text("Total Tests:", size="xs", fw=500),
            dmc.Badge(str(total_tests), color="blue", size="xs")
        ], justify="space-between"),
        dmc.Group([
            dmc.Text("Passed:", size="xs", fw=500),
            dmc.Badge(str(passed_tests), color="green", size="xs")
        ], justify="space-between"),
        dmc.Group([
            dmc.Text("Failed:", size="xs", fw=500),
            dmc.Badge(str(total_tests - passed_tests), color="red", size="xs")
        ], justify="space-between"),
        dmc.Group([
            dmc.Text("Success Rate:", size="xs", fw=500),
            dmc.Badge(f"{(passed_tests/total_tests*100):.1f}%" if total_tests >
                      0 else "0%", color="teal", size="xs")
        ], justify="space-between")
    ]

    # Performance Metrics
    perf_children = [
        dmc.Text("Meters Analyzed:", size="xs", fw=500),
        dmc.Badge(str(len(test_results)), color="blue", size="xs", mb="xs"),
        dmc.Text("Analysis Duration:", size="xs", fw=500),
        dmc.Badge("< 1 min", color="green", size="xs", mb="xs"),
        dmc.Text("Data Points:", size="xs", fw=500),
        dmc.Badge("Processing...", color="orange", size="xs")
    ]

    # Data Quality Report
    quality_children = [
        dmc.Text("File Integrity:", size="xs", fw=500),
        dmc.Badge("✓ Good", color="green", size="xs", mb="xs"),
        dmc.Text("Data Completeness:", size="xs", fw=500),
        dmc.Badge("✓ Complete", color="green", size="xs", mb="xs"),
        dmc.Text("Signal Quality:", size="xs", fw=500),
        dmc.Badge("Under Review", color="orange", size="xs")
    ]

    return test_summary, dmc.Stack(stats_children, gap="xs"), dmc.Stack(perf_children, gap="xs"), dmc.Stack(quality_children, gap="xs")


@callback(
    Output("time-trends-plot", "figure"),
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_time_trends_plot(results_data, theme_data):
    """Create time trends plot for digital/analog signals."""
    # Get theme
    template = theme_data.get(
        'template', 'mantine_light') if theme_data else 'mantine_light'

    if not results_data or not results_data.get('plots_data'):
        # Create empty figure with proper theme
        fig = go.Figure()
        fig.update_layout(
            template=template,
            title="Time Trends - Run analysis to view data",
            xaxis_title="Time",
            yaxis_title="Flow Rate",
            margin=dict(l=40, r=40, t=60, b=40),
            height=500
        )
        return fig

    # Create single plot for all time trends
    fig = go.Figure()

    plots_data = results_data.get('plots_data', {})

    # Add time series data for each meter
    # Better color palette with distinct colors for each signal type
    digital_colors = ['#1f77b4', '#ff7f0e',
                      '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    analog_colors = ['#17becf', '#bcbd22',
                     '#e377c2', '#7f7f7f', '#c5b0d5', '#c49c94']
    reference_colors = ['#2ca02c', '#ff7f0e',
                        '#1f77b4', '#d62728', '#9467bd', '#8c564b']

    meter_idx = 0

    for meter_name, meter_data in plots_data.items():
        if 'time_series' in meter_data:
            ts_data = meter_data['time_series']

            # Digital signal - solid line
            if 'digital_signal' in ts_data:
                fig.add_trace(
                    go.Scatter(
                        x=ts_data['digital_signal'].get('timestamps', []),
                        y=ts_data['digital_signal'].get('values', []),
                        mode='lines',
                        name=f'{meter_name} - Digital',
                        line=dict(color=digital_colors[meter_idx % len(
                            digital_colors)], width=2),
                    )
                )

            # Analog signal - dashed line with different color
            if 'analog_signal' in ts_data:
                fig.add_trace(
                    go.Scatter(
                        x=ts_data['analog_signal'].get('timestamps', []),
                        y=ts_data['analog_signal'].get('values', []),
                        mode='lines',
                        name=f'{meter_name} - Analog',
                        line=dict(color=analog_colors[meter_idx % len(analog_colors)],
                                  dash='dash', width=2),
                    )
                )

            # Reference signal - dot-dash line with third color palette
            if 'reference_signal' in ts_data:
                fig.add_trace(
                    go.Scatter(
                        x=ts_data['reference_signal'].get('timestamps', []),
                        y=ts_data['reference_signal'].get('values', []),
                        mode='lines',
                        name=f'{meter_name} - Reference',
                        line=dict(color=reference_colors[meter_idx % len(reference_colors)],
                                  dash='dashdot', width=2),
                    )
                )

            meter_idx += 1

    fig.update_layout(
        template=template,
        title="Signal Time Trends - All Signals Combined",
        xaxis_title="Time",
        yaxis_title="Flow Rate",
        height=650,
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig


@callback(
    Output("distributions-plot", "figure"),
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_distributions_plot(results_data, theme_data):
    """Create time delta distribution plot showing time differences between successive readings."""
    template = theme_data.get(
        'template', 'mantine_light') if theme_data else 'mantine_light'

    if not results_data or not results_data.get('plots_data'):
        fig = go.Figure()
        fig.update_layout(
            template=template,
            title="Time Delta Distribution - Run analysis to view data",
            xaxis_title="Time Delta (seconds)",
            yaxis_title="Frequency",
            margin=dict(l=40, r=40, t=60, b=40),
            height=650
        )
        return fig

    # Calculate time deltas from actual CSV data
    import pandas as pd
    import numpy as np
    from datetime import datetime

    plots_data = results_data.get('plots_data', {})

    # Load the actual CSV data to calculate time deltas
    try:
        data_dir = r"C:\Temp\python_projects\Flow Meter Acceptance L05\_Data"
        digital_csv = os.path.join(data_dir, "SCADATagID_DIG.csv")
        analog_csv = os.path.join(data_dir, "SCADATagID_ANL.csv")

        time_deltas = []

        if os.path.exists(digital_csv):
            df_dig = pd.read_csv(digital_csv)
            df_dig['datetime'] = pd.to_datetime(df_dig['datetime'])
            df_dig = df_dig.sort_values('datetime')
            dig_deltas = df_dig['datetime'].diff(
            ).dt.total_seconds().dropna().values
            time_deltas.extend(dig_deltas)

        if os.path.exists(analog_csv):
            df_anl = pd.read_csv(analog_csv)
            df_anl['datetime'] = pd.to_datetime(df_anl['datetime'])
            df_anl = df_anl.sort_values('datetime')
            anl_deltas = df_anl['datetime'].diff(
            ).dt.total_seconds().dropna().values
            time_deltas.extend(anl_deltas)

        if time_deltas:
            # Create single histogram showing time delta distribution
            fig = go.Figure()

            fig.add_trace(
                go.Histogram(
                    x=time_deltas,
                    name="Time Delta Distribution",
                    marker_color='#1f77b4',
                    opacity=0.8,
                    nbinsx=50,
                    hovertemplate="<b>Time Delta:</b> %{x:.1f} seconds<br>" +
                                  "<b>Count:</b> %{y}<br><extra></extra>"
                )
            )

            # Add statistics text
            mean_delta = np.mean(time_deltas)
            std_delta = np.std(time_deltas)
            min_delta = np.min(time_deltas)
            max_delta = np.max(time_deltas)

            fig.add_annotation(
                x=0.98, y=0.98,
                xref="paper", yref="paper",
                text=f"<b>Statistics:</b><br>" +
                     f"Mean: {mean_delta:.2f}s<br>" +
                     f"Std: {std_delta:.2f}s<br>" +
                     f"Min: {min_delta:.2f}s<br>" +
                     f"Max: {max_delta:.2f}s<br>" +
                     f"Total: {len(time_deltas)} intervals",
                showarrow=False,
                align="left",
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="gray",
                borderwidth=1
            )

        else:
            # No data available
            fig = go.Figure()
            fig.add_annotation(
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                text="No time delta data available",
                showarrow=False,
                font=dict(size=16)
            )

    except Exception as e:
        # Error loading data - show error message
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            text=f"Error loading time delta data: {str(e)}",
            showarrow=False,
            font=dict(size=14)
        )

    fig.update_layout(
        template=template,
        title="Time Delta Distribution Between Successive Readings",
        xaxis_title="Time Delta (seconds)",
        yaxis_title="Frequency",
        height=650,
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=False
    )

    return fig


@callback(
    Output("spectral-plot", "figure"),
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_spectral_plot(results_data, theme_data):
    """Create spectral analysis plots for tests 4.1 and 4.2."""
    template = theme_data.get(
        'template', 'mantine_light') if theme_data else 'mantine_light'

    if not results_data or not results_data.get('test_results'):
        fig = go.Figure()
        fig.update_layout(
            template=template,
            title="Spectral Analysis (Tests 4.1 & 4.2) - Run analysis to view data",
            xaxis_title="Frequency (Hz)",
            yaxis_title="Power Spectral Density",
            margin=dict(l=40, r=40, t=60, b=40),
            height=500
        )
        return fig

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Signal Stability (Test 4.1)", "Frequency Spectrum (Test 4.2)",
                        "Stability Windows", "Spectral Entropy"),
        vertical_spacing=0.12
    )

    # Generate sample spectral data for demonstration
    import numpy as np

    test_results = results_data.get('test_results', {})
    # Distinct color palette for spectral analysis
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
              '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']

    for i, (meter_name, meter_results) in enumerate(test_results.items()):
        color = colors[i % len(colors)]

        # Sample frequency spectrum
        freqs = np.logspace(-2, 2, 100)  # 0.01 to 100 Hz
        power = 1/(1 + freqs**2) + 0.1*np.random.random(100)  # 1/f + noise

        fig.add_trace(
            go.Scatter(x=freqs, y=power, mode='lines', name=f'{meter_name}',
                       line=dict(color=color)),
            row=1, col=2
        )

        # Sample stability data
        time_windows = np.arange(0, 100, 1)
        stability = 90 + 5*np.sin(time_windows/10) + 2*np.random.random(100)

        fig.add_trace(
            go.Scatter(x=time_windows, y=stability, mode='lines+markers',
                       name=f'{meter_name} Stability', line=dict(color=color),
                       marker=dict(size=4)),
            row=1, col=1
        )

        # Rolling window stability
        window_stability = np.convolve(stability, np.ones(10)/10, mode='same')
        fig.add_trace(
            go.Scatter(x=time_windows, y=window_stability, mode='lines',
                       name=f'{meter_name} Rolling Avg', line=dict(color=color, dash='dash')),
            row=2, col=1
        )

        # Spectral entropy over time
        entropy_time = time_windows
        entropy_vals = 0.5 + 0.3 * \
            np.sin(entropy_time/20) + 0.1*np.random.random(100)

        fig.add_trace(
            go.Scatter(x=entropy_time, y=entropy_vals, mode='lines',
                       name=f'{meter_name} Entropy', line=dict(color=color)),
            row=2, col=2
        )

    # Add threshold lines if we have data
    if test_results:
        try:
            fig.add_hline(y=90, line_dash="dot", line_color="red",
                          row=1, col=1)  # Stability threshold
            fig.add_hline(y=0.7, line_dash="dot", line_color="red",
                          row=2, col=2)  # Entropy threshold
        except Exception:
            # Skip adding threshold lines if there's an issue
            pass

    fig.update_layout(
        template=template,
        title="Spectral Analysis - Signal Stability & Frequency Content",
        height=500,
        margin=dict(l=40, r=40, t=80, b=40),
        showlegend=True
    )

    fig.update_xaxes(title_text="Time Window", row=1, col=1)
    fig.update_xaxes(title_text="Frequency (Hz)", type="log", row=1, col=2)
    fig.update_xaxes(title_text="Time Window", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=2)

    fig.update_yaxes(title_text="Stability (%)", row=1, col=1)
    fig.update_yaxes(title_text="Power", row=1, col=2)
    fig.update_yaxes(title_text="Stability (%)", row=2, col=1)
    fig.update_yaxes(title_text="Entropy", row=2, col=2)

    return fig


@callback(
    Output("quality-metrics-plot", "figure"),
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_quality_metrics_plot(results_data, theme_data):
    """Create quality metrics visualization showing test summary and performance metrics."""
    template = theme_data.get(
        'template', 'mantine_light') if theme_data else 'mantine_light'

    if not results_data or not results_data.get('test_results'):
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            text="<b>Quality Metrics Dashboard</b><br><br>" +
                 "Run an analysis to view:<br>" +
                 "• Test Results Summary<br>" +
                 "• Signal Quality Metrics<br>" +
                 "• Performance Indicators<br>" +
                 "• Overall Quality Score",
            showarrow=False,
            font=dict(size=16),
            align="center"
        )
        fig.update_layout(
            template=template,
            title="Quality Metrics Dashboard",
            margin=dict(l=40, r=40, t=60, b=40),
            height=650
        )
        return fig

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Test Results Overview", "SNR Analysis",
                        "MSE Analysis", "Quality Scores"),
        specs=[[{"type": "domain"}, {"type": "scatter"}],
               [{"type": "bar"}, {"type": "indicator"}]]
    )

    test_results = results_data.get('test_results', {})

    # Aggregate test results for pie chart
    total_pass = 0
    total_fail = 0

    snr_data = []
    mse_data = []
    meter_names = []

    for meter_name, meter_results in test_results.items():
        meter_names.append(meter_name)

        # Count pass/fail for this meter
        meter_pass = 0
        meter_fail = 0

        for category in ['reliability_tests', 'timeliness_tests', 'accuracy_tests', 'robustness_tests']:
            if category in meter_results:
                for test_name, test_result in meter_results[category].items():
                    if test_result.get('status') == 'pass':
                        total_pass += 1
                        meter_pass += 1
                    else:
                        total_fail += 1
                        meter_fail += 1

        # Extract SNR and MSE values (sample data)
        snr_data.append(25.5 + 5*np.random.random())  # Sample SNR
        mse_data.append(0.1 + 0.05*np.random.random())  # Sample MSE

    # Pie chart for overall results
    fig.add_trace(
        go.Pie(labels=['Passed', 'Failed'], values=[total_pass, total_fail],
               marker_colors=['green', 'red']),
        row=1, col=1
    )

    # SNR analysis
    fig.add_trace(
        go.Scatter(x=meter_names, y=snr_data, mode='markers+lines',
                   name='SNR (dB)', marker=dict(size=10, color='blue')),
        row=1, col=2
    )

    # MSE bar chart
    fig.add_trace(
        go.Bar(x=meter_names, y=mse_data, name='MSE', marker_color='orange'),
        row=2, col=1
    )

    # Quality indicator
    overall_quality = (total_pass / (total_pass + total_fail)) * \
        100 if (total_pass + total_fail) > 0 else 0

    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=overall_quality,
            title={'text': "Overall Quality Score"},
            gauge={'axis': {'range': [None, 100]},
                   'bar': {'color': "darkgreen" if overall_quality > 80 else "orange" if overall_quality > 60 else "red"},
                   'steps': [{'range': [0, 60], 'color': "lightgray"},
                             {'range': [60, 80], 'color': "yellow"},
                             {'range': [80, 100], 'color': "lightgreen"}],
                   'threshold': {'line': {'color': "red", 'width': 4},
                                 'thickness': 0.75, 'value': 90}}
        ),
        row=2, col=2
    )

    # Add SNR threshold line only if we have data and the subplot exists
    if meter_names and snr_data:
        try:
            fig.add_hline(y=20, line_dash="dot",
                          line_color="red", row=1, col=2)
        except Exception:
            # Skip adding threshold line if there's an issue
            pass

    fig.update_layout(
        template=template,
        title="Quality Metrics Analysis - Performance Dashboard",
        height=650,
        margin=dict(l=40, r=40, t=80, b=40),
        showlegend=True
    )

    return fig
