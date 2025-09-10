"""
RTU to CSV Converter page component for DMC application.
Converts RTU files to CSV format with peek file filtering and parallel processing.
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
from services.rtu_to_csv_service import RtuFileService
import tempfile
from logging_config import get_logger

# Set up logging
logger = get_logger(__name__)


# RTU File Service Wrapper for handling background operations
class RtuServiceWrapper:
    def __init__(self):
        self._background_thread = None
        self._current_service = None
    
    def process_rtu_folder_async(self, 
                                rtu_folder_path: str,
                                peek_file: Dict,
                                start_datetime: str,
                                end_datetime: str,
                                frequency_minutes: float,
                                id_width: int,
                                max_workers: int = 4,
                                task_manager = None) -> str:
        """
        Start RTU processing in background thread using the new RtuFileService.
        
        Returns:
            Task ID for tracking the background operation
        """
        task_id = f"rtu_task_{int(datetime.now().timestamp())}"
        
        # Start background thread
        self._background_thread = threading.Thread(
            target=self._background_process_wrapper,
            args=(task_id, rtu_folder_path, peek_file, start_datetime, 
                  end_datetime, frequency_minutes, id_width, max_workers, task_manager),
            daemon=True
        )
        self._background_thread.start()
        
        return task_id
    
    def _background_process_wrapper(self, task_id: str, rtu_folder_path: str, 
                                   peek_file: Dict, start_datetime: str, end_datetime: str,
                                   frequency_minutes: float, id_width: int, max_workers: int,
                                   task_manager):
        """Wrapper to handle synchronous operations in background thread."""
        temp_peek_path = None
        try:
            # Update task manager progress if available
            if task_manager:
                task_manager.update_progress("Initializing RTU file processing...")
            
            # Create temporary peek file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_peek:
                if 'tags' in peek_file:
                    temp_peek.write('\n'.join(peek_file['tags']))
                elif 'content' in peek_file:
                    content = base64.b64decode(peek_file['content']).decode('utf-8')
                    temp_peek.write(content)
                temp_peek_path = temp_peek.name
            
            # Parse datetime strings
            def parse_datetime(dt_str):
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d'
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(dt_str, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Could not parse datetime: {dt_str}")
            
            start_dt = parse_datetime(start_datetime)
            end_dt = parse_datetime(end_datetime)
            
            if task_manager:
                task_manager.update_progress("Setting up RTU file service...")
            
            # Create RtuFileService instance
            self._current_service = RtuFileService(
                dir_path=rtu_folder_path,
                id_width=id_width,
                max_workers=max_workers
            )
            
            # Set up the service
            self._current_service.set_rtu_files()
            self._current_service.set_peek_file(temp_peek_path)
            
            if task_manager:
                task_manager.update_progress("Processing RTU files...")
            
            # Process the files (this is the time-consuming part)
            self._current_service.fetch_rtu_file_data(start_dt, end_dt)
            
            # Success result
            result = {
                'success': True,
                'task_id': task_id,
                'output_directory': rtu_folder_path,
                'message': 'RTU files converted successfully'
            }
            
            if task_manager:
                task_manager.complete_task(result)
                
        except Exception as e:
            # Error result
            logger.error(f"RTU processing failed: {str(e)}", exc_info=True)
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
        """Cancel the current RTU processing operation."""
        if self._current_service:
            self._current_service.cancel()

# Initialize the service wrapper
rtu_csv_service = RtuServiceWrapper()

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

# Create directory selector component for RTU files folder
rtu_directory_component, rtu_directory_ids = create_directory_selector(
    component_id='rtu-files-folder',
    title="RTU Files Folder (.dt files)",
    placeholder="Select folder containing .dt files...",
    browse_button_text="Browse Folder"
)


def create_rtu_to_csv_page():
    """Create the RTU to CSV Converter page layout."""

    return dmc.Container([
        # Data stores
        dcc.Store(id='peek-file-store', data={}),
        dcc.Store(id='rtu-processing-store', data={'status': 'idle'}),
        dcc.Store(id='background-task-store', data={'task_id': None, 'status': 'idle'}),
        dcc.Store(id=rtu_directory_ids['store'], data={'path': ''}),
        
        # Notification container for this page
        html.Div(id='rtu-csv-notifications'),
        
        # Interval component for polling background task progress
        dcc.Interval(
            id='rtu-csv-background-task-interval',
            interval=2000,  # Update every 2 seconds to reduce load
            n_intervals=0,
            disabled=True
        ),

        # Header Section
        dmc.Stack([
            dmc.Center([
                dmc.Stack([
                    dmc.Group([
                        dmc.Title("RTU to CSV Converter", order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
                            id="rtu-csv-help-modal-btn",
                            variant="light",
                            color="blue",
                            size="lg"
                        )
                    ], justify="center", align="center", gap="md"),
                    dmc.Text("Convert RTU files to CSV format with tag filtering and sequential processing",
                             c="dimmed", ta="center", size="md")
                ], gap="xs")
            ]),

            # Help Modal
            dmc.Modal(
                title="RTU to CSV Converter Help",
                id="rtu-csv-help-modal",
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
                                    dmc.ListItem("Folder containing RTU files (.dt extension)"),
                                    dmc.ListItem("Peek text file with one tag per line"),
                                    dmc.ListItem("drtu.exe available in system PATH"),
                                    dmc.ListItem("Read permissions to RTU folder"),
                                    dmc.ListItem("Write permissions to RTU folder for CSV output")
                                ], size="sm")
                            ])
                        ], span=6),
                        dmc.GridCol([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="lightbulb", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Process", fw=500)
                                ], gap="xs"),
                                dmc.List([
                                    dmc.ListItem("Select folder containing .dt files"),
                                    dmc.ListItem("Upload peek file with desired tags"),
                                    dmc.ListItem("Select date range for data extraction"),
                                    dmc.ListItem("Configure data frequency and ID width"),
                                    dmc.ListItem("Optionally enable data tabulation"),
                                    dmc.ListItem("Click 'Convert to CSV' to process all .dt files")
                                ], size="sm")
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
                        # RTU Files Folder Selection
                        rtu_directory_component,

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
                                        id='peek-file-upload',
                                        children=dmc.Stack([
                                            dmc.Center([
                                                BootstrapIcon(icon="file-text", width=36, height=36, color="var(--mantine-color-green-6)")
                                            ]),
                                            dmc.Text('Drop Peek File', size="sm", fw=500, ta="center"),
                                            dmc.Text('(one tag per line)', size="xs", c="dimmed", ta="center")
                                        ], gap="xs", p="lg", align="center"),
                                        style={
                                            'width': '100%',
                                            'height': '100px',
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
                                    id='peek-file-status',
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
                                            id="rtu-csv-start-datetime",
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
                                            id="rtu-csv-end-datetime",
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

                                # Data Frequency
                                dmc.Stack([
                                    dmc.Text("Data Frequency (minutes)", size="sm", fw=500),
                                    dmc.Group([
                                        dmc.Select(
                                            id="data-frequency-preset",
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
                                            id="data-frequency-custom",
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
                                ], gap="xs"),

                        # Max Workers
                        dmc.Stack([
                            dmc.Text("Max Workers", size="sm", fw=500),
                            dmc.NumberInput(
                                id="max-workers-input",
                                value=4,
                                min=1,
                                max=8,
                                step=1,
                                style={"width": "100%"},
                                size="md"
                            )
                        ], gap="xs"),

                        # ID Width
                        dmc.Stack([
                            dmc.Text("ID Width", size="sm", fw=500),
                            dmc.NumberInput(
                                id="id-width-input",
                                value=30,
                                min=1,
                                max=50,
                                step=1,
                                style={"width": "100%"},
                                size="md"
                            )
                        ], gap="xs")

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
                                    dmc.ListItem("All .dt files in the selected folder will be processed"),
                                    dmc.ListItem("CSV files will be merged into MergedDataFrame.csv"),
                                    dmc.ListItem("Processing uses parallel workers for better performance"),
                                    dmc.ListItem("Peek file filters which tags to extract"),
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
                                            "Write to CSV"
                                        ], id='convert-csv-btn', size="lg", disabled=True, variant="filled", 
                                          style={'minWidth': '160px'}),
                                        
                                        dmc.Button([
                                            BootstrapIcon(icon="x-circle", width=16),
                                            dmc.Space(w="sm"),
                                            "Cancel"
                                        ], id='cancel-csv-btn', size="lg", disabled=True, variant="outline", color="red",
                                          style={'minWidth': '120px'})
                                    ], gap="md", justify="center"),

                                    html.Div(
                                        id='csv-processing-alert',
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
    Output("rtu-csv-help-modal", "opened"),
    Input("rtu-csv-help-modal-btn", "n_clicks"),
    State("rtu-csv-help-modal", "opened"),
    prevent_initial_call=True,
)
def toggle_help_modal(n, opened):
    """Toggle the help modal."""
    return not opened


# Peek file upload callback
@callback(
    [Output('peek-file-store', 'data'),
     Output('peek-file-status', 'children')],
    [Input('peek-file-upload', 'contents')],
    [State('peek-file-upload', 'filename')],
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
        tags = [line.strip() for line in content_text.split('\n') if line.strip()]
        
        file_info = {
            'filename': filename,
            'content': content_string,
            'tags': tags,
            'tag_count': len(tags)
        }
        
        status_message = dmc.Alert(
            f"Loaded '{filename}' with {len(tags)} tags",
            color="green",
            variant="light",
            icon=BootstrapIcon(icon="check-circle")
        )
        
        return file_info, status_message
        
    except Exception as e:
        error_message = dmc.Alert(
            f"Error loading peek file: {str(e)}",
            color="red",
            variant="light",
            icon=BootstrapIcon(icon="exclamation-triangle")
        )
        return {}, error_message


# Data frequency custom input callback
@callback(
    Output('data-frequency-custom', 'disabled'),
    Input('data-frequency-preset', 'value')
)
def toggle_custom_frequency_input(preset_value):
    """Enable/disable custom frequency input based on preset selection."""
    return preset_value != "custom"


# Enable/disable convert button
@callback(
    Output('convert-csv-btn', 'disabled', allow_duplicate=True),
    [Input('peek-file-store', 'data'),
     Input(rtu_directory_ids['store'], 'data')],
    prevent_initial_call=True
)
def update_convert_button_state(peek_file, rtu_folder):
    """Enable convert button when all requirements are met."""
    has_peek_file = bool(peek_file.get('filename'))
    has_rtu_folder = bool(rtu_folder.get('path'))
    
    return not (has_peek_file and has_rtu_folder)


# Convert to CSV callback - immediate UI feedback
@callback(
    [Output('csv-processing-alert', 'children'),
     Output('rtu-processing-store', 'data'),
     Output('cancel-csv-btn', 'disabled', allow_duplicate=True),
     Output('rtu-csv-background-task-interval', 'disabled', allow_duplicate=True),
     Output('convert-csv-btn', 'disabled', allow_duplicate=True),
     Output('rtu-csv-notifications', 'children')],
    [Input('convert-csv-btn', 'n_clicks')],
    [State('peek-file-store', 'data'),
     State('rtu-csv-start-datetime', 'value'),
     State('rtu-csv-end-datetime', 'value'),
     State('data-frequency-preset', 'value'),
     State('data-frequency-custom', 'value'),
     State('id-width-input', 'value'),
     State('max-workers-input', 'value'),
     State(rtu_directory_ids['store'], 'data')],
    prevent_initial_call=True
)
def convert_rtu_to_csv(n_clicks, peek_file, start_datetime, end_datetime, 
                      frequency_preset, frequency_custom, id_width, max_workers, rtu_folder):
    """Process RTU files and convert to CSV format."""
    
    if not n_clicks:
        return "", {'status': 'idle'}, True, True, False, ""
    
    try:
        # Quick validation first - these should be instant
        if not peek_file.get('filename'):
            error_notification = dmc.Notification(
                title="Error",
                message="No peek file uploaded",
                color="red",
                autoClose=5000,
                action="show"
            )
            return "", {'status': 'error', 'error': 'No peek file'}, True, True, False, error_notification
            
        if not rtu_folder.get('path'):
            error_notification = dmc.Notification(
                title="Error", 
                message="No RTU folder selected",
                color="red",
                autoClose=5000,
                action="show"
            )
            return "", {'status': 'error', 'error': 'No RTU folder'}, True, True, False, error_notification
        
        # Show processing alert below buttons
        processing_alert = dmc.Alert([
            dmc.Group([
                BootstrapIcon(icon="clock", width=16),
                dmc.Text("RTU file processing started. This may take several minutes...", size="sm")
            ], gap="xs"),
            dmc.Space(h="xs"),
            dmc.Progress(value=100, animated=True, color="blue", size="sm")
        ], color="blue", variant="light")
        
        # Show processing notification IMMEDIATELY
        processing_notification = dmc.Notification(
            title="Processing Started",
            message="RTU file processing started. This may take several minutes.",
            color="blue",
            autoClose=False,
            action="show"
        )
        
        # Quick preparation of parameters - minimal processing
        frequency_minutes = float(frequency_custom) if frequency_preset == "custom" and frequency_custom else float(frequency_preset)
        
        # Simple string conversion - should be fast
        start_datetime_str = start_datetime.strftime('%Y-%m-%d %H:%M:%S') if not isinstance(start_datetime, str) else start_datetime
        end_datetime_str = end_datetime.strftime('%Y-%m-%d %H:%M:%S') if not isinstance(end_datetime, str) else end_datetime
        
        # Start background processing - everything heavy happens here
        task_id = rtu_csv_service.process_rtu_folder_async(
            rtu_folder_path=rtu_folder['path'],
            peek_file=peek_file,
            start_datetime=start_datetime_str,
            end_datetime=end_datetime_str,
            frequency_minutes=frequency_minutes,
            id_width=int(id_width),
            max_workers=int(max_workers),
            task_manager=background_task_manager
        )
        
        # Start the background task
        background_task_manager.start_task(task_id)
        
        # Return immediately with processing UI state
        return processing_alert, {'status': 'processing', 'task_id': task_id}, False, False, True, processing_notification
            
    except Exception as e:
        error_notification = dmc.Notification(
            title="Conversion Error",
            message=f"Error during conversion: {str(e)}",
            color="red",
            autoClose=5000,
            action="show"
        )
        return "", {'status': 'error', 'error': str(e)}, True, True, False, error_notification


# Cancel processing callback
@callback(
    [Output('csv-processing-alert', 'children', allow_duplicate=True),
     Output('rtu-processing-store', 'data', allow_duplicate=True),
     Output('cancel-csv-btn', 'disabled', allow_duplicate=True),
     Output('rtu-csv-background-task-interval', 'disabled', allow_duplicate=True),
     Output('convert-csv-btn', 'disabled', allow_duplicate=True),
     Output('rtu-csv-notifications', 'children', allow_duplicate=True)],
    [Input('cancel-csv-btn', 'n_clicks')],
    [State('rtu-processing-store', 'data')],
    prevent_initial_call=True
)
def cancel_rtu_processing(n_clicks, current_store):
    """Cancel the RTU processing operation."""
    if not n_clicks:
        raise PreventUpdate
    
    # Signal cancellation to the service
    rtu_csv_service.cancel_processing()
    
    # Reset background task manager
    background_task_manager.reset()
    
    # Create cancel notification
    cancel_notification = dmc.Notification(
        title="Processing Cancelled",
        message="RTU processing has been cancelled",
        color="orange",
        autoClose=3000,
        action="show"
    )
    
    return "", {'status': 'cancelled'}, True, True, False, cancel_notification


# RTU Directory selector callback
create_directory_selector_callback(
    store_ids=rtu_directory_ids
)


@callback(
    [Output('csv-processing-alert', 'children', allow_duplicate=True),
     Output('convert-csv-btn', 'disabled', allow_duplicate=True),
     Output('cancel-csv-btn', 'disabled', allow_duplicate=True),
     Output('rtu-csv-background-task-interval', 'disabled', allow_duplicate=True),
     Output('rtu-csv-notifications', 'children', allow_duplicate=True)],
    [Input('rtu-csv-background-task-interval', 'n_intervals')],
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
                    "RTU files converted successfully! Output saved as MergedDataFrame.csv in the RTU folder.",
                    color="green",
                    variant="light",
                    icon=BootstrapIcon(icon="check-circle", width=16)
                )
                success_notification = dmc.Notification(
                    title="Conversion Successful",
                    message="RTU files converted successfully! Output saved as MergedDataFrame.csv in the RTU folder.",
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
        
        return "", False, True, True, ""
    except Exception as e:
        error_notification = dmc.Notification(
            title="Task Monitoring Error",
            message=f"Error monitoring task: {str(e)}",
            color="red",
            autoClose=5000,
            action="show"
        )
        return "", False, True, True, error_notification
