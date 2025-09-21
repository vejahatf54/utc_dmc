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
import tempfile
from logging_config import get_logger

# Set up logging
logger = get_logger(__name__)


# RTU File Service Wrapper for handling background operations using new RTU service
class RtuServiceWrapper:
    def __init__(self):
        self._background_thread = None
        self._current_service = None
        self._cancel_requested = False

    def process_rtu_folder_with_new_service_async(self,
                                                  processing_params: Dict,
                                                  task_manager=None) -> str:
        """
        Start RTU processing in background thread using the new RTUService.

        Args:
            processing_params: Dictionary containing all processing parameters
            task_manager: Optional task manager for progress updates

        Returns:
            Task ID for tracking the background operation
        """
        task_id = f"rtu_task_{int(datetime.now().timestamp())}"

        # Start background thread
        self._background_thread = threading.Thread(
            target=self._background_process_with_new_service,
            args=(task_id, processing_params, task_manager),
            daemon=True
        )
        self._background_thread.start()

        return task_id

    def _background_process_with_new_service(self, task_id: str, processing_params: Dict, task_manager):
        """Process RTU files using the new RTU service."""
        temp_tags_file = None
        try:
            from services.rtu_service import RTUService
            import glob

            # Reset cancel flag
            self._cancel_requested = False

            if task_manager:
                task_manager.update_progress(
                    "Initializing RTU processing with new service...")

            # Create RTU service instance
            self._current_service = RTUService()

            rtu_folder_path = processing_params['rtu_folder_path']
            start_datetime = processing_params['start_datetime']
            end_datetime = processing_params['end_datetime']
            peek_selection = processing_params['peek_selection']
            peek_file = processing_params['peek_file']
            csv_format = processing_params['csv_format']
            enable_sampling = processing_params['enable_sampling']
            sampling_interval = processing_params['sampling_interval']
            sampling_type = processing_params['sampling_type']

            # Get all .dt files in the folder
            dt_files = glob.glob(os.path.join(rtu_folder_path, "*.dt"))
            if not dt_files:
                raise ValueError("No .dt files found in the selected folder")

            if task_manager:
                task_manager.update_progress(
                    f"Found {len(dt_files)} .dt files to process...")

            # Handle tags file creation if needed
            if peek_selection == "SELECTED_PEEKS":
                # Create temporary tags file from peek file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_tags:
                    if 'tags' in peek_file:
                        temp_tags.write('\n'.join(peek_file['tags']))
                    elif 'content' in peek_file:
                        content = base64.b64decode(
                            peek_file['content']).decode('utf-8')
                        temp_tags.write(content)
                    temp_tags_file = temp_tags.name

            # Format datetime strings for the service
            def format_datetime_for_service(dt):
                if isinstance(dt, str):
                    # Try to parse and reformat
                    parsed = datetime.fromisoformat(dt.replace(
                        'Z', '+00:00')) if 'T' in dt else datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                    return parsed.strftime('%y/%m/%d %H:%M:%S')
                else:
                    return dt.strftime('%y/%m/%d %H:%M:%S')

            start_time_str = format_datetime_for_service(start_datetime)
            end_time_str = format_datetime_for_service(end_datetime)

            # Process each .dt file
            output_files = []
            total_files = len(dt_files)

            for i, dt_file in enumerate(dt_files, 1):
                if self._cancel_requested:
                    logger.info("Processing cancelled by user")
                    break

                # Update progress less frequently to reduce overhead
                if task_manager and (i == 1 or i % 5 == 0 or i == total_files):
                    task_manager.update_progress(
                        f"Processing file {i}/{total_files}: {os.path.basename(dt_file)}")

                # Generate output file name
                base_name = os.path.splitext(os.path.basename(dt_file))[0]
                output_file = os.path.join(
                    rtu_folder_path, f"{base_name}_export.csv")

                # Prepare service call parameters
                export_kwargs = {
                    'start_time': start_time_str,
                    'end_time': end_time_str
                }

                # Add tags file if using selected tags - ensure it's passed for both formats
                if peek_selection == "SELECTED_PEEKS" and temp_tags_file:
                    export_kwargs['tags_file'] = temp_tags_file

                # Add sampling parameters if enabled
                if enable_sampling:
                    export_kwargs['enable_sampling'] = True
                    export_kwargs['sample_interval'] = sampling_interval
                    export_kwargs['sample_mode'] = sampling_type

                # Call the appropriate export method based on CSV format
                try:
                    if csv_format == "flat-csv":
                        points_exported = self._current_service.export_csv_flat(
                            dt_file, output_file, **export_kwargs)
                    else:  # dataframe-csv
                        points_exported = self._current_service.export_csv_dataframe(
                            dt_file, output_file, **export_kwargs)

                    output_files.append(output_file)
                    # Reduce logging frequency for performance
                    if i == 1 or i % 10 == 0 or i == total_files:
                        logger.info(
                            f"Exported {points_exported} points from {dt_file} to {output_file}")

                except Exception as e:
                    logger.error(f"Failed to process {dt_file}: {str(e)}")
                    # Continue with next file instead of failing completely
                    continue

            if self._cancel_requested:
                result = {
                    'success': False,
                    'error': 'Processing was cancelled by user',
                    'task_id': task_id
                }
            elif output_files:
                # Merge all CSV files into one sorted by timestamp
                merged_file = None
                try:
                    if task_manager:
                        task_manager.update_progress(
                            "Merging CSV files by timestamp...")

                    merged_file = self._merge_csv_files(
                        output_files, rtu_folder_path)

                    # Success result with merged file
                    result = {
                        'success': True,
                        'task_id': task_id,
                        'output_directory': rtu_folder_path,
                        'output_files': output_files,
                        'merged_file': merged_file,
                        'files_processed': len(output_files),
                        'message': f'Successfully processed {len(output_files)} RTU files and merged into {os.path.basename(merged_file)}'
                    }
                except Exception as merge_error:
                    logger.error(
                        f"Failed to merge CSV files: {str(merge_error)}")
                    # Still report success for individual files, but note merge failure
                    result = {
                        'success': True,
                        'task_id': task_id,
                        'output_directory': rtu_folder_path,
                        'output_files': output_files,
                        'files_processed': len(output_files),
                        'merge_error': str(merge_error),
                        'message': f'Successfully processed {len(output_files)} RTU files (merge failed: {str(merge_error)})'
                    }
            else:
                result = {
                    'success': False,
                    'error': 'No files were successfully processed',
                    'task_id': task_id
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
            # Clean up temporary tags file
            if temp_tags_file and os.path.exists(temp_tags_file):
                try:
                    os.unlink(temp_tags_file)
                except:
                    pass  # Ignore cleanup errors

    def _merge_csv_files(self, csv_files, output_directory):
        """
        Merge multiple CSV files into one, sorted by timestamp.

        Args:
            csv_files: List of CSV file paths to merge
            output_directory: Directory where to save the merged file

        Returns:
            Path to the merged CSV file
        """
        import pandas as pd
        from datetime import datetime

        if not csv_files:
            raise ValueError("No CSV files to merge")

        logger.info(f"Merging {len(csv_files)} CSV files...")

        # Read all CSV files
        dataframes = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)

                # Add source file column
                df['source_file'] = os.path.basename(csv_file)

                dataframes.append(df)
                logger.debug(f"Read {len(df)} rows from {csv_file}")

            except Exception as e:
                logger.warning(f"Failed to read {csv_file}: {str(e)}")
                continue

        if not dataframes:
            raise ValueError("No valid CSV files could be read")

        # Combine all dataframes
        merged_df = pd.concat(dataframes, ignore_index=True)
        logger.info(
            f"Combined {len(merged_df)} total rows from {len(dataframes)} files")

        # Try to find timestamp column and sort by it
        timestamp_columns = []
        for col in merged_df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['time', 'date', 'timestamp', 'ts']):
                timestamp_columns.append(col)

        if timestamp_columns:
            # Use the first timestamp column found
            timestamp_col = timestamp_columns[0]
            logger.info(f"Sorting by timestamp column: {timestamp_col}")

            try:
                # Try to convert to datetime if it's not already
                if merged_df[timestamp_col].dtype == 'object':
                    merged_df[timestamp_col] = pd.to_datetime(
                        merged_df[timestamp_col], errors='coerce')

                # Sort by timestamp
                merged_df = merged_df.sort_values(
                    by=timestamp_col).reset_index(drop=True)
                logger.info("Successfully sorted by timestamp")

            except Exception as e:
                logger.warning(
                    f"Failed to sort by timestamp column {timestamp_col}: {str(e)}")
                # Continue without sorting
        else:
            logger.warning(
                "No timestamp column found, files will be merged without sorting")

        # Generate output filename
        merged_filename = f"MergedDataFrame_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        merged_filepath = os.path.join(output_directory, merged_filename)

        # Save merged file
        merged_df.to_csv(merged_filepath, index=False)
        logger.info(
            f"Saved merged CSV file: {merged_filepath} ({len(merged_df)} rows)")

        # Clean up individual CSV files after successful merge
        for csv_file in csv_files:
            try:
                if os.path.exists(csv_file):
                    os.remove(csv_file)
                    logger.debug(f"Deleted individual file: {csv_file}")
            except Exception as e:
                logger.warning(
                    f"Failed to delete individual file {csv_file}: {str(e)}")

        logger.info(
            f"Cleaned up {len(csv_files)} individual CSV files after merge")

        return merged_filepath

    def cancel_processing(self):
        """Cancel the current RTU processing operation."""
        self._cancel_requested = True
        logger.info("RTU processing cancellation requested")


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
                error_msg = result.get(
                    'error', 'Unknown error') if result else 'Processing failed'
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
        dcc.Store(id='background-task-store',
                  data={'task_id': None, 'status': 'idle'}),
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
                        dmc.Title("RTU to CSV Converter",
                                  order=2, ta="center"),
                        dmc.ActionIcon(
                            BootstrapIcon(
                                icon="question-circle", width=20, color="var(--mantine-color-blue-6)"),
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
                    dmc.Stack([
                        dmc.Grid([
                            dmc.GridCol([
                                dmc.Stack([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="info-circle", width=16),
                                        dmc.Space(w="sm"),
                                        dmc.Text("Requirements", fw=500)
                                    ], gap="xs"),
                                    dmc.List([
                                        dmc.ListItem(
                                            "Folder containing RTU files (.dt extension)"),
                                        dmc.ListItem(
                                            "Peek text file with one tag per line (optional)"),
                                        dmc.ListItem(
                                            "Read permissions to RTU folder"),
                                        dmc.ListItem(
                                            "Write permissions to RTU folder for CSV output")
                                    ], size="sm")
                                ])
                            ], span=6),
                            dmc.GridCol([
                                dmc.Stack([
                                    dmc.Group([
                                        BootstrapIcon(
                                            icon="lightbulb", width=16),
                                        dmc.Space(w="sm"),
                                        dmc.Text("Process", fw=500)
                                    ], gap="xs"),
                                    dmc.List([
                                        dmc.ListItem(
                                            "Select folder containing .dt files"),
                                        dmc.ListItem(
                                            "Choose tag selection: All Tags or Selected Tags"),
                                        dmc.ListItem(
                                            "Upload peek file if using Selected Tags"),
                                        dmc.ListItem(
                                            "Select date range for data extraction"),
                                        dmc.ListItem(
                                            "Choose CSV export format and sampling options"),
                                        dmc.ListItem(
                                            "Click 'Write to CSV' to process all .dt files")
                                    ], size="sm")
                                ])
                            ], span=6)
                        ]),

                        dmc.Divider(variant="dashed"),

                        dmc.Stack([
                            dmc.Group([
                                BootstrapIcon(icon="gear", width=16),
                                dmc.Space(w="sm"),
                                dmc.Text("Processing Details", fw=500)
                            ], gap="xs"),
                            dmc.List([
                                dmc.ListItem(
                                    "All .dt files in the selected folder will be processed sequentially"),
                                dmc.ListItem(
                                    "Output files are created in the same folder as input files with '_export.csv' suffix"),
                                dmc.ListItem(
                                    "Each .dt file creates one corresponding CSV file (e.g., 'data.dt' → 'data_export.csv')"),
                                dmc.ListItem(
                                    "After processing, all CSV files are automatically merged into 'MergedDataFrame_YYYYMMDD_HHMMSS.csv'"),
                                dmc.ListItem(
                                    "The merged file is sorted by timestamp column if found"),
                                dmc.ListItem(
                                    "Flat CSV creates one file per tag, DataFrame CSV creates structured data"),
                                dmc.ListItem(
                                    "Peek file filters specify which tags to extract (one tag per line)"),
                                dmc.ListItem(
                                    "Sampling options allow data interpolation at regular intervals"),
                                dmc.ListItem(
                                    "Processing runs in background and can be cancelled at any time")
                            ], size="sm")
                        ])
                    ], gap="md")
                ],
                opened=False,
                size="xl"
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

                        # Peek Selection Options
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="file-text", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("PEEK Selection",
                                             fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # Radio buttons for PEEK selection
                                dmc.Stack([
                                    dmc.Text("Tag Selection:",
                                             size="sm", fw=500),
                                    dmc.RadioGroup(
                                        children=dmc.Group([
                                            dmc.Radio(
                                                "All Tags", value="ALL_PEEKS"),
                                            dmc.Radio("Selected Tags",
                                                      value="SELECTED_PEEKS")
                                        ], gap="xl"),
                                        id="peek-selection-radio",
                                        value="ALL_PEEKS",
                                        size="sm"
                                    )
                                ], gap="xs"),

                                dmc.Space(h="sm"),

                                # Upload area for peek file - initially hidden
                                html.Div([
                                    html.Div([
                                        dcc.Upload(
                                            id='peek-file-upload',
                                            children=dmc.Stack([
                                                dmc.Center([
                                                    BootstrapIcon(
                                                        icon="file-text", width=36, height=36, color="var(--mantine-color-green-6)")
                                                ]),
                                                dmc.Text(
                                                    'Drop Peek File', size="sm", fw=500, ta="center"),
                                                dmc.Text(
                                                    '(one tag per line)', size="xs", c="dimmed", ta="center")
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
                                    ], id="peek-file-upload-container", style={'display': 'none'}),

                                    # Peek file status
                                    html.Div(
                                        id='peek-file-status',
                                        style={'minHeight': '20px'}
                                    ),
                                ]),

                            ], gap="sm", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                        # Date Range Selection
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(icon="calendar3", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("Date Range Selection",
                                             fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # Loading/Content container
                                html.Div([
                                    # Loading state
                                    html.Div([
                                        dmc.Center([
                                            dmc.Stack([
                                                dmc.Loader(
                                                    color="blue", size="sm"),
                                                dmc.Text(
                                                    "Setting up date range selection...", size="sm", c="dimmed", ta="center")
                                            ], gap="sm", align="center")
                                        ], style={"padding": "20px"})
                                    ], id="date-loading-container", style={'display': 'none'}),

                                    # Date inputs container
                                    html.Div([
                                        dmc.Group([
                                            dmc.Stack([
                                                dmc.Text(
                                                    "Start Date & Time", size="sm", fw=500),
                                                dmc.DateTimePicker(
                                                    id="rtu-csv-start-datetime",
                                                    value=datetime.now(),
                                                    style={"width": "100%"},
                                                    size="md",
                                                    clearable=False,
                                                    withSeconds=True,
                                                    valueFormat="YYYY/MM/DD HH:mm:ss"
                                                )
                                            ], gap="xs", style={"flex": 1}),

                                            dmc.Stack([
                                                dmc.Text(
                                                    "End Date & Time", size="sm", fw=500),
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
                                        ], gap="md", grow=True),

                                        # Status message for loaded dates
                                        html.Div(
                                            id='date-range-status',
                                            style={'minHeight': '20px'}
                                        )
                                    ], id="date-inputs-container")
                                ])
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
                                    dmc.Text("Processing Options",
                                             fw=500, size="md")
                                ], gap="xs"),

                                dmc.Divider(size="xs"),

                                # CSV Export Format
                                dmc.Stack([
                                    dmc.Text("CSV Export Format",
                                             size="sm", fw=500),
                                    dmc.RadioGroup(
                                        children=dmc.Group([
                                            dmc.Radio(
                                                "Flat CSV", value="flat-csv"),
                                            dmc.Radio("DataFrame CSV",
                                                      value="dataframe-csv")
                                        ], gap="xl"),
                                        id="csv-format-radio",
                                        value="flat-csv",
                                        size="sm"
                                    )
                                ], gap="xs"),

                                dmc.Space(h="md"),

                                # Sampling Options
                                dmc.Stack([
                                    dmc.Text("Data Sampling",
                                             size="sm", fw=500),
                                    dmc.Switch(
                                        id="enable-sampling-switch",
                                        label="Enable Sampling",
                                        size="sm",
                                        checked=False
                                    )
                                ], gap="xs"),

                                dmc.Space(h="sm"),

                                # Sampling Configuration - initially hidden
                                html.Div([
                                    dmc.Stack([
                                        # Sampling Interval
                                        dmc.Stack([
                                            dmc.Text(
                                                "Sampling Interval (seconds)", size="sm", fw=500),
                                            dmc.NumberInput(
                                                id="sampling-interval-input",
                                                value=60,
                                                min=1,
                                                max=3600,  # 1 hour max
                                                step=1,
                                                style={"width": "100%"},
                                                size="sm"
                                            )
                                        ], gap="xs"),

                                        dmc.Space(h="sm"),

                                        # Sampling Type
                                        dmc.Stack([
                                            dmc.Text("Sampling Type",
                                                     size="sm", fw=500),
                                            dmc.RadioGroup(
                                                children=dmc.Group([
                                                    dmc.Radio(
                                                        "Actual", value="actual"),
                                                    dmc.Radio(
                                                        "Interpolated", value="interpolated")
                                                ], gap="xl"),
                                                id="sampling-type-radio",
                                                value="actual",
                                                size="sm"
                                            )
                                        ], gap="xs"),
                                    ], gap="sm")
                                ], id="sampling-config-container", style={'display': 'none'}),

                            ], gap="md", p="sm")
                        ], shadow="sm", radius="md", withBorder=True),

                        # Conversion Section
                        dmc.Paper([
                            dmc.Stack([
                                dmc.Group([
                                    BootstrapIcon(
                                        icon="arrow-repeat", width=16),
                                    dmc.Space(w="sm"),
                                    dmc.Text("CSV Conversion",
                                             fw=500, size="md")
                                ], gap="xs", justify="center"),

                                dmc.Divider(size="xs"),

                                # Conversion button and status
                                dmc.Stack([
                                    dmc.Group([
                                        dmc.Button([
                                            BootstrapIcon(
                                                icon="download", width=16),
                                            dmc.Space(w="sm"),
                                            "Write to CSV"
                                        ], id='convert-csv-btn', size="lg", disabled=True, variant="filled",
                                            style={'minWidth': '160px'}),

                                        dmc.Button([
                                            BootstrapIcon(
                                                icon="x-circle", width=16),
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
        tags = [line.strip()
                for line in content_text.split('\n') if line.strip()]

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


# PEEK selection callback - show/hide file upload
@callback(
    Output('peek-file-upload-container', 'style'),
    Input('peek-selection-radio', 'value')
)
def toggle_peek_file_upload(selection):
    """Show/hide peek file upload based on selection."""
    if selection == "SELECTED_PEEKS":
        return {'display': 'block'}
    else:
        return {'display': 'none'}


# Sampling configuration callback - show/hide sampling options
@callback(
    Output('sampling-config-container', 'style'),
    Input('enable-sampling-switch', 'checked')
)
def toggle_sampling_config(enabled):
    """Show/hide sampling configuration based on switch."""
    if enabled:
        return {'display': 'block'}
    else:
        return {'display': 'none'}


# Set current datetime for date pickers when folder is selected
@callback(
    [Output('rtu-csv-start-datetime', 'value'),
     Output('rtu-csv-end-datetime', 'value'),
     Output('date-loading-container', 'style'),
     Output('date-inputs-container', 'style'),
     Output('date-range-status', 'children'),
     Output('rtu-csv-notifications', 'children', allow_duplicate=True)],
    [Input(rtu_directory_ids['store'], 'data')],
    prevent_initial_call=True
)
def set_default_datetime_values(rtu_folder):
    """Set current datetime for both start and end date pickers when folder is selected."""
    if not rtu_folder.get('path'):
        # Reset to default state when no folder selected
        return (datetime.now(), datetime.now(),
                {'display': 'none'}, {'display': 'block'}, "", "")

    try:
        import glob

        rtu_folder_path = rtu_folder['path']
        dt_files = glob.glob(os.path.join(rtu_folder_path, "*.dt"))

        if not dt_files:
            error_notification = dmc.Notification(
                title="No .dt Files Found",
                message="No .dt files found in the selected folder",
                color="orange",
                autoClose=5000,
                action="show"
            )
            return (no_update, no_update,
                    {'display': 'none'}, {'display': 'block'},
                    dmc.Alert("No .dt files found in the selected folder",
                              color="orange", variant="light"),
                    error_notification)

        # Set both start and end datetime to current datetime
        current_datetime = datetime.now()

        # Success - folder selected with .dt files
        status_message = dmc.Alert(
            f"Found {len(dt_files)} .dt files. Please select your desired date range.",
            color="blue",
            variant="light",
            icon=BootstrapIcon(icon="info-circle", width=16)
        )

        success_notification = dmc.Notification(
            title="Folder Selected",
            message=f"Found {len(dt_files)} .dt files. Please set your date range.",
            color="blue",
            autoClose=3000,
            action="show"
        )

        return (current_datetime, current_datetime,
                {'display': 'none'}, {'display': 'block'},
                status_message, success_notification)

    except Exception as e:
        error_notification = dmc.Notification(
            title="Error Processing Folder",
            message=f"Error processing folder: {str(e)}",
            color="red",
            autoClose=5000,
            action="show"
        )

        error_message = dmc.Alert(
            f"Error processing folder: {str(e)}",
            color="red",
            variant="light",
            icon=BootstrapIcon(icon="exclamation-triangle", width=16)
        )

        return (no_update, no_update,
                {'display': 'none'}, {'display': 'block'},
                error_message, error_notification)


# Clientside callback to show date inputs when folder selection changes
@callback(
    [Output('date-loading-container', 'style', allow_duplicate=True),
     Output('date-inputs-container', 'style', allow_duplicate=True)],
    [Input(rtu_directory_ids['store'], 'data')],
    prevent_initial_call=True
)
def show_date_inputs_immediately(rtu_folder):
    """Show date inputs immediately when folder selection changes (no loading needed)."""
    if rtu_folder.get('path'):
        # Hide loading, show inputs immediately
        return {'display': 'none'}, {'display': 'block'}
    else:
        # Show inputs, hide loading
        return {'display': 'none'}, {'display': 'block'}


# Enable/disable convert button
@callback(
    Output('convert-csv-btn', 'disabled', allow_duplicate=True),
    [Input('peek-file-store', 'data'),
     Input(rtu_directory_ids['store'], 'data'),
     Input('peek-selection-radio', 'value')],
    prevent_initial_call=True
)
def update_convert_button_state(peek_file, rtu_folder, peek_selection):
    """Enable convert button when all requirements are met."""
    has_rtu_folder = bool(rtu_folder.get('path'))

    # If "ALL_PEEKS" is selected, we don't need a peek file
    if peek_selection == "ALL_PEEKS":
        return not has_rtu_folder
    else:  # "SELECTED_PEEKS" selected, need both folder and peek file
        has_peek_file = bool(peek_file.get('filename'))
        return not (has_peek_file and has_rtu_folder)


# Convert to CSV callback - immediate UI feedback
@callback(
    [Output('csv-processing-alert', 'children'),
     Output('rtu-processing-store', 'data'),
     Output('cancel-csv-btn', 'disabled', allow_duplicate=True),
     Output('rtu-csv-background-task-interval',
            'disabled', allow_duplicate=True),
     Output('convert-csv-btn', 'disabled', allow_duplicate=True),
     Output('rtu-csv-notifications', 'children')],
    [Input('convert-csv-btn', 'n_clicks')],
    [State('peek-file-store', 'data'),
     State('rtu-csv-start-datetime', 'value'),
     State('rtu-csv-end-datetime', 'value'),
     State('peek-selection-radio', 'value'),
     State('csv-format-radio', 'value'),
     State('enable-sampling-switch', 'checked'),
     State('sampling-interval-input', 'value'),
     State('sampling-type-radio', 'value'),
     State(rtu_directory_ids['store'], 'data')],
    prevent_initial_call=True
)
def convert_rtu_to_csv(n_clicks, peek_file, start_datetime, end_datetime,
                       peek_selection, csv_format, enable_sampling, sampling_interval,
                       sampling_type, rtu_folder):
    """Process RTU files and convert to CSV format using the new RTU service."""

    if not n_clicks:
        return "", {'status': 'idle'}, True, True, False, ""

    try:
        # Quick validation first - these should be instant
        if not rtu_folder.get('path'):
            error_notification = dmc.Notification(
                title="Error",
                message="No RTU folder selected",
                color="red",
                autoClose=5000,
                action="show"
            )
            return "", {'status': 'error', 'error': 'No RTU folder'}, True, True, False, error_notification

        # Validate peek file if SELECTED_PEEKS is chosen
        if peek_selection == "SELECTED_PEEKS" and not peek_file.get('filename'):
            error_notification = dmc.Notification(
                title="Error",
                message="No peek file uploaded for selected PEEKS option",
                color="red",
                autoClose=5000,
                action="show"
            )
            return "", {'status': 'error', 'error': 'No peek file'}, True, True, False, error_notification

        # Show processing alert below buttons
        processing_alert = dmc.Alert([
            dmc.Group([
                BootstrapIcon(icon="clock", width=16),
                dmc.Text(
                    "RTU file processing started. This may take several minutes...", size="sm")
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

        # Prepare processing parameters
        processing_params = {
            'rtu_folder_path': rtu_folder['path'],
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'peek_selection': peek_selection,
            'peek_file': peek_file if peek_selection == "SELECTED_PEEKS" else None,
            'csv_format': csv_format,
            'enable_sampling': enable_sampling,
            'sampling_interval': sampling_interval if enable_sampling else None,
            'sampling_type': sampling_type if enable_sampling else None
        }

        # Start background processing - everything heavy happens here
        task_id = rtu_csv_service.process_rtu_folder_with_new_service_async(
            processing_params,
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
     Output('rtu-csv-background-task-interval',
            'disabled', allow_duplicate=True),
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
     Output('rtu-csv-background-task-interval',
            'disabled', allow_duplicate=True),
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
            # Convert disabled, Cancel enabled, Interval running
            return progress_alert, True, False, False, ""
        elif task_status['status'] == 'completed':
            # Reset the manager and return final status
            result = task_status['result']
            background_task_manager.reset()

            if result and result.get('success'):
                files_processed = result.get('files_processed', 0)
                output_directory = result.get('output_directory', '')
                merged_file = result.get('merged_file')
                merge_error = result.get('merge_error')

                # Create success message based on whether merging succeeded
                if merged_file:
                    merged_filename = os.path.basename(merged_file)
                    success_message = f"Successfully processed {files_processed} RTU files and merged into {merged_filename}!"
                    notification_message = f"Files processed and merged! Check: {merged_filename}"
                elif merge_error:
                    success_message = f"Successfully processed {files_processed} RTU files! (Merge failed: {merge_error})"
                    notification_message = f"Files processed but merge failed. Individual files in: {output_directory}"
                else:
                    success_message = f"Successfully processed {files_processed} RTU files! Individual CSV files created."
                    notification_message = f"Successfully processed {files_processed} RTU files! Check folder: {output_directory}"

                success_alert = dmc.Alert(
                    success_message,
                    color="green",
                    variant="light",
                    icon=BootstrapIcon(icon="check-circle", width=16)
                )
                success_notification = dmc.Notification(
                    title="Conversion Successful",
                    message=notification_message,
                    color="green",
                    autoClose=5000,
                    action="show"
                )
                # Convert enabled, Cancel disabled, Interval stopped
                return success_alert, False, True, True, success_notification
            else:
                error_msg = result.get(
                    'error', 'Unknown error') if result else 'Processing failed'
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
                # Convert enabled, Cancel disabled, Interval stopped
                return error_alert, False, True, True, error_notification

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
