"""
Review to CSV Converter page component for DMC application.
Converts Review files to CSV format with peek file filtering and parallel processing.
"""

import dash_mantine_components as dmc
from dash import html, Input, Output, State, callback, callback_context, dcc, ALL, no_update
from dash.exceptions import PreventUpdate
from components.bootstrap_icon import BootstrapIcon
import base64
import io
import pandas as pd
import os
import threading
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta, date
from components.directory_selector import create_directory_selector, create_directory_selector_callback
from services.review_to_csv_service import ReviewCsvService
import tempfile
from logging_config import get_logger

# Set up logging
logger = get_logger(__name__)


# Review File Service Wrapper for handling background operations
class ReviewServiceWrapper:
    def __init__(self):
        self._background_thread = None
        self._current_service = None
    
    def process_review_folder_async(self, 
                                   review_folder_path: str,
                                   peek_file: Dict,
                                   start_datetime: str,
                                   end_datetime: str,
                                   frequency_minutes: float,
                                   dump_all: bool,
                                   task_manager = None) -> str:
        """
        Start Review processing in background thread using ReviewCsvService.
        
        Returns:
            Task ID for tracking the background operation
        """
        task_id = f"review_task_{int(datetime.now().timestamp())}"
        
        # Start background thread
        self._background_thread = threading.Thread(
            target=self._background_process_wrapper,
            args=(task_id, review_folder_path, peek_file, start_datetime, 
                  end_datetime, frequency_minutes, dump_all, task_manager),
            daemon=True
        )
        self._background_thread.start()
        
        return task_id
    
    def _background_process_wrapper(self, task_id: str, review_folder_path: str, 
                                   peek_file: Dict, start_datetime: str, end_datetime: str,
                                   frequency_minutes: float, dump_all: bool, task_manager):
        """Wrapper to handle synchronous operations in background thread."""
        temp_peek_path = None
        try:
            # Update task manager progress if available
            if task_manager:
                task_manager.update_progress("Initializing Review file processing...")
            
            # Create temporary peek file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_peek:
                if 'tags' in peek_file:
                    temp_peek.write('\n'.join(peek_file['tags']))
                elif 'content' in peek_file:
                    content = base64.b64decode(peek_file['content']).decode('utf-8')
                    temp_peek.write(content)
                temp_peek_path = temp_peek.name
            
            # Parse datetime strings to the format expected by ReviewCsvService
            def parse_datetime_to_service_format(dt_str):
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d'
                ]
                for fmt in formats:
                    try:
                        dt = datetime.strptime(dt_str, fmt)
                        # Convert to yy/MM/dd_HH:mm:ss format
                        return dt.strftime('%y/%m/%d_%H:%M:%S')
                    except ValueError:
                        continue
                raise ValueError(f"Could not parse datetime: {dt_str}")
            
            start_formatted = parse_datetime_to_service_format(start_datetime)
            end_formatted = parse_datetime_to_service_format(end_datetime)
            
            if task_manager:
                task_manager.update_progress("Setting up Review file service...")
            
            # Create ReviewCsvService instance
            self._current_service = ReviewCsvService(
                folder_path=review_folder_path,
                start_time=start_formatted,
                end_time=end_formatted,
                dump_all=dump_all,
                freq=frequency_minutes if not dump_all else None,
                merged_file="MergedReviewData.csv"
            )
            
            # Set peek file
            self._current_service.set_peek_file(temp_peek_path)
            
            if task_manager:
                task_manager.update_progress("Processing Review files...")
            
            # Process the files (this is the time-consuming part)
            self._current_service.run()
            
            # Success result
            result = {
                'success': True,
                'task_id': task_id,
                'output_directory': review_folder_path,
                'message': 'Review files converted successfully'
            }
            
            if task_manager:
                task_manager.complete_task(result)
                
        except Exception as e:
            # Error result
            logger.error(f"Review processing failed: {str(e)}", exc_info=True)
            error_result = {
                'success': False,
                'error': f"Processing failed: {str(e)}",
                'task_id': task_id
            }
            
            if task_manager:
                task_manager.complete_task(error_result)
        finally:
            # Clear service reference
            self._current_service = None
            # Clean up temporary peek file
            if temp_peek_path and os.path.exists(temp_peek_path):
                try:
                    os.unlink(temp_peek_path)
                except:
                    pass  # Ignore cleanup errors
    
    def cancel_processing(self):
        """Cancel the current Review processing operation."""
        if self._current_service:
            self._current_service.cancel()

# Initialize the service wrapper
review_csv_service = ReviewServiceWrapper()

# Background task manager
class BackgroundTaskManager:
    def __init__(self):
        self.current_task_id = None
        self.task_status = 'idle'
        self.task_result = None
        self.progress_message = ""
        self.lock = threading.Lock()
    
    def start_task(self, task_id):
        with self.lock:
            self.current_task_id = task_id
            self.task_status = 'running'
            self.task_result = None
            self.progress_message = "Starting processing..."
    
    def update_progress(self, message):
        with self.lock:
            if self.task_status == 'running':  # Only update if still running
                self.progress_message = message
    
    def complete_task(self, result):
        with self.lock:
            self.task_result = result
            self.task_status = 'completed'
            if result and result.get('success'):
                self.progress_message = "Processing completed successfully"
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Processing failed'
                self.progress_message = f"Processing failed: {error_msg}"
    
    def get_status(self):
        with self.lock:
            return {
                'task_id': self.current_task_id,
                'status': self.task_status,
                'result': self.task_result,
                'progress': self.progress_message
            }
    
    def reset(self):
        with self.lock:
            self.current_task_id = None
            self.task_status = 'idle'
            self.task_result = None
            self.progress_message = ""

background_task_manager = BackgroundTaskManager()

# Create directory selector component for Review files folder
review_directory_component, review_directory_ids = create_directory_selector(
    component_id='review-files-folder',
    title="Review Files Folder (.review files)",
    placeholder="Select folder containing .review files...",
    browse_button_text="Browse Folder"
)


def create_review_to_csv_page():
    """Create the Review to CSV Converter page layout."""

    return dmc.Container([
        # Data stores
        dcc.Store(id='review-peek-file-store', data={}),
        dcc.Store(id='review-processing-store', data={'status': 'idle'}),
        dcc.Store(id=review_directory_ids['store'], data={'path': ''}),
        
        # Notification container for this page
        html.Div(id='review-csv-notifications'),
        
        # Interval component for polling background task progress
        dcc.Interval(
            id='review-csv-background-task-interval',
            interval=2000,  # Update every 2 seconds to reduce load
            n_intervals=0,
            disabled=True
        ),

        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("Review to CSV Converter", order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="review-csv-help-modal-btn",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Convert Review files to CSV format with peek filtering and automatic merging",
                             c="dimmed", ta="center", size="md")
                ], gap="xs")
            ]),

            # Help Modal
            dmc.Modal(
                title="Review to CSV Converter Help",
                id="review-csv-help-modal",
                children=[
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="info-circle", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Requirements", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem("Folder containing Review files (.review extension)"),
                                    dmc.ListItem("Peek text file with one peek per line"),
                                    dmc.ListItem("dreview.exe available in system PATH"),
                                    dmc.ListItem("Read permissions to Review folder"),
                                    dmc.ListItem("Write permissions to Review folder for CSV output")
                                ], size="sm")
                            ])
                        ], span=6),
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="lightbulb", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Peek File Format", fw=500)
                                ], gap="xs"),
                                dmc.Stack([
                                    dmc.Text("Peeks for defined variables using DEFINE in SPS:", size="sm", fw=500),
                                    dmc.Text("• One should not use :VAL attribute", size="xs", c="dimmed"),
                                    dmc.Text("• This is how SPS saves the dictionary of points in the rtudata file", size="xs", c="dimmed"),
                                    dmc.Text("• For anything other than defined variables, the attributes should be specified", size="xs", c="dimmed"),
                                    dmc.Space(h="xs"),
                                    dmc.Text("The peek file can contain one or more lines of SPS recognizable peeks separated by lines", size="sm")
                                ])
                            ])
                        ], span=6)
                    ])
                ],
                opened=False,
                size="lg"
            ),

            dmc.Space(h="md"),

            # Main Content Layout
            dmc.Grid([
                # Left offset column (1 column)
                dmc.GridCol([], span=1),

                # Left side - Folder Selection and Configuration (4 columns)
                dmc.GridCol([
                    dmc.Stack([
                        # Review Files Folder Selection
                        review_directory_component,

                        # Peek File Upload Section
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="file-text", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Peek File Upload", fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # Upload area for peek file
                                html.Div([
                                    dcc.Upload(
                                        id='review-peek-file-upload',
                                        children=dmc.Stack([
                                            dmc.Center([
                                                BootstrapIcon(icon="file-text", width=36, height=36, color="var(--mantine-color-green-6)")
                                            ]),
                                            dmc.Text('Drop Peek File', size="sm", fw=500, ta="center"),
                                            dmc.Text('(SPS recognizable peeks, one per line)', size="xs", c="dimmed", ta="center")
                                        ], gap="xs", p="lg", align="center"),
                                        style={
                                            'width': '100%',
                                            'height': '120px',
                                            'borderWidth': '2px',
                                            'borderStyle': 'dashed',
                                            'borderRadius': '8px',
                                            'cursor': 'pointer',
                                            'display': 'flex',
                                            'alignItems': 'center',
                                            'justifyContent': 'center'
                                        },
                                        multiple=False,
                                        accept='.txt,.peek'
                                    )
                                ]),

                                # Peek file status
                                html.Div(
                                    id='review-peek-file-status',
                                    style={'minHeight': '20px'}
                                ),

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                        # Date Range Selection
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="calendar3", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Date Range Selection", fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                dmc.Group([
                                    dmc.Stack([
                                        dmc.Text("Start Date & Time", size="sm", fw=500),
                                        dmc.DateTimePicker(
                                            id="review-csv-start-datetime",
                                            value=datetime.now() - timedelta(days=7),
                                            style={"width": "100%"},
                                            size="md",
                                            clearable=False,
                                            withSeconds=True,
                                            valueFormat="YYYY/MM/DD HH:mm:ss"
                                        )
                                    ], gap="xs", style={"flex": 1}),
                                    
                                    dmc.Stack([
                                        dmc.Text("End Date & Time", size="sm", fw=500),
                                        dmc.DateTimePicker(
                                            id="review-csv-end-datetime",
                                            value=datetime.now(),
                                            style={"width": "100%"},
                                            size="md",
                                            clearable=False,
                                            withSeconds=True,
                                            valueFormat="YYYY/MM/DD HH:mm:ss"
                                        )
                                    ], gap="xs", style={"flex": 1})
                                ], gap="md", grow=True)
                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                    ], gap="md")
                ], span=4),

                # Right side - Configuration and Processing (5 columns)
                dmc.GridCol([
                    dmc.Stack([
                        # Processing Options
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="gear", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Processing Options", fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # Dump All Data Switch
                                dmc.Stack([
                                    dmc.Group([
                                        dmc.Switch(
                                            id="review-dump-all-switch",
                                            checked=False,
                                            size="md",
                                            color="blue"
                                        ),
                                        dmc.Text("Dump All Data", size="sm", fw=500)
                                    ], gap="sm"),
                                    dmc.Text(
                                        "When enabled, extracts all available data without frequency filtering",
                                        size="xs", c="dimmed"
                                    )
                                ], gap="xs"),

                                # Data Frequency (conditionally displayed)
                                html.Div(
                                    id="review-frequency-section",
                                    children=[
                                        dmc.Stack([
                                            dmc.Text("Data Frequency (minutes)", size="sm", fw=500),
                                            dmc.Group([
                                                dmc.Select(
                                                    id="review-data-frequency-preset",
                                                    data=[
                                                        {"value": "0.0167", "label": "1 second"},
                                                        {"value": "0.0833", "label": "5 seconds"},
                                                        {"value": "0.1667", "label": "10 seconds"},
                                                        {"value": "0.5", "label": "30 seconds"},
                                                        {"value": "1", "label": "1 minute"},
                                                        {"value": "5", "label": "5 minutes"},
                                                        {"value": "10", "label": "10 minutes"},
                                                        {"value": "60", "label": "1 hour"},
                                                        {"value": "custom", "label": "Custom"}
                                                    ],
                                                    value="1",
                                                    style={"flex": "1"},
                                                    size="md"
                                                ),
                                                dmc.NumberInput(
                                                    id="review-data-frequency-custom",
                                                    placeholder="Custom minutes",
                                                    value=1,
                                                    min=0.001,
                                                    max=1440,  # 24 hours
                                                    step=0.1,
                                                    decimalScale=3,
                                                    style={"flex": "1"},
                                                    size="md",
                                                    disabled=True
                                                )
                                            ], gap="sm")
                                        ], gap="xs")
                                    ]
                                )

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                        # Processing Information
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="info-circle", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Processing Information", fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                dmc.List([
                                    dmc.ListItem("All .review files in the selected folder will be processed"),
                                    dmc.ListItem("CSV files will be automatically merged into MergedReviewData.csv"),
                                    dmc.ListItem("Processing uses parallel workers for better performance"),
                                    dmc.ListItem("Peek file filters which variables to extract"),
                                    dmc.ListItem("For DEFINE variables in SPS, don't use :VAL attribute"),
                                    dmc.ListItem("For other variables, attributes should be specified"),
                                    dmc.ListItem("You can cancel processing at any time")
                                ], size="sm")

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),
                        
                        # Conversion Section
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="arrow-repeat", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("CSV Conversion", fw=500, size="md")
                                ], gap="xs", justify="center"),

                                dmc.Divider(size="xs"),

                                # Conversion button and status
                                dmc.Stack([
                                    dmc.Group([
                                        dmc.Button([
                                            BootstrapIcon(icon="download", width=16),
                                            dmc.Space(w="sm"),
                                            "Convert to CSV"
                                        ], id='review-convert-csv-btn', size="lg", disabled=True, variant="filled", 
                                          style={'minWidth': '160px'}),
                                        
                                        dmc.Button([
                                            BootstrapIcon(icon="x-circle", width=16),
                                            dmc.Space(w="sm"),
                                            "Cancel"
                                        ], id='review-cancel-csv-btn', size="lg", disabled=True, variant="outline", color="red",
                                          style={'minWidth': '120px'})
                                    ], gap="md", justify="center"),

                                    html.Div(
                                        id='review-csv-processing-alert',
                                        style={'minHeight': '20px'}
                                    )
                                ], align="center", gap="sm")

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True)
                    ], gap="md")
                ], span=5),

                # Center spacer column (2 columns)
                dmc.GridCol([], span=2),

                # Right offset column (1 column)
                dmc.GridCol([], span=1),

            ])

        ], gap="md")
    ], fluid=True, p="sm")


# Help modal callback
@callback(
    Output("review-csv-help-modal", "opened"),
    Input("review-csv-help-modal-btn", "n_clicks"),
    State("review-csv-help-modal", "opened"),
    prevent_initial_call=True,
)
def toggle_help_modal(n, opened):
    """Toggle the help modal."""
    return not opened


# Peek file upload callback
@callback(
    [Output('review-peek-file-store', 'data'),
     Output('review-peek-file-status', 'children')],
    [Input('review-peek-file-upload', 'contents')],
    [State('review-peek-file-upload', 'filename')],
    prevent_initial_call=True
)
def handle_peek_file_upload(content, filename):
    """Handle peek file upload."""
    if not content or not filename:
        return {}, ""
    
    try:
        # Decode file content
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        
        # Parse as text file
        content_text = decoded.decode('utf-8')
        peeks = [line.strip() for line in content_text.split('\n') if line.strip()]
        
        file_info = {
            'filename': filename,
            'content': content_string,
            'tags': peeks,
            'tag_count': len(peeks)
        }
        
        status_alert = dmc.Alert(
            [
                dmc.Group([
                    BootstrapIcon(icon="check-circle", width=16),
                    dmc.Space(w="sm"),
                    dmc.Stack([
                        dmc.Text(f"File: {filename}", size="sm", fw=500),
                        dmc.Text(f"Peeks loaded: {len(peeks)}", size="xs", c="dimmed")
                    ], gap=0)
                ], gap="xs")
            ],
            title="Peek File Loaded",
            color="green",
            variant="light"
        )
        
        return file_info, status_alert
        
    except Exception as e:
        logger.error(f"Error parsing peek file: {e}")
        error_alert = dmc.Alert(
            f"Error reading file: {str(e)}",
            title="Upload Error",
            color="red",
            variant="light"
        )
        return {}, error_alert


# Custom frequency input handling
@callback(
    Output("review-data-frequency-custom", "disabled"),
    Input("review-data-frequency-preset", "value"),
    prevent_initial_call=True
)
def toggle_custom_frequency(preset_value):
    """Enable custom frequency input when 'custom' is selected."""
    return preset_value != "custom"


# Dump all switch callback to show/hide frequency section
@callback(
    Output("review-frequency-section", "style"),
    Input("review-dump-all-switch", "checked"),
    prevent_initial_call=True
)
def toggle_frequency_section(dump_all_checked):
    """Show/hide frequency section based on dump all switch."""
    if dump_all_checked:
        return {"display": "none"}
    else:
        return {"display": "block"}


# Convert button enable/disable callback
@callback(
    Output('review-convert-csv-btn', 'disabled'),
    [Input(review_directory_ids['store'], 'data'),
     Input('review-peek-file-store', 'data'),
     Input('review-processing-store', 'data')],
    prevent_initial_call=True
)
def update_convert_button_state(folder_data, peek_data, processing_data):
    """Enable convert button when all required inputs are available."""
    folder_path = folder_data.get('path', '')
    has_peek_file = bool(peek_data.get('tags', []))
    task_running = processing_data.get('status') in ['processing', 'running']
    
    # Enable if folder is selected, peek file is uploaded, and no task is running
    should_enable = bool(folder_path) and has_peek_file and not task_running
    return not should_enable


# Cancel button enable/disable callback
@callback(
    Output('review-cancel-csv-btn', 'disabled'),
    Input('review-processing-store', 'data'),
    prevent_initial_call=True
)
def update_cancel_button_state(processing_data):
    """Enable cancel button only when processing is running."""
    task_running = processing_data.get('status') in ['processing', 'running']
    return not task_running


# Convert to CSV callback
@callback(
    [Output('review-csv-processing-alert', 'children', allow_duplicate=True),
     Output('review-processing-store', 'data', allow_duplicate=True),
     Output('review-convert-csv-btn', 'disabled', allow_duplicate=True),
     Output('review-cancel-csv-btn', 'disabled', allow_duplicate=True),
     Output('review-csv-background-task-interval', 'disabled', allow_duplicate=True),
     Output('review-csv-notifications', 'children', allow_duplicate=True)],
    [Input('review-convert-csv-btn', 'n_clicks')],
    [State(review_directory_ids['store'], 'data'),
     State('review-peek-file-store', 'data'),
     State('review-csv-start-datetime', 'value'),
     State('review-csv-end-datetime', 'value'),
     State('review-data-frequency-preset', 'value'),
     State('review-data-frequency-custom', 'value'),
     State('review-dump-all-switch', 'checked')],
    prevent_initial_call=True
)
def start_review_csv_conversion(n_clicks, folder_data, peek_data, start_datetime, 
                               end_datetime, frequency_preset, frequency_custom, dump_all):
    """Start the Review to CSV conversion process."""
    if not n_clicks:
        raise PreventUpdate
    
    # Validate inputs
    folder_path = folder_data.get('path', '')
    if not folder_path:
        notification = dmc.Notification(
            title="Missing Folder",
            message="Please select a folder containing .review files",
            color="red",
            action="show"
        )
        return "", {'status': 'error'}, False, True, True, notification
    
    if not peek_data.get('tags', []):
        notification = dmc.Notification(
            title="Missing Peek File",
            message="Please upload a peek file with the variables to extract",
            color="red",
            action="show"
        )
        return "", {'status': 'error'}, False, True, True, notification
    
    try:
        # Show immediate processing alert with progress bar
        processing_alert = dmc.Alert([
            dmc.Group([
                BootstrapIcon(icon="clock", width=16),
                dmc.Text("Processing review files...", size="sm")
            ], gap="xs"),
            dmc.Space(h="xs"),
            dmc.Progress(value=100, animated=True, color="blue", size="sm")
        ], color="blue", variant="light")
        
        # Show processing notification IMMEDIATELY
        processing_notification = dmc.Notification(
            title="Processing Started",
            message="Review file processing started. This may take several minutes.",
            color="blue",
            autoClose=False,
            action="show"
        )
        
        # Quick preparation of parameters - minimal processing
        frequency_minutes = None
        if not dump_all:
            frequency_minutes = float(frequency_custom) if frequency_preset == "custom" and frequency_custom else float(frequency_preset)
        
        # Simple string conversion - should be fast
        start_datetime_str = start_datetime.strftime('%Y-%m-%d %H:%M:%S') if not isinstance(start_datetime, str) else start_datetime
        end_datetime_str = end_datetime.strftime('%Y-%m-%d %H:%M:%S') if not isinstance(end_datetime, str) else end_datetime
        
        # Start background processing - everything heavy happens here
        task_id = review_csv_service.process_review_folder_async(
            review_folder_path=folder_path,
            peek_file=peek_data,
            start_datetime=start_datetime_str,
            end_datetime=end_datetime_str,
            frequency_minutes=frequency_minutes,
            dump_all=dump_all,
            task_manager=background_task_manager
        )
        
        # Start the background task
        background_task_manager.start_task(task_id)
        
        # Return immediately with processing UI state
        return processing_alert, {'status': 'processing', 'task_id': task_id}, True, False, False, processing_notification
            
    except Exception as e:
        error_notification = dmc.Notification(
            title="Conversion Error",
            message=f"Error during conversion: {str(e)}",
            color="red",
            autoClose=5000,
            action="show"
        )
        return "", {'status': 'error', 'error': str(e)}, False, True, True, error_notification


# Cancel processing callback
@callback(
    [Output('review-csv-processing-alert', 'children', allow_duplicate=True),
     Output('review-processing-store', 'data', allow_duplicate=True),
     Output('review-cancel-csv-btn', 'disabled', allow_duplicate=True),
     Output('review-csv-background-task-interval', 'disabled', allow_duplicate=True),
     Output('review-convert-csv-btn', 'disabled', allow_duplicate=True),
     Output('review-csv-notifications', 'children', allow_duplicate=True)],
    [Input('review-cancel-csv-btn', 'n_clicks')],
    [State('review-processing-store', 'data')],
    prevent_initial_call=True
)
def cancel_review_processing(n_clicks, current_store):
    """Cancel the ongoing Review processing."""
    if not n_clicks:
        raise PreventUpdate
    
    # Signal cancellation to the service
    review_csv_service.cancel_processing()
    
    # Reset background task manager
    background_task_manager.reset()
    
    # Create cancel notification
    cancel_notification = dmc.Notification(
        title="Processing Cancelled",
        message="Review processing has been cancelled",
        color="orange",
        autoClose=3000,
        action="show"
    )
    
    return "", {'status': 'cancelled'}, True, True, False, cancel_notification


# Background task polling callback
@callback(
    [Output('review-csv-processing-alert', 'children', allow_duplicate=True),
     Output('review-convert-csv-btn', 'disabled', allow_duplicate=True),
     Output('review-cancel-csv-btn', 'disabled', allow_duplicate=True),
     Output('review-csv-background-task-interval', 'disabled', allow_duplicate=True),
     Output('review-csv-notifications', 'children', allow_duplicate=True)],
    [Input('review-csv-background-task-interval', 'n_intervals')],
    prevent_initial_call=True
)
def update_background_task_status(n_intervals):
    """Poll background task status and update UI."""
    try:
        task_status = background_task_manager.get_status()
        
        if task_status['status'] == 'idle':
            return "", False, True, True, ""
        elif task_status['status'] == 'running':
            progress_alert = dmc.Alert([
                dmc.Group([
                    BootstrapIcon(icon="clock", width=16),
                    dmc.Text(task_status['progress'], size="sm")
                ], gap="xs"),
                dmc.Space(h="xs"),
                dmc.Progress(value=100, animated=True, color="blue", size="sm")
            ], color="blue", variant="light")
            return progress_alert, True, False, False, ""  # Convert disabled, Cancel enabled, Interval running
        elif task_status['status'] == 'completed':
            # Reset the manager and return final status
            result = task_status['result']
            background_task_manager.reset()
            
            if result and result.get('success'):
                success_alert = dmc.Alert(
                    "Review files converted successfully! Output saved as MergedReviewData.csv in the Review folder.",
                    color="green",
                    variant="light",
                    icon=BootstrapIcon(icon="check-circle", width=16)
                )
                success_notification = dmc.Notification(
                    title="Conversion Successful",
                    message="Review files converted successfully! Output saved as MergedReviewData.csv in the Review folder.",
                    color="green",
                    autoClose=5000,
                    action="show"
                )
                return success_alert, False, True, True, success_notification  # Convert enabled, Cancel disabled, Interval stopped
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Processing failed'
                error_alert = dmc.Alert(
                    f"Conversion failed: {error_msg}",
                    color="red",
                    variant="light",
                    icon=BootstrapIcon(icon="exclamation-triangle", width=16)
                )
                error_notification = dmc.Notification(
                    title="Conversion Failed",
                    message=f"Conversion failed: {error_msg}",
                    color="red",
                    autoClose=5000,
                    action="show"
                )
                return error_alert, False, True, True, error_notification  # Convert enabled, Cancel disabled, Interval stopped
    except Exception as e:
        logger.error(f"Error polling background task: {e}")
        
    return "", False, True, True, ""


# Register directory selector callback for review folder
create_directory_selector_callback(
    store_ids=review_directory_ids,
    dialog_title="Select Review Files Folder"
)
