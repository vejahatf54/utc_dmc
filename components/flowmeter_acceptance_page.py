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
import pandas as pd
import os
import io
import base64
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
                title="Flowmeter Acceptance Testing - Complete Guide",
                id="flowmeter-help-modal",
                size="xl",
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
                        ]),
                        dmc.Divider(),
                        dmc.Text("Test Categories & Pass Criteria:",
                                 fw=500, size="sm"),
                        dmc.Accordion([
                            dmc.AccordionItem([
                                dmc.AccordionControl([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="shield-check", width=16),
                                        dmc.Text(
                                            "Reliability Tests (1.1-1.4)", fw=500, c="blue")
                                    ], gap="xs")
                                ]),
                                dmc.AccordionPanel([
                                    dmc.Stack([
                                        dmc.Text("Test 1.1: Readings within Expected Range", fw=500, size="sm"),
                                        dmc.Text("Pass Criteria: 0 readings outside min/max range", c="red", size="xs"),
                                        dmc.Text("Validates all flowmeter readings fall within operational bounds (min_range to max_range)", size="xs"),
                                        
                                        dmc.Text("Test 1.2: Measurement Units Verified", fw=500, size="sm", mt="xs"),
                                        dmc.Text("Pass Criteria: Unit conversion successful (always passes)", c="green", size="xs"),
                                        dmc.Text("Checks if values are in m³/h using 80%-120% tolerance of min_Q/max_Q. Converts from barrels/h if needed (÷6.2898)", size="xs"),
                                        
                                        dmc.Text("Test 1.3: Signal Quality (RTU)", fw=500, size="sm", mt="xs"),
                                        dmc.Text("Pass Criteria: 0 bad quality readings", c="red", size="xs"),
                                        dmc.Text("All quality flags must be 'GOOD' in RTU data", size="xs"),
                                        
                                        dmc.Text("Test 1.4: Signal Quality (Review)", fw=500, size="sm", mt="xs"),
                                        dmc.Text("Pass Criteria: All status values = 1 (GOOD)", c="red", size="xs"),
                                        dmc.Text("All ST column values must equal 1 in Review file", size="xs")
                                    ], gap="xs")
                                ])
                            ], value="reliability"),
                            dmc.AccordionItem([
                                dmc.AccordionControl([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="clock-history", width=16),
                                        dmc.Text(
                                            "Timeliness Tests (2.1-2.2)", fw=500, c="teal")
                                    ], gap="xs")
                                ]),
                                dmc.AccordionPanel([
                                    dmc.Stack([
                                        dmc.Text("Test 2.1: Time Differences", fw=500, size="sm"),
                                        dmc.Group([
                                            dmc.Text("Pass Criteria:", fw=500, size="xs"),
                                            dmc.Badge("≥95% within 6s", color="red", size="xs"),
                                            dmc.Badge("Mean ≤5s", color="red", size="xs"),
                                            dmc.Badge("95th percentile ≤6s", color="red", size="xs")
                                        ], gap="xs"),
                                        dmc.Text("Ensures RTU reporting frequency around 5 seconds with ±20% tolerance", size="xs"),
                                        
                                        dmc.Text("Test 2.2: FLAT Attribute Check", fw=500, size="sm", mt="xs"),
                                        dmc.Text("Pass Criteria: FLAT ≤ threshold (excluding shutdown periods where VAL ≤ 1)", c="red", size="xs"),
                                        dmc.Text("Validates temporal consistency in review data", size="xs")
                                    ], gap="xs")
                                ])
                            ], value="timeliness"),
                            dmc.AccordionItem([
                                dmc.AccordionControl([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="activity", width=16),
                                        dmc.Text(
                                            "Accuracy Tests (3.1-3.5)", fw=500, c="red")
                                    ], gap="xs")
                                ]),
                                dmc.AccordionPanel([
                                    dmc.Stack([
                                        dmc.Text("Test 3.1: Mean Squared Error", fw=500, size="sm"),
                                        dmc.Text("Pass Criteria: RMSE within accuracy_range% of nominal flow", c="red", size="xs"),
                                        dmc.Text("Classical MSE (Σ(yi-xi)²/n) between digital and analog signals", size="xs"),
                                        
                                        dmc.Text("Test 3.2: Signal-to-Noise Ratio", fw=500, size="sm", mt="xs"),
                                        dmc.Text("Pass Criteria: SNR > 30 dB", c="red", size="xs"),
                                        dmc.Text("Power-based SNR: 10×log₁₀(signal_power/noise_power) with detrending", size="xs"),
                                        
                                        dmc.Text("Test 3.3: Target vs Digital", fw=500, size="sm", mt="xs"),
                                        dmc.Text("Pass Criteria: No explicit threshold (informational)", c="blue", size="xs"),
                                        dmc.Text("Time-aligned comparison of target meter vs digital RTU signal", size="xs"),
                                        
                                        dmc.Text("Test 3.4: Target vs Reference", fw=500, size="sm", mt="xs"),
                                        dmc.Text("Pass Criteria: No explicit threshold (informational)", c="blue", size="xs"),
                                        dmc.Text("Time-aligned comparison of target meter vs reference meter", size="xs"),
                                        
                                        dmc.Text("Test 3.5: SNR Comparison", fw=500, size="sm", mt="xs"),
                                        dmc.Text("Pass Criteria: Both digital AND analog SNR ≥ 95% of reference SNR", c="red", size="xs"),
                                        dmc.Text("Requires Ref_SCADATagID column in tags file", size="xs", c="orange")
                                    ], gap="xs")
                                ])
                            ], value="accuracy"),
                            dmc.AccordionItem([
                                dmc.AccordionControl([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="graph-up", width=16),
                                        dmc.Text(
                                            "Robustness Test (4.1)", fw=500, c="orange")
                                    ], gap="xs")
                                ]),
                                dmc.AccordionPanel([
                                    dmc.Stack([
                                        dmc.Text("Test 4.1: Signal Stability", fw=500, size="sm"),
                                        dmc.Text("Pass Criteria: Stability ≥ stability_threshold% (default: 90%)", c="red", size="xs"),
                                        dmc.Text("Algorithm: Combines ±3σ outlier detection with rolling drift analysis", fw=500, size="xs"),
                                        dmc.List([
                                            dmc.ListItem("±3σ bounds: mean ± 3×std_deviation"),
                                            dmc.ListItem("Drift check: rolling mean within drift_threshold% of overall mean"),
                                            dmc.ListItem("Reading is stable if within ±3σ AND no local drift")
                                        ]),
                                        dmc.Group([
                                            dmc.Text("Parameters:", fw=500, size="xs"),
                                            dmc.Badge("Window: 50", color="gray", size="xs"),
                                            dmc.Badge("Drift: 5%", color="gray", size="xs"),
                                            dmc.Badge("Threshold: 90%", color="gray", size="xs")
                                        ], gap="xs")
                                    ], gap="xs")
                                ])
                            ], value="robustness"),
                            dmc.AccordionItem([
                                dmc.AccordionControl([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="graph-down", width=16),
                                        dmc.Text(
                                            "Graph Interpretation Guide", fw=500, c="violet")
                                    ], gap="xs")
                                ]),
                                dmc.AccordionPanel([
                                    dmc.Stack([
                                        dmc.Text("Test Results Overview (Bar Chart)", fw=500, size="sm"),
                                        dmc.Text("Green bars = Pass, Red bars = Fail. Quick visual of overall meter status.", size="xs"),
                                        
                                        dmc.Text("Category Breakdown (Stacked Bar)", fw=500, size="sm", mt="xs"),
                                        dmc.Text("Shows pass/fail counts per test category. Identifies problematic test areas.", size="xs"),
                                        
                                        dmc.Text("Time Series Plots", fw=500, size="sm", mt="xs"),
                                        dmc.List([
                                            dmc.ListItem("Stable signals: Consistent values, minimal drift"),
                                            dmc.ListItem("Outlier spikes: Sharp deviations indicate measurement issues"),
                                            dmc.ListItem("Drift patterns: Gradual changes suggest sensor degradation"),
                                            dmc.ListItem("High noise: Frequent variations indicate poor signal quality")
                                        ]),
                                        
                                        dmc.Text("Troubleshooting Failed Tests:", fw=500, size="sm", mt="xs"),
                                        dmc.List([
                                            dmc.ListItem("High outliers (Test 4.1): Check sensor calibration"),
                                            dmc.ListItem("High drift (Test 4.1): Look for systematic bias or degradation"),
                                            dmc.ListItem("Poor SNR (Test 3.2): Investigate electrical interference"),
                                            dmc.ListItem("Range failures (Test 1.1): Verify operational bounds")
                                        ])
                                    ], gap="xs")
                                ])
                            ], value="interpretation")
                        ], variant="separated"),
                        dmc.Divider(),
                        dmc.Alert([
                            dmc.Group([
                                BootstrapIcon(icon="lightbulb", width=16),
                                dmc.Text("Key Features", fw=500)
                            ], gap="xs", mb="xs"),
                            dmc.Text("✓ Real CSV data analysis (no synthetic data) ✓ Time-aligned comparisons ✓ Statistical robustness ✓ Comprehensive pass/fail criteria ✓ Visual result interpretation", size="xs")
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
                                            placeholder="Enter FLAT threshold",
                                            min=0,
                                            value=5.0,
                                            size="sm"
                                        ),
                                        dmc.NumberInput(
                                            label="Accuracy Range",
                                            id="accuracy-range-input",
                                            placeholder="Enter accuracy range",
                                            min=0,
                                            value=1.0,
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
                                                label="4.1: Signals are Stable", id="robustness-check-1")
                                        ], gap="xs")
                                    ], withBorder=True, p="sm"),
                                    dmc.Card([
                                        dmc.Stack([
                                            dmc.Text("Accuracy Checks",
                                             fw=500, c="red"),
                                            dmc.Checkbox(
                                                label="3.1: Digital/Analog Signals are in Close Agreement in the rtu File", id="accuracy-check-1"),
                                            dmc.Checkbox(
                                                label="3.2: Acceptable Signal-to-Noise ratio for D/A signals in the rtu File (> 30 dB)", id="accuracy-check-2"),
                                            dmc.Checkbox(
                                                label="3.3: MBS Target vs rtu Digital Signal Comparison", id="accuracy-check-3"),
                                            dmc.Checkbox(
                                                label="3.4: MBS target vs MBS reference signals Comparison", id="accuracy-check-4"),
                                            dmc.Checkbox(
                                                label="3.5: Target DIG/ANL SNR within 95% of Reference meter SNR", id="accuracy-check-5")
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
                                        placeholder="Enter window size",
                                        min=10,
                                        max=200,
                                        value=50,
                                        size="xs",
                                        style={"flex": "1"},
                                        description="Rolling window"
                                    ),
                                    dmc.NumberInput(
                                        label="Drift Threshold (%)",
                                        id="drift-threshold-input",
                                        placeholder="Enter drift threshold",
                                        min=0.1,
                                        max=20.0,
                                        value=5.0,
                                        step=0.1,
                                        size="xs",
                                        style={"flex": "1"},
                                        description="Max drift"
                                    ),
                                    dmc.NumberInput(
                                        label="Stability Threshold (%)",
                                        id="stability-threshold-input",
                                        placeholder="Enter stability threshold",
                                        min=50.0,
                                        max=100.0,
                                        value=90.0,
                                        step=1.0,
                                        size="xs",
                                        style={"flex": "1"},
                                        description="Required stability"
                                    )
                                ], gap="sm", align="stretch")
                            ], shadow="sm", p="sm", id="test-41-params-card", style={"display": "none"}),
                            dmc.Card([
                                dmc.Group([
                                    dmc.Button(
                                        "Run Analysis",
                                        id="run-analysis-btn",
                                        size="lg",
                                        variant="filled",
                                        className="px-4",
                                        leftSection=BootstrapIcon(
                                            icon="play-circle", width=20),
                                        disabled=True
                                    )
                                ], justify="center", gap="md"),
                                dmc.Space(h="sm"),
                                dmc.Group([
                                    dmc.Checkbox(
                                        id="use-existing-data-checkbox",
                                        label="Run Analysis with existing Data",
                                        description="Skip data extraction and use existing CSV files in _Data folder",
                                        size="sm"
                                    )
                                ], justify="center")
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
                        # Header with title and Export PDF button
                        dmc.Group([
                            dmc.Group([
                                dmc.Title("Analysis Results", order=2),
                                BootstrapIcon(icon="graph-up-arrow", width=24)
                            ], gap="xs"),
                            dmc.Button("Export PDF", variant="outline", size="sm",
                                       leftSection=BootstrapIcon(
                                           icon="file-pdf", width=16),
                                       id="export-pdf-btn")
                        ], justify="space-between", align="center"),

                        # PDF Export Modal
                        dmc.Modal(
                            title="Export PDF Report - Flowmeter Details",
                            id="pdf-export-modal",
                            size="lg",
                            children=[
                                dmc.Stack([
                                    dmc.Text("Please provide the following details for the PDF report:",
                                             size="sm", c="dimmed"),
                                    dmc.SimpleGrid([
                                        # Left column
                                        dmc.Stack([
                                            dmc.TextInput(
                                                label="Flowmeter Accepted",
                                                placeholder="Enter flowmeter identifier",
                                                id="pdf-flowmeter-name",
                                                required=True
                                            ),
                                            dmc.TextInput(
                                                label="Line Number",
                                                placeholder="Enter line number",
                                                id="pdf-line-number"
                                            ),
                                            dmc.TextInput(
                                                label="Location",
                                                placeholder="Enter location",
                                                id="pdf-location"
                                            )
                                        ], gap="md"),
                                        # Right column
                                        dmc.Stack([
                                            dmc.Select(
                                                label="Reason",
                                                placeholder="Select reason",
                                                id="pdf-reason",
                                                data=[
                                                    {"value": "New Installation",
                                                        "label": "New Installation"},
                                                    {"value": "Firmware Upgrade",
                                                        "label": "Firmware Upgrade"},
                                                    {"value": "Replacement",
                                                        "label": "Replacement"},
                                                    {"value": "Database Parameters Update",
                                                        "label": "Database Parameters Update"},
                                                    {"value": "Field Maintenance",
                                                        "label": "Field Maintenance"}
                                                ]
                                            ),
                                            dmc.TextInput(
                                                label="LDS Number",
                                                placeholder="Enter LDS number",
                                                id="pdf-lds-number"
                                            ),
                                            dmc.Select(
                                                label="Type",
                                                placeholder="Select type",
                                                id="pdf-type",
                                                data=[
                                                    {"value": "Mainline",
                                                        "label": "Mainline"},
                                                    {"value": "Injection",
                                                        "label": "Injection"},
                                                    {"value": "Delivery",
                                                        "label": "Delivery"},
                                                    {"value": "Injection/Mainline",
                                                        "label": "Injection/Mainline"},
                                                    {"value": "Delivery/Mainline",
                                                        "label": "Delivery/Mainline"}
                                                ]
                                            )
                                        ], gap="md")
                                    ], cols=2, spacing="xl"),
                                    dmc.Group([
                                        dmc.Button(
                                            "Cancel",
                                            variant="outline",
                                            id="pdf-cancel-btn"
                                        ),
                                        dmc.Button(
                                            "Generate PDF Report",
                                            leftSection=BootstrapIcon(
                                                icon="file-pdf", width=16),
                                            id="pdf-generate-btn",
                                            loading=False
                                        )
                                    ], justify="flex-end", gap="md", mt="xl")
                                ], gap="lg")
                            ]
                        ),

                        dmc.Divider(),

                        # Main Results Layout - Left column for test results, right column for plots
                        dmc.Group([
                            # Left Column - Test Results Summary Card - Wider and more compact
                            dmc.Card([
                                dmc.Group([
                                    dmc.Title("Test Results Summary", order=4),
                                    BootstrapIcon(
                                        icon="clipboard-check", width=18)
                                ], gap="xs", mb="sm"),
                                html.Div(id="test-results-summary", children=[
                                    dmc.Text("Run an analysis to see test results.",
                                             ta="center", c="dimmed", size="sm", py="md")
                                ])
                            ], shadow="sm", p="md", style={"width": "380px", "height": "75vh", "overflow": "auto"}),

                            # Right Column - Interactive Plots - Fill remaining space
                            dmc.Stack([
                                dmc.Tabs([
                                    dmc.TabsList([
                                        dmc.TabsTab("Time Trends",
                                                    value="time-trends"),
                                        dmc.TabsTab("Distributions",
                                                    value="distributions"),
                                        dmc.TabsTab(
                                            "Signal Stability Analysis", value="spectral"),
                                        dmc.TabsTab(
                                            "Quality Metrics", value="quality")
                                    ]),
                                    dmc.TabsPanel([
                                        dcc.Graph(id="time-trends-plot",
                                                  style={"height": "55vh", "width": "95%", "margin": "0 auto"})
                                    ], value="time-trends"),
                                    dmc.TabsPanel([
                                        dcc.Graph(id="distributions-plot",
                                                  style={"height": "55vh", "width": "95%", "margin": "0 auto"})
                                    ], value="distributions"),
                                    dmc.TabsPanel([
                                        dcc.Graph(id="spectral-plot",
                                                  style={"height": "55vh", "width": "95%", "margin": "0 auto"})
                                    ], value="spectral"),
                                    dmc.TabsPanel([
                                        html.Div(id="quality-metrics-cards",
                                                 style={"height": "55vh", "width": "95%", "overflow": "auto", "margin": "0 auto"})
                                    ], value="quality")
                                ], value="time-trends", id="results-plot-tabs")
                            ], style={"flex": "1", "maxWidth": "calc(100vw - 320px)"})
                        ], gap="sm", align="stretch", style={"height": "70vh"})
                    ], gap="sm", id="analysis-results-content")
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
    [Output("test-41-params-card", "style")],
    [Input("robustness-check-1", "checked")],
    prevent_initial_call=True
)
def toggle_robustness_params(rob1_checked):
    """Show/hide robustness parameter cards based on checkbox selection."""
    style_41 = {"display": "block"} if rob1_checked else {"display": "none"}
    return [style_41]


# Combined callback for preset checks and form clearing
@callback(
    [Output("reliability-check-1", "checked"),
     Output("reliability-check-2", "checked"),
     Output("reliability-check-3", "checked"),
     Output("reliability-check-4", "checked"),
     Output("tc-check-1", "checked"),
     Output("tc-check-2", "checked"),
     Output("robustness-check-1", "checked"),
     Output("accuracy-check-1", "checked"),
     Output("accuracy-check-2", "checked"),
     Output("accuracy-check-3", "checked"),
     Output("accuracy-check-4", "checked"),
     Output("accuracy-check-5", "checked"),
     Output("flat-threshold-input", "value"),
     Output("min-flowrate-input", "value"),
     Output("max-flowrate-input", "value"),
     Output("accuracy-range-input", "value"),
     Output("results-tab", "disabled", allow_duplicate=True),
     Output("main-tabs", "value", allow_duplicate=True)],
    [Input("partial-commissioning-btn", "n_clicks"),
     Input("full-acceptance-btn", "n_clicks")],
    [State("flat-threshold-input", "value"),
     State("min-flowrate-input", "value"),
     State("max-flowrate-input", "value"),
     State("accuracy-range-input", "value")],
    prevent_initial_call=True
)
def handle_form_actions(partial_clicks, full_clicks,
                        flat_threshold, min_flow, max_flow, accuracy_range):
    """Handle preset check selection and form clearing."""
    ctx = callback_context
    if not ctx.triggered:
        return [False] * 11 + [5, None, None, 1.0] + [True, "setup"]

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == "partial-commissioning-btn":
        # Partial commissioning preset: rel 1-4, tc 1-2, rob 1, acc 1&3&4 (core tests, skip SNR comparison)
        checks = [True, True, True, True, True, True,
                  True, True, False, True, True, False]
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
     State("accuracy-check-1", "checked"),
     State("accuracy-check-2", "checked"),
     State("accuracy-check-3", "checked"),
     State("accuracy-check-4", "checked"),
     State("accuracy-check-5", "checked"),
     State("stability-window-input", "value"),
     State("drift-threshold-input", "value"),
     State("stability-threshold-input", "value"),
     State("use-existing-data-checkbox", "checked"),
     State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def run_flowmeter_analysis(n_clicks, rtu_file, csv_file, review_file, start_time, end_time,
                           flat_threshold, min_flow, max_flow, accuracy_range,
                           rel1, rel2, rel3, rel4, tc1, tc2, rob1, acc1, acc2, acc3, acc4, acc5,
                           stability_window, drift_threshold, stability_threshold, use_existing_data, theme_data):
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

        # Validate required parameters based on selected tests
        validation_errors = []

        # Basic parameters validation
        if not all([flat_threshold, min_flow, max_flow, accuracy_range]):
            validation_errors.append(
                "Missing required parameters: FLAT Threshold, Min/Max Flowrate, and Accuracy Range must be provided")

        # Test 4.1 parameter validation
        if rob1 and not all([stability_window, drift_threshold, stability_threshold]):
            validation_errors.append(
                "Test 4.1 selected but missing parameters: Window Size, Drift Threshold, and Stability Threshold are required")

        if validation_errors:
            error_notification = dmc.Notification(
                title="Parameter Validation Failed",
                message="; ".join(validation_errors),
                color="red",
                autoClose=False,
                action="show",
                icon=BootstrapIcon(icon="exclamation-triangle")
            )
            return False, "setup", dash.no_update, True, dash.no_update, error_notification

        # Prepare parameters dictionary - UI must provide all required values, no defaults
        params = {
            'rtu_file': rtu_file,
            'csv_tags_file': csv_file,
            'review_file': review_file,
            'csv_file': "flowmeter_data",
            'report_name': "flowmeter_report",
            'time_start': start_str,
            'time_end': end_str,
            'flat_threshold': float(flat_threshold),
            'min_range': float(min_flow),
            'max_range': float(max_flow),
            'min_q': float(min_flow),
            'max_q': float(max_flow),
            'accuracy_range': float(accuracy_range),
            'reliability_check_1': rel1,
            'reliability_check_2': rel2,
            'reliability_check_3': rel3,
            'reliability_check_4': rel4,
            'tc_check_1': tc1,
            'tc_check_2': tc2,
            'robustness_check_1': rob1,
            'accuracy_check_1': acc1,
            'accuracy_check_2': acc2,
            'accuracy_check_3': acc3,
            'accuracy_check_4': acc4,
            'accuracy_check_5': acc5,
            # Robustness Test Parameters - only include if tests are selected
            'stability_window_size': int(stability_window) if rob1 else None,
            'drift_threshold': float(drift_threshold) if rob1 else None,
            'stability_threshold': float(stability_threshold) if rob1 else None,
            # Skip data extraction flag
            'use_existing_data': use_existing_data or False
        }

        # Run analysis
        results = service.run_analysis(params)

        # Create results display
        checks_selected = [rel1, rel2, rel3, rel4,
                           tc1, tc2, rob1, acc1, acc2, acc3, acc4]
        selected_count = sum(checks_selected)

        # Generate comprehensive time series visualizations
        plots = service.create_analysis_plots(theme_data)

        # Create CSV export notification
        csv_export_info = results.get('csv_export', {})
        exported_files = csv_export_info.get('exported_files', [])

        csv_notification = dmc.Notification(
            title="CSV Data Exported",
            message=f"Successfully exported {len(exported_files)} CSV files to _Data directory: SCADATagID_DIG.csv, SCADATagID_ANL.csv, Ref_SCADATagID.csv, MBSTagID.csv, Reference_Meter.csv",
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

# Validation callback to enable/disable Run Analysis button


@callback(
    Output("run-analysis-btn", "disabled"),
    [Input(rtu_file_ids['input'], "value"),
     Input(csv_tags_ids['input'], "value"),
     Input(review_file_ids['input'], "value"),
     Input("min-flowrate-input", "value"),
     Input("max-flowrate-input", "value"),
     Input("reliability-check-1", "checked"),
     Input("reliability-check-2", "checked"),
     Input("reliability-check-3", "checked"),
     Input("reliability-check-4", "checked"),
     Input("tc-check-1", "checked"),
     Input("tc-check-2", "checked"),
     Input("robustness-check-1", "checked"),
     Input("accuracy-check-1", "checked"),
     Input("accuracy-check-2", "checked"),
     Input("accuracy-check-3", "checked"),
     Input("accuracy-check-4", "checked"),
     Input("accuracy-check-5", "checked")]
)
def validate_required_fields(rtu_file, csv_file, review_file, min_flow, max_flow,
                             rel1, rel2, rel3, rel4, tc1, tc2, rob1, acc1, acc2, acc3, acc4, acc5):
    """Validate required fields and enable/disable Run Analysis button."""

    # Check if all required file fields are filled
    files_valid = all([rtu_file, csv_file, review_file])

    # Check if min and max flowrate are provided and valid
    flowrate_valid = all([
        min_flow is not None and min_flow != "",
        max_flow is not None and max_flow != "",
        isinstance(min_flow, (int, float)) or (
            isinstance(min_flow, str) and min_flow.strip()),
        isinstance(max_flow, (int, float)) or (
            isinstance(max_flow, str) and max_flow.strip())
    ])

    # Check if at least one analysis check is selected
    checks = [rel1, rel2, rel3, rel4, tc1, tc2,
              rob1, acc1, acc2, acc3, acc4, acc5]
    at_least_one_check = any(checks)

    # Enable button only if all validations pass
    return not (files_valid and flowrate_valid and at_least_one_check)

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
    Output("test-results-summary", "children"),
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_results_summary(results_data, theme_data):
    """Update the test results summary and additional reports."""
    if not results_data or not results_data.get('test_results'):
        no_data_msg = dmc.Text(
            "No analysis results available.", ta="center", c="dimmed", size="sm", py="md")
        return no_data_msg

    # Get theme
    template = theme_data.get(
        'template', 'mantine_light') if theme_data else 'mantine_light'
    is_dark = template == 'mantine_dark'

    test_results = results_data['test_results']

    # Define the specific tests we want to show (1.1 to 4.1) - Complete list
    target_tests = [
        # Test 1.1 - Range Checks
        ('Test 1.1 - Digital Signal Range', 'Test 1.1 - Digital Range Check'),
        ('Test 1.1 - Analog Signal Range', 'Test 1.1 - Analog Range Check'),
        # Test 1.2 - Units Verification
        ('Test 1.2 - Digital Signal Units', 'Test 1.2 - Digital Units Check'),
        ('Test 1.2 - Analog Signal Units', 'Test 1.2 - Analog Units Check'),
        # Test 1.3 - Quality Checks (stored as different keys in reliability_tests)
        ('Digital Signal Quality Check', 'Test 1.3 - Digital Quality Check'),
        ('Analog Signal Quality Check', 'Test 1.3 - Analog Quality Check'),
        # Test 1.4 - Review File Quality
        ('Test 1.4 - Review File Quality', 'Test 1.4 - Review Quality Check'),
        # Test 2.1 - Time Differences
        ('Test 2.1 - Digital Signal Time Diff', 'Test 2.1 - Digital Time Diff'),
        ('Test 2.1 - Analog Signal Time Diff', 'Test 2.1 - Analog Time Diff'),
        # Test 2.2 - FLAT Attribute
        ('Test 2.2 - FLAT Attribute Check', 'Test 2.2 - FLAT Attribute'),
        # Test 3.1 - Mean Squared Error
        ('Test 3.1 - Mean Squared Error', 'Test 3.1 - MSE Analysis'),
        # Test 3.2 - Signal-to-Noise Ratio
        ('Test 3.2 - Digital Signal SNR', 'Test 3.2 - Digital SNR Analysis'),
        ('Test 3.2 - Analog Signal SNR', 'Test 3.2 - Analog SNR Analysis'),
        # Test 3.3 & 3.4 - Target Comparisons
        ('Test 3.3 - Target vs Digital', 'Test 3.3 - Target vs Digital'),
        ('Test 3.4 - Target vs Reference', 'Test 3.4 - Target vs Reference'),
        # Test 3.5 - SNR Comparison
        ('Test 3.5 - SNR Comparison', 'Test 3.5 - SNR Comparison'),
        # Test 4.1 - Signal Stability
        ('Test 4.1 - Digital Signal Stability', 'Test 4.1 - Digital Stability'),
        ('Test 4.1 - Analog Signal Stability', 'Test 4.1 - Analog Stability')
    ]

    # Create compact test results summary
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
                    BootstrapIcon(icon=status_icon, width=14,
                                  color=status_color),
                    dmc.Text(f"Meter: {meter_name}", fw=600, size="sm")
                ], gap="xs", mb="2px"),
                dmc.Divider(size="xs", mb="2px")
            ], p="xs", mb="4px", style={"backgroundColor": "var(--mantine-color-gray-1)" if not is_dark else "var(--mantine-color-dark-6)"})
        )

        # Collect all tests from all categories
        all_tests = {}
        for category_name, category_tests in meter_results.items():
            if category_name in ['reliability_tests', 'timeliness_tests', 'accuracy_tests', 'robustness_tests']:
                all_tests.update(category_tests)

        # Show only target tests in sorted order
        for test_key, display_name in target_tests:
            if test_key in all_tests:
                total_tests += 1
                test_result = all_tests[test_key]
                test_status = test_result.get('status', 'unknown')
                if test_status == 'pass':
                    passed_tests += 1

                # Compact format: just thumbs up/down and test title
                test_icon = "hand-thumbs-up-fill" if test_status == 'pass' else "hand-thumbs-down-fill" if test_status == 'fail' else "question-circle"
                test_color = "green" if test_status == 'pass' else "red" if test_status == 'fail' else "orange"

                test_cards.append(
                    dmc.Group([
                        BootstrapIcon(icon=test_icon, width=14,
                                      color=test_color),
                        dmc.Text(display_name, size="xs", fw=500)
                    ], gap="xs", align="center", ml="sm", mb="2px")
                )

    # Check if all tests passed and add pass image
    all_tests_passed = total_tests > 0 and passed_tests == total_tests

    if all_tests_passed:
        # Add pass.png image at the bottom when all tests pass
        test_cards.append(
            dmc.Center([
                dmc.Stack([
                    dmc.Divider(mb="md"),
                    html.Img(
                        src="/assets/passed.png",  # Use the passed.png from assets folder
                        style={
                            "width": "120px",
                            "height": "auto",
                            # Green glow
                            "filter": "drop-shadow(0 4px 12px rgba(34, 197, 94, 0.4))",
                            "transform": "scale(1.05)",
                            "transition": "all 0.3s ease"
                        }
                    ),
                    dmc.Text(
                        f"🎉 ALL TESTS PASSED! 🎉",
                        size="md",
                        fw=700,
                        c="green",
                        ta="center",
                        style={
                            "textShadow": "0 2px 4px rgba(34, 197, 94, 0.3)"}
                    ),
                    dmc.Text(
                        f"{passed_tests}/{total_tests} Tests Successful",
                        size="sm",
                        c="dimmed",
                        ta="center"
                    )
                ], gap="xs", align="center")
            ], mt="md")
        )

    test_summary = dmc.Stack(test_cards, gap="2px") if test_cards else dmc.Text(
        "No test results available.", c="dimmed", size="sm")

    return test_summary


@callback(
    Output("time-trends-plot", "figure"),
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_time_trends_plot(results_data, theme_data):
    """Create time trends plot showing 4 data sources: Target, Reference, RTU Analog, RTU Digital."""
    template = theme_data.get(
        'template', 'mantine_light') if theme_data else 'mantine_light'

    if not results_data:
        fig = go.Figure()
        fig.update_layout(
            template=template,
            title="Time Trends - Run analysis to view data",
            xaxis_title="Time",
            yaxis_title="Flow Rate",
            margin=dict(l=40, r=40, t=60, b=40)
        )
        return fig

    # Load data from the 4 required CSV files
    try:
        csv_export_info = results_data.get('csv_export', {})
        data_dir = csv_export_info.get('data_dir')

        if not data_dir:
            raise ValueError("No data directory found")

        # Define the 5 required CSV files with their specific formats
        data_sources = [
            {
                'file': os.path.join(data_dir, "MBSTagID.csv"),
                'name': "Target Meter",
                'color': '#1f77b4',  # Blue
                'line_style': 'solid',
                'time_column': 'TIME',
                'value_column': ':VAL',  # Look for column ending with :VAL
                'format_type': 'mbs'
            },
            {
                'file': os.path.join(data_dir, "Reference_Meter.csv"),
                'name': "Reference Meter",
                'color': '#ff7f0e',  # Orange
                'line_style': 'dash',
                'time_column': 'TIME',
                'value_column': ':VAL',  # Look for column ending with :VAL
                'format_type': 'reference'
            },
            {
                'file': os.path.join(data_dir, "SCADATagID_ANL.csv"),
                'name': "RTU Analog Signal",
                'color': '#2ca02c',  # Green
                'line_style': 'dot',
                'time_column': 'datetime',
                'value_column': 'value',
                'format_type': 'scada'
            },
            {
                'file': os.path.join(data_dir, "SCADATagID_DIG.csv"),
                'name': "RTU Digital Signal",
                'color': '#d62728',  # Red
                'line_style': 'dashdot',
                'time_column': 'datetime',
                'value_column': 'value',
                'format_type': 'scada'
            },
            {
                'file': os.path.join(data_dir, "Ref_SCADATagID.csv"),
                'name': "Reference RTU Signal",
                'color': '#9467bd',  # Purple
                'line_style': 'longdash',
                'time_column': 'datetime',
                'value_column': 'value',
                'format_type': 'scada'
            }
        ]

        fig = go.Figure()

        debug_info = []  # For debugging

        for source in data_sources:
            if os.path.exists(source['file']):
                try:
                    df = pd.read_csv(source['file'])
                    df.columns = df.columns.str.strip()  # Clean column names
                    debug_info.append(
                        f"{source['name']}: Found {len(df)} rows, columns: {list(df.columns)}")

                    # Find time and value columns based on format type
                    time_col = None
                    value_col = None

                    if source['format_type'] in ['mbs', 'reference']:
                        # MBS and Reference format: TIME, SN_QSO_SU_5M1:VAL, SN_QSO_SU_5M1:ST, SN_QSO_SU_5M1:FLAT
                        time_col = source['time_column']  # 'TIME'
                        # Find column ending with :VAL
                        for col in df.columns:
                            if col.endswith(':VAL'):
                                value_col = col
                                break

                    elif source['format_type'] == 'scada':
                        # SCADA format: datetime,timestamp,tag_name,value,quality
                        time_col = source['time_column']  # 'datetime'
                        value_col = source['value_column']  # 'value'

                    # Check if we found the required columns
                    if time_col not in df.columns:
                        debug_info.append(
                            f"{source['name']}: Time column '{time_col}' not found in {list(df.columns)}")
                        continue

                    if not value_col or value_col not in df.columns:
                        debug_info.append(
                            f"{source['name']}: Value column '{value_col}' not found in {list(df.columns)}")
                        continue

                    # Convert timestamp and clean data
                    if source['format_type'] in ['mbs', 'reference']:
                        # MBS/Reference format: 2025/06/27 04:30:00.000
                        df[time_col] = pd.to_datetime(
                            df[time_col], format='%Y/%m/%d %H:%M:%S.%f', errors='coerce')
                    else:
                        # SCADA format: 2025-06-27 04:30:03
                        df[time_col] = pd.to_datetime(
                            df[time_col], errors='coerce')

                    # Remove rows with NaN timestamps or values
                    df = df.dropna(subset=[time_col, value_col])
                    df = df.sort_values(time_col)

                    # Ensure values are numeric
                    df[value_col] = pd.to_numeric(
                        df[value_col], errors='coerce')
                    df = df.dropna(subset=[value_col])

                    if len(df) > 0:
                        # Add trace to plot
                        fig.add_trace(go.Scatter(
                            x=df[time_col],
                            y=df[value_col],
                            mode='lines',
                            name=source['name'],
                            line=dict(
                                color=source['color'],
                                width=2,
                                dash=source['line_style']
                            ),
                            hovertemplate="<b>%{fullData.name}</b><br>" +
                            "Time: %{x}<br>" +
                            "Value: %{y:.4f}<br>" +
                            "<extra></extra>"
                        ))
                        debug_info.append(
                            f"{source['name']}: Successfully loaded {len(df)} data points using {time_col} and {value_col}")
                    else:
                        debug_info.append(
                            f"{source['name']}: No valid data after cleaning")

                except Exception as e:
                    debug_info.append(f"{source['name']}: Error - {str(e)}")
                    continue
            else:
                debug_info.append(
                    f"{source['name']}: File not found - {source['file']}")

        # If no data loaded, show debug information
        if not fig.data:
            # Show first 10 debug messages
            debug_text = "<br>".join(debug_info[:10])
            fig.add_annotation(
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                text=f"No time trend data loaded.<br><br>Debug Info:<br>{debug_text}",
                showarrow=False,
                font=dict(size=12),
                align="left"
            )

        if not fig.data:
            fig.add_annotation(
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                text="No time trend data available.<br>Ensure CSV files are generated from analysis.",
                showarrow=False,
                font=dict(size=16),
                align="center"
            )

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            text=f"Error loading time trend data: {str(e)}",
            showarrow=False,
            font=dict(size=14)
        )

    # Calculate Y-axis range: 0 to Q_max (maximum value from all traces)
    y_max = 0
    if fig.data:
        for trace in fig.data:
            if hasattr(trace, 'y') and trace.y is not None:
                trace_max = max(trace.y) if len(trace.y) > 0 else 0
                y_max = max(y_max, trace_max)

    # Add 10% padding to the maximum value
    q_max = y_max * 1.1 if y_max > 0 else 100

    # Update layout with sparse datetime ticks and fixed Y-axis range
    fig.update_layout(
        template=template,
        title="Time Trends - Target, Reference, RTU Analog & Digital Signals",
        xaxis_title="Time",
        yaxis_title="Flow Rate",
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        # Configure sparse datetime ticks
        xaxis=dict(
            tickmode='auto',
            nticks=8,  # Limit number of ticks
            tickformat='%m/%d %H:%M',  # Shorter date format
            tickangle=45
        ),
        # Fix Y-axis range from 0 to Q_max
        yaxis=dict(
            title="Flow Rate",
            range=[0, q_max],
            fixedrange=False  # Allow zooming but default to 0-Q_max
        ),
        hovermode='x unified'
    )

    return fig


@callback(
    Output("distributions-plot", "figure"),
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_distributions_plot(results_data, theme_data):
    """Create distribution plot showing Digital and Analog signals from RTU with bar chart and curve."""
    template = theme_data.get(
        'template', 'mantine_light') if theme_data else 'mantine_light'

    if not results_data or not results_data.get('plots_data'):
        fig = go.Figure()
        fig.update_layout(
            template=template,
            title="Signal Distribution - Run analysis to view data",
            xaxis_title="Signal Value",
            yaxis_title="Frequency",
            margin=dict(l=40, r=40, t=60, b=40)
        )
        return fig

    # Load the actual RTU data for Digital and Analog signals
    try:
        csv_export_info = results_data.get('csv_export', {})
        data_dir = csv_export_info.get('data_dir')

        if not data_dir:
            raise ValueError("No data directory found in analysis results")

        digital_csv = os.path.join(data_dir, "SCADATagID_DIG.csv")
        analog_csv = os.path.join(data_dir, "SCADATagID_ANL.csv")

        fig = go.Figure()
        colors = ['#1f77b4', '#ff7f0e']  # Blue for digital, orange for analog

        # Process Digital signals (SCADA format) - Calculate reporting frequency
        if os.path.exists(digital_csv):
            df_dig = pd.read_csv(digital_csv)
            df_dig.columns = df_dig.columns.str.strip()

            # SCADA format has 'datetime' column - calculate reporting frequency
            if 'datetime' in df_dig.columns and len(df_dig) > 1:
                # Convert datetime and calculate time differences (reporting frequency)
                timestamps = pd.to_datetime(
                    df_dig['datetime'], errors='coerce').dropna()
                timestamps = timestamps.sort_values()

                if len(timestamps) > 1:
                    # Calculate time differences in seconds
                    time_diffs = timestamps.diff().dt.total_seconds().dropna()

                    if len(time_diffs) > 0:
                        # Bar chart for reporting frequency distribution
                        fig.add_trace(go.Histogram(
                            x=time_diffs,
                            name="Digital Reporting Frequency",
                            marker_color=colors[0],
                            opacity=0.6,
                            nbinsx=30,
                            histnorm='probability',
                            yaxis='y'
                        ))

                        # Add smooth curve (KDE approximation)
                        hist, bin_edges = np.histogram(
                            time_diffs, bins=50, density=True)
                        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

                        # Simple smoothing for curve
                        try:
                            from scipy import ndimage
                            smoothed_hist = ndimage.gaussian_filter1d(
                                hist, sigma=1.0)
                            fig.add_trace(go.Scatter(
                                x=bin_centers,
                                y=smoothed_hist * np.diff(bin_edges)[0],
                                mode='lines',
                                name='Digital Frequency Curve',
                                line=dict(color=colors[0], width=3),
                                yaxis='y2'
                            ))
                        except ImportError:
                            # Fallback without smoothing
                            fig.add_trace(go.Scatter(
                                x=bin_centers,
                                y=hist * np.diff(bin_edges)[0],
                                mode='lines',
                                name='Digital Frequency Curve',
                                line=dict(color=colors[0], width=3),
                                yaxis='y2'
                            ))

        # Process Analog signals (SCADA format) - Calculate reporting frequency
        if os.path.exists(analog_csv):
            df_anl = pd.read_csv(analog_csv)
            df_anl.columns = df_anl.columns.str.strip()

            # SCADA format has 'datetime' column - calculate reporting frequency
            if 'datetime' in df_anl.columns and len(df_anl) > 1:
                # Convert datetime and calculate time differences (reporting frequency)
                timestamps = pd.to_datetime(
                    df_anl['datetime'], errors='coerce').dropna()
                timestamps = timestamps.sort_values()

                if len(timestamps) > 1:
                    # Calculate time differences in seconds
                    time_diffs = timestamps.diff().dt.total_seconds().dropna()

                    if len(time_diffs) > 0:
                        # Bar chart for reporting frequency distribution
                        fig.add_trace(go.Histogram(
                            x=time_diffs,
                            name="Analog Reporting Frequency",
                            marker_color=colors[1],
                            opacity=0.6,
                            nbinsx=30,
                            histnorm='probability',
                            yaxis='y'
                        ))

                        # Add smooth curve (KDE approximation)
                        hist, bin_edges = np.histogram(
                            time_diffs, bins=50, density=True)
                        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

                        # Simple smoothing for curve
                        try:
                            from scipy import ndimage
                            smoothed_hist = ndimage.gaussian_filter1d(
                                hist, sigma=1.0)
                            fig.add_trace(go.Scatter(
                                x=bin_centers,
                                y=smoothed_hist * np.diff(bin_edges)[0],
                                mode='lines',
                                name='Analog Frequency Curve',
                                line=dict(color=colors[1], width=3),
                                yaxis='y2'
                            ))
                        except ImportError:
                            # Fallback without smoothing
                            fig.add_trace(go.Scatter(
                                x=bin_centers,
                                y=hist * np.diff(bin_edges)[0],
                                mode='lines',
                                name='Analog Frequency Curve',
                                line=dict(color=colors[1], width=3),
                                yaxis='y2'
                            ))

        if not fig.data:
            # No data available
            fig.add_annotation(
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                text="No RTU signal data available",
                showarrow=False,
                font=dict(size=16)
            )

    except Exception as e:
        # Error loading data - show error message
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            text=f"Error loading RTU data: {str(e)}",
            showarrow=False,
            font=dict(size=14)
        )

    # Update layout with dual y-axes for histogram and curve
    fig.update_layout(
        template=template,
        title="Digital and Analog Signal Reporting Frequency Distribution",
        xaxis_title="Time Interval (seconds)",
        yaxis=dict(title="Probability (Histogram)", side="left"),
        yaxis2=dict(title="Density (Curve)", side="right", overlaying="y"),
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=True,
        hovermode='x unified'
    )

    return fig


@callback(
    Output("spectral-plot", "figure"),
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_spectral_plot(results_data, theme_data):
    """Create signal stability analysis plots for test 4.1."""
    template = theme_data.get(
        'template', 'mantine_light') if theme_data else 'mantine_light'

    if not results_data or not results_data.get('test_results'):
        fig = go.Figure()
        fig.update_layout(
            template=template,
            title="Signal Stability Analysis (Test 4.1) - Run analysis to view data",
            xaxis_title="Time",
            yaxis_title="Signal Value",
            margin=dict(l=40, r=40, t=60, b=40)
        )
        return fig

    from plotly.subplots import make_subplots

    # Create subplots for stability analysis
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Digital Signal Stability", "Analog Signal Stability",
                        "Stability Percentage Over Time", "Signal Drift Analysis"),
        vertical_spacing=0.18,
        horizontal_spacing=0.1
    )

    test_results = results_data.get('test_results', {})
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

    # Try to load actual RTU data for stability analysis
    try:
        csv_export_info = results_data.get('csv_export', {})
        data_dir = csv_export_info.get('data_dir')

        if data_dir:
            digital_csv = os.path.join(data_dir, "SCADATagID_DIG.csv")
            analog_csv = os.path.join(data_dir, "SCADATagID_ANL.csv")

            # Plot Digital signal stability (SCADA format)
            if os.path.exists(digital_csv):
                df_dig = pd.read_csv(digital_csv)
                df_dig.columns = df_dig.columns.str.strip()

                if 'datetime' in df_dig.columns and 'value' in df_dig.columns:
                    timestamps = pd.to_datetime(df_dig['datetime'])
                    values = pd.to_numeric(
                        df_dig['value'], errors='coerce').dropna()

                    if len(values) > 0:
                        # Plot raw signal
                        fig.add_trace(go.Scatter(
                            x=timestamps[:len(values)],
                            y=values,
                            mode='lines',
                            name='Digital Signal',
                            line=dict(color=colors[0], width=1)
                        ), row=1, col=1)

                        # Calculate rolling stability (standard deviation)
                        # Adaptive window size
                        window_size = min(50, len(values) // 4)
                        if window_size > 1:
                            rolling_std = values.rolling(
                                window=window_size, min_periods=1).std()
                            stability_pct = 100 * \
                                (1 - rolling_std / values.std())

                            fig.add_trace(go.Scatter(
                                x=timestamps[:len(stability_pct)],
                                y=stability_pct,
                                mode='lines',
                                name='Digital Stability %',
                                line=dict(color=colors[0], width=2)
                            ), row=2, col=1)

            # Plot Analog signal stability (SCADA format)
            if os.path.exists(analog_csv):
                df_anl = pd.read_csv(analog_csv)
                df_anl.columns = df_anl.columns.str.strip()

                if 'datetime' in df_anl.columns and 'value' in df_anl.columns:
                    timestamps = pd.to_datetime(df_anl['datetime'])
                    values = pd.to_numeric(
                        df_anl['value'], errors='coerce').dropna()

                    if len(values) > 0:
                        # Plot raw signal
                        fig.add_trace(go.Scatter(
                            x=timestamps[:len(values)],
                            y=values,
                            mode='lines',
                            name='Analog Signal',
                            line=dict(color=colors[1], width=1)
                        ), row=1, col=2)

                        # Calculate rolling stability
                        # Adaptive window size
                        window_size = min(50, len(values) // 4)
                        if window_size > 1:
                            rolling_std = values.rolling(
                                window=window_size, min_periods=1).std()
                            stability_pct = 100 * \
                                (1 - rolling_std / values.std())

                            fig.add_trace(go.Scatter(
                                x=timestamps[:len(stability_pct)],
                                y=stability_pct,
                                mode='lines',
                                name='Analog Stability %',
                                line=dict(color=colors[1], width=2)
                            ), row=2, col=1)

                            # Add drift analysis (difference from mean)
                            mean_value = values.mean()
                            drift = values - mean_value

                            fig.add_trace(go.Scatter(
                                x=timestamps[:len(drift)],
                                y=drift,
                                mode='lines',
                                name='Signal Drift',
                                line=dict(color=colors[2], width=1)
                            ), row=2, col=2)

        # Extract Test 4.1 results and add summary annotations
        has_stability_data = False
        for meter_name, meter_results in test_results.items():
            if 'robustness_tests' in meter_results:
                digital_test = meter_results['robustness_tests'].get(
                    'Test 4.1 - Digital Signal Stability')
                analog_test = meter_results['robustness_tests'].get(
                    'Test 4.1 - Analog Signal Stability')

                if digital_test:
                    has_stability_data = True
                    # Add annotation with test results
                    fig.add_annotation(
                        x=0.02, y=0.98,
                        xref="paper", yref="paper",
                        text=f"<b>Digital:</b> {digital_test.get('value', 'N/A')}<br>" +
                             f"<b>Status:</b> {digital_test.get('status', 'unknown').upper()}",
                        showarrow=False,
                        align="left",
                        font=dict(size=10)
                    )

                if analog_test:
                    has_stability_data = True
                    fig.add_annotation(
                        x=0.52, y=0.98,
                        xref="paper", yref="paper",
                        text=f"<b>Analog:</b> {analog_test.get('value', 'N/A')}<br>" +
                             f"<b>Status:</b> {analog_test.get('status', 'unknown').upper()}",
                        showarrow=False,
                        align="left",
                        font=dict(size=10)
                    )

        if not has_stability_data:
            fig.add_annotation(
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                text="Enable Test 4.1 (Signal Stability) to view stability analysis",
                showarrow=False,
                font=dict(size=16)
            )

    except Exception as e:
        fig.add_annotation(
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            text=f"Error loading stability data: {str(e)}",
            showarrow=False,
            font=dict(size=14)
        )

    # Update subplot titles and axes
    fig.update_xaxes(title_text="Time", row=1, col=1)
    fig.update_xaxes(title_text="Time", row=1, col=2)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=2)

    fig.update_yaxes(title_text="Signal Value", row=1, col=1)
    fig.update_yaxes(title_text="Signal Value", row=1, col=2)
    fig.update_yaxes(title_text="Stability (%)", row=2, col=1)
    fig.update_yaxes(title_text="Drift from Mean", row=2, col=2)

    fig.update_layout(
        template=template,
        title="Signal Stability Analysis - Test 4.1",
        margin=dict(l=40, r=40, t=80, b=40),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
        )
    )

    return fig


@callback(
    Output("quality-metrics-cards", "children"),
    [Input("analysis-results-store", "data")],
    [State("plotly-theme-store", "data")],
    prevent_initial_call=True
)
def update_quality_metrics_cards(results_data, theme_data):
    """Create quality metrics cards showing MSE and SNR values only."""
    if not results_data or not results_data.get('test_results'):
        return dmc.Center([
            dmc.Stack([
                BootstrapIcon(icon="graph-up", width=48,
                              color="var(--mantine-color-gray-5)"),
                dmc.Text("Quality Metrics Dashboard",
                         size="lg", fw=500, ta="center"),
                dmc.Text("Run an analysis to view MSE and SNR metrics",
                         ta="center", c="dimmed", size="sm")
            ], gap="md", align="center")
        ], style={"height": "100%"})

    test_results = results_data.get('test_results', {})
    cards = []

    # Create cards for each meter
    for meter_name, meter_results in test_results.items():
        mse_value = "N/A"
        snr_digital = "N/A"
        snr_analog = "N/A"

        # Extract MSE and SNR values from test results
        snr_reference = "N/A"
        if 'accuracy_tests' in meter_results:
            # Get MSE from Test 3.1
            mse_test = meter_results['accuracy_tests'].get(
                'Test 3.1 - Mean Squared Error')
            if mse_test and 'MSE:' in mse_test.get('value', ''):
                try:
                    mse_str = mse_test['value'].split(
                        'MSE:')[1].split(',')[0].strip()
                    mse_value = f"{float(mse_str):.4f}"
                except:
                    mse_value = "N/A"

            # Get Digital SNR from Test 3.2
            snr_dig_test = meter_results['accuracy_tests'].get(
                'Test 3.2 - Digital Signal SNR')
            if snr_dig_test and 'SNR:' in snr_dig_test.get('value', ''):
                try:
                    snr_str = snr_dig_test['value'].split('SNR:')[1].strip()
                    if snr_str != 'N/A':
                        snr_digital = f"{float(snr_str.split()[0]):.2f} dB"
                except:
                    snr_digital = "N/A"

            # Get Analog SNR from Test 3.2
            snr_anl_test = meter_results['accuracy_tests'].get(
                'Test 3.2 - Analog Signal SNR')
            if snr_anl_test and 'SNR:' in snr_anl_test.get('value', ''):
                try:
                    snr_str = snr_anl_test['value'].split('SNR:')[1].strip()
                    if snr_str != 'N/A':
                        snr_analog = f"{float(snr_str.split()[0]):.2f} dB"
                except:
                    snr_analog = "N/A"

            # Get Reference SNR from Test 3.5
            snr_comp_test = meter_results['accuracy_tests'].get(
                'Test 3.5 - SNR Comparison')
            if snr_comp_test and 'Ref:' in snr_comp_test.get('value', ''):
                try:
                    # Extract reference SNR from "Digital: X.XdB, Analog: X.XdB, Ref: X.XdB" format
                    snr_str = snr_comp_test['value'].split('Ref:')[1].strip()
                    if snr_str != 'N/A' and 'dB' in snr_str:
                        ref_value = snr_str.replace('dB', '').strip()
                        snr_reference = f"{float(ref_value):.2f} dB"
                except:
                    snr_reference = "N/A"

        # Create meter card with theme-aware styling
        meter_card = dmc.Card([
            # Meter header
            dmc.Group([
                BootstrapIcon(icon="speedometer2", width=20),
                dmc.Text(f"Meter: {meter_name}", fw=600, size="md")
            ], gap="xs", mb="md"),

            # Quality metrics layout - Centered cards
            dmc.Center([
                dmc.Stack([
                    # MSE Card - Top center
                    dmc.Card([
                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="calculator", width=18,
                                              color="var(--mantine-color-orange-6)"),
                                dmc.Text("Mean Squared Error",
                                         size="sm", fw=500)
                            ], gap="xs", justify="center"),
                            dmc.Text(mse_value, size="xl", fw=700,
                                     ta="center", c="orange"),
                            dmc.Text("Test 3.1 Result", size="xs",
                                     c="dimmed", ta="center")
                        ], gap="xs")
                    ], shadow="sm", p="md", style={"width": "300px"}),

                    # Combined SNR Card - Below MSE, centered
                    dmc.Card([
                        dmc.Stack([
                            # Card header with icon
                            dmc.Group([
                                BootstrapIcon(icon="activity", width=18,
                                              color="var(--mantine-color-blue-6)"),
                                dmc.Text("Signal-to-Noise Ratio (SNR)",
                                         size="sm", fw=500)
                            ], gap="xs", justify="center"),

                            # SNR values in a horizontal layout
                            dmc.Group([
                                # Digital SNR
                                dmc.Stack([
                                    dmc.Text("Digital", size="xs",
                                             fw=500, ta="center", c="blue"),
                                    dmc.Text(snr_digital, size="lg",
                                             fw=700, ta="center", c="blue"),
                                ], gap="2px", align="center"),

                                dmc.Divider(orientation="vertical", size="sm"),

                                # Analog SNR
                                dmc.Stack([
                                    dmc.Text("Analog", size="xs",
                                             fw=500, ta="center", c="green"),
                                    dmc.Text(snr_analog, size="lg",
                                             fw=700, ta="center", c="green"),
                                ], gap="2px", align="center"),

                                dmc.Divider(orientation="vertical", size="sm"),

                                # Reference SNR
                                dmc.Stack([
                                    dmc.Text("Reference", size="xs",
                                             fw=500, ta="center", c="purple"),
                                    dmc.Text(snr_reference, size="lg",
                                             fw=700, ta="center", c="purple"),
                                ], gap="2px", align="center")
                            ], justify="center", gap="lg"),

                            dmc.Text("Test 3.2 & 3.5 Results", size="xs",
                                     c="dimmed", ta="center")
                        ], gap="md")
                    ], shadow="sm", p="md", style={"width": "400px"})
                ], gap="lg", align="center")
            ])
        ], shadow="sm", p="md", mb="md")

        cards.append(meter_card)

    if not cards:
        return dmc.Center([
            dmc.Text("No quality metrics data available",
                     ta="center", c="dimmed", size="md")
        ], style={"height": "100%"})

    return dmc.Stack(cards, gap="md")


# Modal Toggle Callback
@callback(
    Output("pdf-export-modal", "opened"),
    [Input("export-pdf-btn", "n_clicks"),
     Input("pdf-cancel-btn", "n_clicks")],
    [State("pdf-export-modal", "opened"),
     State("analysis-results-store", "data")],
    prevent_initial_call=True
)
def toggle_pdf_modal(export_clicks, cancel_clicks, modal_opened, results_data):
    """Toggle PDF export modal."""
    triggered = callback_context.triggered[0]["prop_id"]

    if triggered == "export-pdf-btn.n_clicks" and results_data:
        return True
    elif triggered == "pdf-cancel-btn.n_clicks":
        return False

    return modal_opened


# PDF Loading Indicator Callback
@callback(
    Output("pdf-generate-btn", "loading"),
    [Input("pdf-generate-btn", "n_clicks")],
    prevent_initial_call=True
)
def show_pdf_loading(n_clicks):
    """Show loading state on button when PDF generation starts."""
    if n_clicks:
        return True
    return False


# PDF Export Callback
@callback(
    [Output("pdf-export-modal", "opened", allow_duplicate=True),
     Output("export-pdf-btn", "children"),
     Output("pdf-generate-btn", "loading", allow_duplicate=True)],
    [Input("pdf-generate-btn", "n_clicks")],
    [State("analysis-results-store", "data"),
     State("plotly-theme-store", "data"),
     State("file-store-flowmeter-csv-tags", "data"),
     State("time-trends-plot", "figure"),
     State("distributions-plot", "figure"),
     State("spectral-plot", "figure"),
     State("pdf-flowmeter-name", "value"),
     State("pdf-line-number", "value"),
     State("pdf-location", "value"),
     State("pdf-reason", "value"),
     State("pdf-lds-number", "value"),
     State("pdf-type", "value")],
    prevent_initial_call=True
)
def generate_pdf_report(n_clicks, results_data, theme_data, tags_file_data,
                        trends_fig, dist_fig, stability_fig,
                        flowmeter_name, line_number, location, reason, lds_number, type_val):
    """Generate comprehensive PDF report with flowmeter details."""
    if not n_clicks or not results_data:
        return False, "Export PDF", False

    # Validate required fields
    if not flowmeter_name or not flowmeter_name.strip():
        return True, [
            BootstrapIcon(icon="exclamation-triangle-fill",
                          width=16, color="red"),
            " Flowmeter name required"
        ], False

    try:
        # Get the tags file path to determine where to save the PDF
        tags_file_path = None
        if tags_file_data and tags_file_data.get('path'):
            tags_file_path = tags_file_data['path']
            # Create PDF path next to tags file with flowmeter name
            safe_name = "".join(
                c for c in flowmeter_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            pdf_filename = f"FinalReport_{safe_name}.pdf"
            pdf_path = os.path.join(
                os.path.dirname(tags_file_path), pdf_filename)
        else:
            # Fallback to current directory
            safe_name = "".join(
                c for c in flowmeter_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            pdf_path = f"FinalReport_{safe_name}.pdf"

        # Prepare flowmeter details
        flowmeter_details = {
            'flowmeter_name': flowmeter_name,
            'line_number': line_number or 'N/A',
            'location': location or 'N/A',
            'reason': reason or 'N/A',
            'lds_number': lds_number or 'N/A',
            'type': type_val or 'N/A'
        }

        # Generate comprehensive PDF report using available libraries
        result = generate_comprehensive_pdf_report(
            pdf_path, results_data, trends_fig, dist_fig, stability_fig, flowmeter_details)

        return False, result, False  # Close modal, return result, stop loading

    except Exception as e:
        return True, [
            BootstrapIcon(icon="exclamation-triangle-fill",
                          width=16, color="red"),
            f" Error: {str(e)}"
        ], False  # Keep modal open, show error, stop loading


def generate_comprehensive_pdf_report(pdf_path, results_data, trends_fig, dist_fig, stability_fig, flowmeter_details=None):
    """Generate comprehensive PDF report using matplotlib and plotly."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.patches as patches
        import plotly.graph_objects as go
        from datetime import datetime

        # Create PDF with multiple pages
        with PdfPages(pdf_path) as pdf:
            # Page 1: Title and Test Results Summary
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.axis('off')

            # Title - moved higher for more top margin
            fig.suptitle('Flowmeter Acceptance Test Report',
                         fontsize=16, fontweight='bold', y=0.97)
            # Closer spacing between title and generated date
            ax.text(0.5, 0.92, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    ha='center', va='top', transform=ax.transAxes, fontsize=10)

            # Flowmeter Details Table (if provided) - Start higher
            y_start = 0.88
            if flowmeter_details:
                # More compact section header
                ax.text(0.05, y_start, 'Flowmeter Details', transform=ax.transAxes,
                        fontsize=12, fontweight='bold')
                y_start -= 0.03

                # More compact table layout
                details_y = y_start
                row_height = 0.025  # Reduced row height for compactness

                details_mapping = [
                    ('Flowmeter Name:', flowmeter_details.get(
                        'flowmeter_name', 'N/A')),
                    ('Line Number:', flowmeter_details.get('line_number', 'N/A')),
                    ('Location:', flowmeter_details.get('location', 'N/A')),
                    ('Reason:', flowmeter_details.get('reason', 'N/A')),
                    ('LDS Number:', flowmeter_details.get('lds_number', 'N/A')),
                    ('Type:', flowmeter_details.get('type', 'N/A'))
                ]

                # Display details without background box
                for label, value in details_mapping:
                    # Compact spacing from border edges
                    ax.text(0.07, details_y, label, transform=ax.transAxes,
                            fontsize=9, fontweight='bold')
                    # Compact spacing between label and value
                    ax.text(0.35, details_y, str(value), transform=ax.transAxes,
                            fontsize=9)
                    details_y -= row_height

                y_start = details_y - 0.02

            # Test Results Summary - Two Column Layout
            if results_data and results_data.get('test_results'):
                # Left Column: Test Results Summary - No box
                card_height = 0.55  # Keep height for positioning

                # Header without box
                ax.text(0.05, y_start - 0.02, 'Test Results Summary', transform=ax.transAxes,
                        fontsize=12, fontweight='bold')

                test_results = results_data['test_results']
                y_pos = y_start - 0.06

                # Use the same complete target_tests list as the UI
                target_tests = [
                    # Test 1.1 - Range Checks
                    ('Test 1.1 - Digital Signal Range',
                     'Test 1.1 - Digital Range Check'),
                    ('Test 1.1 - Analog Signal Range',
                     'Test 1.1 - Analog Range Check'),
                    # Test 1.2 - Units Verification
                    ('Test 1.2 - Digital Signal Units',
                     'Test 1.2 - Digital Units Check'),
                    ('Test 1.2 - Analog Signal Units',
                     'Test 1.2 - Analog Units Check'),
                    # Test 1.3 - Quality Checks (stored as different keys in reliability_tests)
                    ('Digital Signal Quality Check',
                     'Test 1.3 - Digital Quality Check'),
                    ('Analog Signal Quality Check',
                     'Test 1.3 - Analog Quality Check'),
                    # Test 1.4 - Review File Quality
                    ('Test 1.4 - Review File Quality',
                     'Test 1.4 - Review Quality Check'),
                    # Test 2.1 - Time Differences
                    ('Test 2.1 - Digital Signal Time Diff',
                     'Test 2.1 - Digital Time Diff'),
                    ('Test 2.1 - Analog Signal Time Diff',
                     'Test 2.1 - Analog Time Diff'),
                    # Test 2.2 - FLAT Attribute
                    ('Test 2.2 - FLAT Attribute Check',
                     'Test 2.2 - FLAT Attribute'),
                    # Test 3.1 - Mean Squared Error
                    ('Test 3.1 - Mean Squared Error', 'Test 3.1 - MSE Analysis'),
                    # Test 3.2 - Signal-to-Noise Ratio
                    ('Test 3.2 - Digital Signal SNR',
                     'Test 3.2 - Digital SNR Analysis'),
                    ('Test 3.2 - Analog Signal SNR',
                     'Test 3.2 - Analog SNR Analysis'),
                    # Test 3.3 & 3.4 - Target Comparisons
                    ('Test 3.3 - Target vs Digital',
                     'Test 3.3 - Target vs Digital'),
                    ('Test 3.4 - Target vs Reference',
                     'Test 3.4 - Target vs Reference'),
                    # Test 3.5 - SNR Comparison
                    ('Test 3.5 - SNR Comparison', 'Test 3.5 - SNR Comparison'),
                    # Test 4.1 - Signal Stability
                    ('Test 4.1 - Digital Signal Stability',
                     'Test 4.1 - Digital Stability'),
                    ('Test 4.1 - Analog Signal Stability',
                     'Test 4.1 - Analog Stability')
                ]

                total_tests = 0
                passed_tests = 0

                for meter_name, meter_results in test_results.items():
                    # Meter header without background box
                    overall_status = meter_results.get(
                        'overall_status', 'unknown')
                    if overall_status == 'pass':
                        ax.text(0.05, y_pos, '●', transform=ax.transAxes,
                                fontsize=10, color='green', fontweight='bold')
                    else:
                        ax.text(0.05, y_pos, '●', transform=ax.transAxes,
                                fontsize=10, color='red', fontweight='bold')

                    ax.text(0.07, y_pos, f'Meter: {meter_name}', transform=ax.transAxes,
                            fontsize=9, fontweight='bold', color='black')
                    y_pos -= 0.025

                    # Collect all tests
                    all_tests = {}
                    for category_name, category_tests in meter_results.items():
                        if category_name in ['reliability_tests', 'timeliness_tests', 'accuracy_tests', 'robustness_tests']:
                            all_tests.update(category_tests)

                    # Add test results in compact format (like UI thumbs up/down)
                    for test_key, display_name in target_tests:
                        if test_key in all_tests:
                            total_tests += 1
                            test_result = all_tests[test_key]
                            test_status = test_result.get('status', 'unknown')

                            if test_status == 'pass':
                                passed_tests += 1
                                status_symbol = '✓'
                                status_color = 'green'
                            else:
                                status_symbol = '✗'
                                status_color = 'red'

                            # Compact format: icon + test name (adjusted positioning)
                            ax.text(0.09, y_pos, status_symbol, transform=ax.transAxes,
                                    fontsize=8, color=status_color, fontweight='bold')
                            ax.text(0.11, y_pos, display_name, transform=ax.transAxes,
                                    fontsize=8)

                            y_pos -= 0.018  # Reduced spacing between tests

                            if y_pos < y_start - card_height + 0.02:  # Stay within card bounds
                                break

                    if y_pos < y_start - card_height + 0.02:
                        break

                # Right Column: Show passed.png if all tests passed
                all_passed = total_tests > 0 and passed_tests == total_tests
                if all_passed:
                    try:
                        # Load the passed.png image from assets folder
                        passed_img_path = os.path.join(os.path.dirname(
                            os.path.dirname(__file__)), 'assets', 'passed.png')
                        if os.path.exists(passed_img_path):
                            # Load and display the passed.png image
                            import PIL.Image
                            passed_img = PIL.Image.open(passed_img_path)

                            # Create an axes for the image in the right column
                            img_ax = fig.add_axes(
                                [0.55, y_start - card_height, 0.35, card_height])
                            img_ax.imshow(passed_img)
                            img_ax.axis('off')
                        else:
                            # Fallback text if image not found
                            ax.text(0.72, y_start - card_height/2, 'ALL TESTS\nPASSED!',
                                    transform=ax.transAxes, fontsize=16, fontweight='bold',
                                    color='green', ha='center', va='center')
                    except Exception as e:
                        # Fallback text if image loading fails
                        ax.text(0.72, y_start - card_height/2, 'ALL TESTS\nPASSED!',
                                transform=ax.transAxes, fontsize=16, fontweight='bold',
                                color='green', ha='center', va='center')

            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

            # Page 2: Time Trends Plot
            if trends_fig and trends_fig.get('data'):
                try:
                    # Convert dict to plotly figure object
                    plotly_fig = go.Figure(trends_fig)
                    # Convert plotly figure to image
                    img_bytes = plotly_fig.to_image(
                        format="png", width=1200, height=800, scale=2)

                    # Create matplotlib figure to display the image with proper margins
                    fig, ax = plt.subplots(figsize=(11, 8.5))
                    ax.axis('off')
                    fig.subplots_adjust(top=0.9, bottom=0.1,
                                        left=0.1, right=0.9)

                    # Load and display image
                    import PIL.Image
                    img = PIL.Image.open(io.BytesIO(img_bytes))
                    ax.imshow(img)
                    ax.set_title('Time Trends - Target, Reference, RTU Analog & Digital Signals',
                                 fontsize=16, fontweight='bold', pad=20)

                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                except Exception as e:
                    print(f"Error adding trends plot: {e}")

            # Page 3: Distribution Plot
            if dist_fig and dist_fig.get('data'):
                try:
                    # Convert dict to plotly figure object
                    plotly_fig = go.Figure(dist_fig)
                    img_bytes = plotly_fig.to_image(
                        format="png", width=1200, height=800, scale=2)

                    fig, ax = plt.subplots(figsize=(11, 8.5))
                    ax.axis('off')
                    fig.subplots_adjust(top=0.9, bottom=0.1,
                                        left=0.1, right=0.9)

                    img = PIL.Image.open(io.BytesIO(img_bytes))
                    ax.imshow(img)
                    ax.set_title('Digital and Analog Signal Reporting Frequency Distribution',
                                 fontsize=16, fontweight='bold', pad=20)

                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                except Exception as e:
                    print(f"Error adding distribution plot: {e}")

            # Page 4: Stability Analysis Plot
            if stability_fig and stability_fig.get('data'):
                try:
                    # Convert dict to plotly figure object
                    plotly_fig = go.Figure(stability_fig)
                    img_bytes = plotly_fig.to_image(
                        format="png", width=1200, height=800, scale=2)

                    fig, ax = plt.subplots(figsize=(11, 8.5))
                    ax.axis('off')
                    fig.subplots_adjust(top=0.9, bottom=0.1,
                                        left=0.1, right=0.9)

                    img = PIL.Image.open(io.BytesIO(img_bytes))
                    ax.imshow(img)
                    ax.set_title('Signal Stability Analysis - Test 4.1',
                                 fontsize=16, fontweight='bold', pad=20)

                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                except Exception as e:
                    print(f"Error adding stability plot: {e}")

            # Page 5: Quality Metrics Dashboard - Create visual snapshot like the UI tab
            if results_data and results_data.get('test_results'):
                try:
                    fig, ax = plt.subplots(figsize=(11, 8.5))
                    ax.axis('off')
                    fig.subplots_adjust(top=0.9, bottom=0.1,
                                        left=0.1, right=0.9)

                    # Title
                    ax.set_title('Quality Metrics Dashboard',
                                 fontsize=18, fontweight='bold', pad=20)

                    test_results = results_data['test_results']
                    y_pos = 0.85

                    # Create cards layout similar to the Quality Metrics tab
                    for meter_name, meter_results in test_results.items():
                        # Meter header with icon (like in UI)
                        ax.text(0.05, y_pos, '⚡', transform=ax.transAxes,
                                fontsize=16, color='orange')
                        ax.text(0.08, y_pos, f'Meter: {meter_name}', transform=ax.transAxes,
                                fontsize=16, fontweight='bold', color='darkblue')
                        y_pos -= 0.08

                        # Extract metrics values
                        mse_value = "N/A"
                        snr_digital = "N/A"
                        snr_analog = "N/A"
                        snr_reference = "N/A"

                        if 'accuracy_tests' in meter_results:
                            accuracy_tests = meter_results['accuracy_tests']

                            # Get MSE from Test 3.1
                            mse_test = accuracy_tests.get(
                                'Test 3.1 - Mean Squared Error')
                            if mse_test and 'MSE:' in mse_test.get('value', ''):
                                try:
                                    mse_str = mse_test['value'].split(
                                        'MSE:')[1].split(',')[0].strip()
                                    mse_value = f"{float(mse_str):.4f}"
                                except:
                                    mse_value = "N/A"

                            # Get Digital SNR from Test 3.2
                            snr_dig_test = accuracy_tests.get(
                                'Test 3.2 - Digital Signal SNR')
                            if snr_dig_test and 'SNR:' in snr_dig_test.get('value', ''):
                                try:
                                    snr_str = snr_dig_test['value'].split('SNR:')[
                                        1].strip()
                                    if snr_str != 'N/A':
                                        snr_digital = f"{float(snr_str.split()[0]):.2f} dB"
                                except:
                                    snr_digital = "N/A"

                            # Get Analog SNR from Test 3.2
                            snr_anl_test = accuracy_tests.get(
                                'Test 3.2 - Analog Signal SNR')
                            if snr_anl_test and 'SNR:' in snr_anl_test.get('value', ''):
                                try:
                                    snr_str = snr_anl_test['value'].split('SNR:')[
                                        1].strip()
                                    if snr_str != 'N/A':
                                        snr_analog = f"{float(snr_str.split()[0]):.2f} dB"
                                except:
                                    snr_analog = "N/A"

                            # Get Reference SNR from Test 3.5
                            snr_comp_test = accuracy_tests.get(
                                'Test 3.5 - SNR Comparison')
                            if snr_comp_test and 'Ref:' in snr_comp_test.get('value', ''):
                                try:
                                    snr_str = snr_comp_test['value'].split('Ref:')[
                                        1].strip()
                                    if snr_str != 'N/A' and 'dB' in snr_str:
                                        ref_value = snr_str.replace(
                                            'dB', '').strip()
                                        snr_reference = f"{float(ref_value):.2f} dB"
                                except:
                                    snr_reference = "N/A"

                        # Create 4-card layout (similar to UI SimpleGrid cols=4)
                        card_width = 0.18
                        card_height = 0.15
                        card_spacing = 0.02
                        start_x = 0.05

                        # MSE Card
                        mse_rect = patches.Rectangle((start_x, y_pos - card_height), card_width, card_height,
                                                     linewidth=1, edgecolor='orange', facecolor='white',
                                                     alpha=0.9, transform=ax.transAxes)
                        ax.add_patch(mse_rect)
                        ax.text(start_x + card_width/2, y_pos - 0.03, 'MSE', transform=ax.transAxes,
                                fontsize=10, fontweight='bold', ha='center', color='orange')
                        ax.text(start_x + card_width/2, y_pos - 0.06, 'Mean Squared Error', transform=ax.transAxes,
                                fontsize=8, fontweight='bold', ha='center')
                        ax.text(start_x + card_width/2, y_pos - 0.10, mse_value, transform=ax.transAxes,
                                fontsize=12, fontweight='bold', ha='center', color='orange')
                        ax.text(start_x + card_width/2, y_pos - 0.13, 'Test 3.1 Result', transform=ax.transAxes,
                                fontsize=6, ha='center', color='gray')

                        # Digital SNR Card
                        dig_x = start_x + card_width + card_spacing
                        dig_rect = patches.Rectangle((dig_x, y_pos - card_height), card_width, card_height,
                                                     linewidth=1, edgecolor='blue', facecolor='white',
                                                     alpha=0.9, transform=ax.transAxes)
                        ax.add_patch(dig_rect)
                        ax.text(dig_x + card_width/2, y_pos - 0.03, 'DIG', transform=ax.transAxes,
                                fontsize=10, fontweight='bold', ha='center', color='blue')
                        ax.text(dig_x + card_width/2, y_pos - 0.06, 'Digital SNR', transform=ax.transAxes,
                                fontsize=8, fontweight='bold', ha='center')
                        ax.text(dig_x + card_width/2, y_pos - 0.10, snr_digital, transform=ax.transAxes,
                                fontsize=12, fontweight='bold', ha='center', color='blue')
                        ax.text(dig_x + card_width/2, y_pos - 0.13, 'Test 3.2 Result', transform=ax.transAxes,
                                fontsize=6, ha='center', color='gray')

                        # Analog SNR Card
                        anl_x = dig_x + card_width + card_spacing
                        anl_rect = patches.Rectangle((anl_x, y_pos - card_height), card_width, card_height,
                                                     linewidth=1, edgecolor='green', facecolor='white',
                                                     alpha=0.9, transform=ax.transAxes)
                        ax.add_patch(anl_rect)
                        ax.text(anl_x + card_width/2, y_pos - 0.03, 'ANL', transform=ax.transAxes,
                                fontsize=10, fontweight='bold', ha='center', color='green')
                        ax.text(anl_x + card_width/2, y_pos - 0.06, 'Analog SNR', transform=ax.transAxes,
                                fontsize=8, fontweight='bold', ha='center')
                        ax.text(anl_x + card_width/2, y_pos - 0.10, snr_analog, transform=ax.transAxes,
                                fontsize=12, fontweight='bold', ha='center', color='green')
                        ax.text(anl_x + card_width/2, y_pos - 0.13, 'Test 3.2 Result', transform=ax.transAxes,
                                fontsize=6, ha='center', color='gray')

                        # Reference SNR Card
                        ref_x = anl_x + card_width + card_spacing
                        ref_rect = patches.Rectangle((ref_x, y_pos - card_height), card_width, card_height,
                                                     linewidth=1, edgecolor='purple', facecolor='white',
                                                     alpha=0.9, transform=ax.transAxes)
                        ax.add_patch(ref_rect)
                        ax.text(ref_x + card_width/2, y_pos - 0.03, 'REF', transform=ax.transAxes,
                                fontsize=10, fontweight='bold', ha='center', color='purple')
                        ax.text(ref_x + card_width/2, y_pos - 0.06, 'Reference SNR', transform=ax.transAxes,
                                fontsize=8, fontweight='bold', ha='center')
                        ax.text(ref_x + card_width/2, y_pos - 0.10, snr_reference, transform=ax.transAxes,
                                fontsize=12, fontweight='bold', ha='center', color='purple')
                        ax.text(ref_x + card_width/2, y_pos - 0.13, 'Test 3.5 Result', transform=ax.transAxes,
                                fontsize=6, ha='center', color='gray')

                        y_pos -= card_height + 0.05

                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                except Exception as e:
                    print(f"Error adding quality metrics page: {e}")

        return [
            BootstrapIcon(icon="check-circle-fill", width=16, color="green"),
            " PDF Report Generated!"
        ]

    except Exception as e:
        return [
            BootstrapIcon(icon="exclamation-triangle-fill",
                          width=16, color="red"),
            f" Error: {str(e)}"
        ]
