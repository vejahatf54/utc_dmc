"""
Flowmeter Acceptance page component for DMC application.
Converts flowmeter commissioning and acceptance testing from Qt to Dash/Mantine.
Uses Plotly for all plotting functionality.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context, dcc, clientside_callback
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px
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
                            dmc.Card([
                                dmc.Group([
                                    dmc.Text("Robustness Parameters",
                                             fw=600, size="md"),
                                    BootstrapIcon(icon="cpu", width=16)
                                ], gap="xs", mb="lg"),
                                dmc.Group([
                                    # First column - Signal Stability (Test 4.1)
                                    dmc.Stack([
                                        dmc.Text(
                                            "Test 4.1 - Signal Stability", size="sm", fw=500, c="dimmed"),
                                        dmc.NumberInput(
                                            label="Window Size",
                                            id="stability-window-input",
                                            value=50,
                                            min=10,
                                            max=200,
                                            size="sm",
                                            description="Rolling window size for stability analysis"
                                        ),
                                        dmc.NumberInput(
                                            label="Drift Threshold (%)",
                                            id="drift-threshold-input",
                                            value=5.0,
                                            min=0.1,
                                            max=20.0,
                                            step=0.1,
                                            size="sm",
                                            description="Max allowed drift from mean"
                                        ),
                                        dmc.NumberInput(
                                            label="Stability Threshold (%)",
                                            id="stability-threshold-input",
                                            value=90.0,
                                            min=50.0,
                                            max=100.0,
                                            step=1.0,
                                            size="sm",
                                            description="Required percentage of stable readings"
                                        )
                                    ], gap="xs", style={"flex": "1"}),
                                    # Vertical divider
                                    dmc.Divider(
                                        orientation="vertical", size="sm"),
                                    # Second column - Spectral Analysis (Test 4.2)
                                    dmc.Stack([
                                        dmc.Text(
                                            "Test 4.2 - Spectral Analysis", size="sm", fw=500, c="dimmed"),
                                        dmc.NumberInput(
                                            label="Noise Threshold (%)",
                                            id="noise-threshold-input",
                                            value=15.0,
                                            min=1.0,
                                            max=50.0,
                                            step=0.1,
                                            size="sm",
                                            description="Max allowed high-frequency noise"
                                        ),
                                        dmc.NumberInput(
                                            label="Low Freq Cutoff (Hz)",
                                            id="low-freq-cutoff-input",
                                            value=0.05,
                                            min=0.001,
                                            max=1.0,
                                            step=0.001,
                                            size="sm",
                                            description="Frequency threshold for stability"
                                        ),
                                        dmc.NumberInput(
                                            label="Entropy Threshold",
                                            id="entropy-threshold-input",
                                            value=0.7,
                                            min=0.1,
                                            max=1.0,
                                            step=0.01,
                                            size="sm",
                                            description="Min spectral entropy for good signal"
                                        )
                                    ], gap="xs", style={"flex": "1"})
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
                            ], shadow="sm", p="xl"),
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
                        ], gap="md"),
                    ], cols=2, spacing="lg", style={"width": "100%"}),
                    dmc.LoadingOverlay(
                        visible=False,
                        id="analysis-loading",
                        overlayProps={"radius": "sm", "blur": 2}
                    )
                ], value="setup"),
                dmc.TabsPanel([
                    # Analysis Results Content
                    dmc.Stack([
                        dmc.Group([
                            dmc.Title("Analysis Results", order=2),
                            BootstrapIcon(icon="graph-up-arrow", width=24)
                        ], gap="xs", justify="center"),
                        dmc.Divider(),
                        html.Div(id="analysis-results-content", children=[
                            dmc.Text("Run an analysis to see results here.",
                                     ta="center", c="dimmed", size="lg", py="xl")
                        ])
                    ], gap="md")
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
        review_file_store
    ], fluid=True, py="md")


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
        ), True, missing_files_notification

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

        # Create comprehensive results display - ONLY SHOW RESULTS, NO FILE GENERATION
        results_content = dmc.Stack([
            # Success Alert
            dmc.Alert(
                "Analysis completed successfully!",
                title="✅ Analysis Complete",
                color="green",
                icon=BootstrapIcon(icon="check-circle"),
                mb="lg"
            ),

            # Time Series Analysis Section
            dmc.Card([
                dmc.Group([
                    dmc.Title("Time Series Analysis Results", order=3),
                    BootstrapIcon(icon="activity", width=20)
                ], gap="xs", mb="md"),
                dmc.Tabs([
                    dmc.TabsList([
                        dmc.TabsTab("Test Overview",
                                    value="test-overview"),
                        dmc.TabsTab("Category Breakdown",
                                    value="category-breakdown"),
                        dmc.TabsTab("Success Rate", value="success-rate")
                    ], variant="pills"),
                    dmc.TabsPanel([
                        dcc.Graph(figure=plots.get(
                            'test_overview', {}), style={'height': '500px'})
                    ], value="test-overview"),
                    dmc.TabsPanel([
                        dcc.Graph(figure=plots.get('category_breakdown', {}),
                                  style={'height': '500px'})
                    ], value="category-breakdown"),
                    dmc.TabsPanel([
                        dcc.Graph(figure=plots.get('success_rate', {}),
                                  style={'height': '500px'})
                    ], value="success-rate")
                ], value="test-overview")
            ], shadow="sm", p="lg", mb="lg"),

            # Analysis Summary Section
            dmc.Card([
                dmc.Group([
                    dmc.Title("Analysis Summary", order=3),
                    BootstrapIcon(icon="clipboard-data", width=20)
                ], gap="xs", mb="md"),
                dmc.SimpleGrid([
                    dmc.Card([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(
                                    icon="file-earmark-text", width=16),
                                dmc.Text("Files Processed", fw=500, c="blue")
                            ], gap="xs"),
                            dmc.Text(
                                f"📄 RTU: {rtu_file.split('/')[-1] if '/' in rtu_file else rtu_file.split('\\')[-1]}", size="sm"),
                            dmc.Text(
                                f"📊 Tags: {csv_file.split('/')[-1] if '/' in csv_file else csv_file.split('\\')[-1]}", size="sm"),
                            dmc.Text(
                                f"📋 Review: {review_file.split('/')[-1] if '/' in review_file else review_file.split('\\')[-1]}", size="sm")
                        ], gap="xs")
                    ], withBorder=True, p="md"),
                    dmc.Card([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="clock", width=16),
                                dmc.Text("Time Range", fw=500, c="teal")
                            ], gap="xs"),
                            dmc.Text(f"⏰ Start: {start_str}", size="sm"),
                            dmc.Text(f"⏰ End: {end_str}", size="sm"),
                            dmc.Text(
                                f"🎯 FLAT Threshold: {flat_threshold}", size="sm")
                        ], gap="xs")
                    ], withBorder=True, p="md"),
                    dmc.Card([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="gear", width=16),
                                dmc.Text("Analysis Parameters",
                                         fw=500, c="orange")
                            ], gap="xs"),
                            dmc.Text(
                                f"🌊 Flow Range: {min_flow or 'Auto'} - {max_flow or 'Auto'}", size="sm"),
                            dmc.Text(
                                f"🎯 Accuracy Range: ±{accuracy_range}", size="sm"),
                            dmc.Text(
                                f"💪 Stability Window: {stability_window or 50}", size="sm"),
                            dmc.Text(
                                f"💪 Drift Threshold: {drift_threshold or 5.0}%", size="sm"),
                            dmc.Text(
                                f"💪 Noise Threshold: {noise_threshold or 15.0}%", size="sm"),
                            dmc.Text(
                                f"📈 Total Checks: {selected_count}/12", size="sm")
                        ], gap="xs")
                    ], withBorder=True, p="md"),
                    dmc.Card([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="check2-square", width=16),
                                dmc.Text("Checks Performed",
                                         fw=500, c="violet")
                            ], gap="xs"),
                            dmc.Text(
                                f"🔧 Reliability: {sum([rel1, rel2, rel3, rel4])}/4", size="sm"),
                            dmc.Text(
                                f"⏱️ Timeliness & Completeness: {sum([tc1, tc2])}/2", size="sm"),
                            dmc.Text(
                                f"💪 Robustness: {sum([rob1, rob2])}/2", size="sm"),
                            dmc.Text(
                                f"🎯 Accuracy: {sum([acc1, acc2, acc3, acc4])}/4", size="sm")
                        ], gap="xs")
                    ], withBorder=True, p="md")
                ], cols=2, spacing="md")
            ], shadow="sm", p="lg", mb="lg")
        ], gap="lg")

        return False, "results", results_content, False, csv_notification

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
        ], gap="md"), False, error_notification


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
