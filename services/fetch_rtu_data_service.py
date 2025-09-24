"""
Fetch RTU Data service implementation following SOLID principles and clean architecture.
Refactored version with dependency injection, proper error handling, and separation of concerns.
"""

import os
import re
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from core.interfaces import IFetchRtuDataService, IRtuLineProvider, IRtuDataProcessor, Result
from domain.rtu_models import (
    RtuDateRange, RtuLineSelection, RtuOutputDirectory, RtuServerFilter,
    RtuFetchResult, RtuFetchConstants
)
from services.config_manager import get_config_manager
from logging_config import get_logger

logger = get_logger(__name__)


class RtuLineProvider(IRtuLineProvider):
    """Provider for available RTU pipeline lines following SRP."""

    def __init__(self, config_manager=None):
        """Initialize with configuration manager dependency."""
        self._config_manager = config_manager or get_config_manager()
        self._base_path = self._config_manager.get_rtudata_base_path()

    def get_lines(self) -> Result[List[Dict[str, str]]]:
        """Get list of available pipeline lines from data source."""
        try:
            logger.info(f"Getting available RTU lines from {self._base_path}")

            # Check if data source is accessible
            if not self._is_data_source_accessible():
                return Result.fail(f'RTU data source not accessible: {self._base_path}')

            # Get all folder names in the data source - these represent line IDs
            lines = []
            for item in os.listdir(self._base_path):
                item_path = os.path.join(self._base_path, item)
                if os.path.isdir(item_path):
                    lines.append({
                        'label': item,  # Use folder name as-is (e.g., "l01", "l02")
                        'value': item
                    })

            # Sort lines by name for better UI
            lines.sort(key=lambda x: x['value'])

            logger.info(f"Successfully retrieved {len(lines)} RTU pipeline lines")
            return Result.ok(lines, f'Successfully retrieved {len(lines)} lines')

        except Exception as e:
            logger.error(f"Error getting available RTU lines: {e}")
            return Result.fail(f'Error accessing RTU data source: {str(e)}')

    def validate_line_exists(self, line_id: str) -> Result[bool]:
        """Validate that a specific line exists in the data source."""
        try:
            if not self._is_data_source_accessible():
                return Result.fail('RTU data source not accessible')

            line_path = os.path.join(self._base_path, line_id)
            exists = os.path.exists(line_path) and os.path.isdir(line_path)
            
            if exists:
                return Result.ok(True, f'Line {line_id} exists')
            else:
                return Result.ok(False, f'Line {line_id} does not exist')

        except Exception as e:
            logger.error(f"Error validating line existence for {line_id}: {e}")
            return Result.fail(f'Error validating line existence: {str(e)}')

    def _is_data_source_accessible(self) -> bool:
        """Check if the RTU data source is accessible."""
        try:
            return os.path.exists(self._base_path) and os.path.isdir(self._base_path)
        except Exception as e:
            logger.warning(f"Error checking RTU data source accessibility: {e}")
            return False


class RtuDataProcessor(IRtuDataProcessor):
    """Processor for RTU data files following SRP."""

    def __init__(self):
        """Initialize the RTU data processor."""
        self._progress_lock = Lock()
        self._processed_files = 0
        self._total_files = 0

    def process_zip_file(self, file_info: Dict[str, Any], output_dir: str) -> Result[Dict[str, Any]]:
        """Process a single RTU zip file."""
        try:
            source_file_path = file_info['source_path']
            filename = file_info['filename']
            date_str = file_info['date_str']
            line_id = file_info['line_id']
            server = file_info['server']

            logger.debug(f"Processing RTU zip file: {filename}")

            extracted_files = []

            # Extract zip file
            with zipfile.ZipFile(source_file_path, 'r') as zip_ref:
                # Find .dt files in the zip
                dt_files = [f for f in zip_ref.namelist() if f.endswith('.dt')]

                if not dt_files:
                    return Result.fail(f"No .dt file found in {filename}")

                # Process each .dt file (usually just one)
                for dt_file in dt_files:
                    # Extract the .dt file content
                    dt_content = zip_ref.read(dt_file)

                    # Create new filename: line_date.dt (e.g., l05_20250804.dt)
                    new_filename = f"{line_id}_{date_str}.dt"
                    output_file_path = os.path.join(output_dir, new_filename)

                    # Write the extracted content to the new file
                    with open(output_file_path, 'wb') as output_file:
                        output_file.write(dt_content)

                    extracted_files.append({
                        'original_zip': filename,
                        'extracted_file': new_filename,
                        'full_path': output_file_path,
                        'date': date_str,
                        'server': server
                    })

                    logger.debug(f"Extracted {dt_file} from {filename} as {new_filename}")

            return Result.ok({
                'success': True,
                'filename': filename,
                'extracted_files': extracted_files
            }, f"Successfully processed {filename}")

        except zipfile.BadZipFile:
            error_msg = f"Invalid zip file: {filename}"
            logger.error(error_msg)
            return Result.fail(error_msg)
        except Exception as e:
            error_msg = f"Error extracting {filename}: {str(e)}"
            logger.error(error_msg)
            return Result.fail(error_msg)

    def process_multiple_files(self, file_list: List[Dict[str, Any]], 
                               output_dir: str, max_workers: int = 4) -> Result[Dict[str, Any]]:
        """Process multiple RTU files in parallel."""
        try:
            if not file_list:
                return Result.fail("No files to process")

            logger.info(f"Starting parallel processing of {len(file_list)} RTU files with {max_workers} workers")

            # Initialize progress tracking
            self._total_files = len(file_list)
            self._processed_files = 0

            # Group files by line_id for organization
            files_by_line = {}
            line_output_dirs = {}

            for file_info in file_list:
                line_id = file_info['line_id']
                
                if line_id not in files_by_line:
                    files_by_line[line_id] = []
                    # Create line output directory
                    line_output_dir = os.path.join(output_dir, line_id)
                    os.makedirs(line_output_dir, exist_ok=True)
                    line_output_dirs[line_id] = line_output_dir

                files_by_line[line_id].append(file_info)

            # Process files in parallel
            extracted_files_by_line = {}
            extraction_errors = []

            # Determine actual number of workers (don't exceed available files)
            actual_workers = min(max_workers, len(file_list))

            with ThreadPoolExecutor(max_workers=actual_workers) as executor:
                # Submit all files for processing
                future_to_file = {}
                
                for line_id, line_files in files_by_line.items():
                    extracted_files_by_line[line_id] = []
                    line_output_dir = line_output_dirs[line_id]
                    
                    for file_info in line_files:
                        future = executor.submit(self.process_zip_file, file_info, line_output_dir)
                        future_to_file[future] = (file_info, line_id)

                # Collect results as they complete
                for future in as_completed(future_to_file):
                    file_info, line_id = future_to_file[future]
                    
                    try:
                        result = future.result()
                        
                        if result.success:
                            # Add extracted files to the line's list
                            extracted_files_by_line[line_id].extend(result.data['extracted_files'])
                        else:
                            # Add error to the list
                            extraction_errors.append(result.error)
                            
                    except Exception as e:
                        error_msg = f"Unexpected error processing {file_info['filename']}: {str(e)}"
                        extraction_errors.append(error_msg)
                        logger.error(error_msg)

                    # Update progress
                    with self._progress_lock:
                        self._processed_files += 1

            # Create file lists for each line
            for line_id, line_files in extracted_files_by_line.items():
                if line_files:
                    line_output_dir = line_output_dirs[line_id]
                    list_file_path = os.path.join(line_output_dir, f"{line_id}.txt")
                    
                    with open(list_file_path, 'w') as list_file:
                        for file_info in line_files:
                            list_file.write(f"{file_info['full_path']}\n")
                    
                    logger.info(f"Created file list: {list_file_path}")

            # Calculate summary
            total_files_extracted = sum(len(files) for files in extracted_files_by_line.values())
            lines_processed = len([line for line, files in extracted_files_by_line.items() if files])

            result_data = {
                'lines_processed': lines_processed,
                'total_files_extracted': total_files_extracted,
                'extracted_files': extracted_files_by_line,
                'extraction_errors': extraction_errors
            }

            message = f"Processed {total_files_extracted} files for {lines_processed} lines"
            if extraction_errors:
                message += f" (with {len(extraction_errors)} errors)"

            return Result.ok(result_data, message)

        except Exception as e:
            logger.error(f"Error in parallel RTU file processing: {e}")
            return Result.fail(f"Parallel processing error: {str(e)}")


class FetchRtuDataServiceV2(IFetchRtuDataService):
    """Refactored RTU data fetching service following SOLID principles."""

    def __init__(self, 
                 line_provider: IRtuLineProvider = None,
                 data_processor: IRtuDataProcessor = None,
                 config_manager=None):
        """Initialize service with dependency injection."""
        self._line_provider = line_provider or RtuLineProvider(config_manager)
        self._data_processor = data_processor or RtuDataProcessor()
        self._config_manager = config_manager or get_config_manager()
        
        # Load configuration
        self._base_path = self._config_manager.get_rtudata_base_path()
        self._timeout = self._config_manager.get_rtudata_timeout()
        
        logger.debug("FetchRtuDataServiceV2 initialized with dependency injection")

    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """Get list of available pipeline lines from data source."""
        return self._line_provider.get_lines()

    def validate_data_source_availability(self) -> Result[bool]:
        """Validate that the RTU data source is accessible."""
        try:
            accessible = os.path.exists(self._base_path) and os.path.isdir(self._base_path)
            
            if accessible:
                return Result.ok(True, "RTU data source is accessible")
            else:
                return Result.ok(False, f"RTU data source not accessible: {self._base_path}")
                
        except Exception as e:
            logger.error(f"Error validating RTU data source availability: {e}")
            return Result.fail(f"Error checking data source: {str(e)}")

    def fetch_rtu_data(self, line_selection: RtuLineSelection, date_range: RtuDateRange,
                       output_directory: RtuOutputDirectory, server_filter: RtuServerFilter = None,
                       max_parallel_workers: int = 4) -> Result[RtuFetchResult]:
        """Fetch RTU data for specified parameters using domain objects."""
        try:
            logger.info(f"Starting RTU data fetch for {line_selection.count} lines")
            
            # Validate data source availability
            availability_result = self.validate_data_source_availability()
            if not availability_result.data:
                return Result.fail(availability_result.message or "RTU data source not accessible")

            # Ensure output directory exists and is writable
            if not output_directory.is_writable:
                return Result.fail(f"Output directory is not writable: {output_directory.path_str}")

            # Get source files for the specified parameters
            source_files_result = self._get_source_files(line_selection, date_range, server_filter)
            if not source_files_result.success:
                return Result.fail(source_files_result.error)

            source_files = source_files_result.data['source_files']
            missing_dates = source_files_result.data['missing_dates']

            if not source_files:
                return Result.ok(
                    RtuFetchResult.create_failure('No RTU data found for the specified lines and dates'),
                    "No data found"
                )

            # Process files using the data processor
            processing_result = self._data_processor.process_multiple_files(
                source_files, output_directory.path_str, max_parallel_workers
            )

            if not processing_result.success:
                return Result.fail(processing_result.error)

            # Create result from processing output
            processing_data = processing_result.data
            
            fetch_result = RtuFetchResult.create_success(
                lines_processed=processing_data['lines_processed'],
                total_files_extracted=processing_data['total_files_extracted'],
                extraction_errors=processing_data['extraction_errors'],
                missing_dates=missing_dates
            )

            logger.info(f"RTU data fetch completed: {fetch_result.summary_text}")
            return Result.ok(fetch_result, "RTU data fetch completed successfully")

        except Exception as e:
            logger.error(f"Unexpected error in RTU data fetch: {e}")
            return Result.fail(f"Unexpected error during RTU data fetch: {str(e)}")

    def _get_source_files(self, line_selection: RtuLineSelection, 
                          date_range: RtuDateRange, server_filter: RtuServerFilter) -> Result[Dict[str, Any]]:
        """Get source files for the specified parameters."""
        try:
            source_files = []
            missing_dates = []

            for line_id in line_selection.line_ids:
                line_path = os.path.join(self._base_path, line_id)
                
                if not os.path.exists(line_path):
                    missing_dates.extend([
                        f"Line {line_id} directory not found for date {d.strftime('%Y%m%d')}" 
                        for d in date_range.date_list
                    ])
                    continue

                # Get all zip files in the line directory
                try:
                    all_files = os.listdir(line_path)
                    zip_files = [f for f in all_files if f.endswith('.zip')]
                except Exception as e:
                    logger.error(f"Error reading directory {line_path}: {e}")
                    missing_dates.extend([
                        f"Line {line_id} directory read error for date {d.strftime('%Y%m%d')}" 
                        for d in date_range.date_list
                    ])
                    continue

                # Process each date in the range
                for target_date in date_range.date_list:
                    date_str = target_date.strftime('%Y%m%d')  # Format: 20250901
                    
                    # Find zip files matching pattern: lineId_YYYYMMDD_HHMM_ServerName.zip
                    pattern = rf'^{re.escape(line_id)}_({re.escape(date_str)})_\d{{4}}_(.+)\.zip$'
                    
                    matching_files = []
                    for zip_file in zip_files:
                        match = re.match(pattern, zip_file)
                        if match:
                            extracted_date = match.group(1)
                            server_part = match.group(2)
                            
                            # Apply server filter if specified
                            if server_filter and not server_filter.is_empty:
                                if server_filter.matches(server_part):
                                    matching_files.append({
                                        'filename': zip_file,
                                        'date': extracted_date,
                                        'server': server_part,
                                        'full_path': os.path.join(line_path, zip_file)
                                    })
                            else:
                                matching_files.append({
                                    'filename': zip_file,
                                    'date': extracted_date,
                                    'server': server_part,
                                    'full_path': os.path.join(line_path, zip_file)
                                })
                    
                    if matching_files:
                        for file_info in matching_files:
                            source_files.append({
                                'line_id': line_id,
                                'date': target_date,
                                'date_str': date_str,
                                'filename': file_info['filename'],
                                'server': file_info['server'],
                                'source_path': file_info['full_path']
                            })
                    else:
                        filter_msg = f" (filter: {server_filter.pattern})" if server_filter and not server_filter.is_empty else ""
                        missing_dates.append(f"Line {line_id}, Date {date_str}{filter_msg}")

            return Result.ok({
                'source_files': source_files,
                'missing_dates': missing_dates,
                'total_found': len(source_files),
                'total_missing': len(missing_dates)
            }, f"Found {len(source_files)} source files")

        except Exception as e:
            logger.error(f"Error getting source files: {e}")
            return Result.fail(f"Error getting source files: {str(e)}")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information about the RTU data service."""
        try:
            system_info = RtuFetchConstants.get_system_info()
            system_info.update({
                'data_source_path': self._base_path,
                'timeout_seconds': self._timeout,
                'service_version': 'v2',
                'architecture': 'clean_architecture'
            })
            return Result.ok(system_info)
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return Result.fail(f"Error getting system info: {str(e)}")


class LegacyFetchRtuDataService:
    """Legacy wrapper service for backward compatibility."""

    def __init__(self, new_service: FetchRtuDataServiceV2 = None):
        """Initialize with new service dependency."""
        self._new_service = new_service or FetchRtuDataServiceV2()
        logger.debug("LegacyFetchRtuDataService initialized as wrapper")

    def get_available_lines(self) -> Dict[str, Any]:
        """Legacy method - returns old format."""
        result = self._new_service.get_available_lines()
        
        if result.success:
            return {
                'success': True,
                'lines': result.data,
                'message': result.message
            }
        else:
            return {
                'success': False,
                'lines': [],
                'message': result.error
            }

    def fetch_rtu_data(self, line_ids: List[str], output_directory: str, 
                       start_date: str = None, end_date: str = None, single_date: str = None,
                       server_filter: str = None, max_parallel_workers: int = 4,
                       progress_callback=None) -> Dict[str, Any]:
        """Legacy method - converts parameters and returns old format."""
        try:
            from domain.rtu_models import RtuLineSelection, RtuDateRange, RtuOutputDirectory, RtuServerFilter
            from datetime import datetime

            # Convert legacy parameters to domain objects
            line_selection = RtuLineSelection(line_ids)
            
            # Handle date parameters
            if single_date:
                start_date_obj = datetime.strptime(single_date, '%Y-%m-%d').date()
                date_range = RtuDateRange(start_date_obj)
            elif start_date and end_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                date_range = RtuDateRange(start_date_obj, end_date_obj)
            else:
                return {
                    'success': False,
                    'message': 'Either single_date or both start_date and end_date must be provided'
                }

            output_dir = RtuOutputDirectory(output_directory)
            server_filter_obj = RtuServerFilter(server_filter)

            # Call new service
            result = self._new_service.fetch_rtu_data(
                line_selection=line_selection,
                date_range=date_range,
                output_directory=output_dir,
                server_filter=server_filter_obj,
                max_parallel_workers=max_parallel_workers
            )

            if result.success:
                fetch_result = result.data
                return fetch_result.to_dict()
            else:
                return {
                    'success': False,
                    'message': result.error
                }

        except Exception as e:
            logger.error(f"Error in legacy RTU data fetch: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }