"""
Fetch RTU Data service for retrieving historical RTU data.
Adapted from FetchArchiveService for RTU data requirements - accessing UNC paths and processing data files.
"""

import os
import logging
import re
import zipfile
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from .config_manager import get_config_manager

logger = logging.getLogger(__name__)


class FetchRtuDataService:
    """Service to fetch RTU data for pipeline lines from UNC paths."""

    def __init__(self):
        """Initialize the FetchRtuDataService."""
        # Get configuration manager
        self.config_manager = get_config_manager()
        
        # Load initial configuration
        self._load_config()

    def _load_config(self):
        """Load configuration settings from the config manager."""
        # Get RTU data configuration
        rtudata_config = self.config_manager.get_rtudata_config()
        
        # UNC path for RTU data backup repository
        self.rtudata_base_path = self.config_manager.get_rtudata_base_path()
        
        # Default output path
        self.default_output_path = self.config_manager.get_rtudata_default_output_path()
        
        # Timeout for large file operations
        self.timeout = self.config_manager.get_rtudata_timeout()
        
        logger.debug(f"RTU data configuration loaded - Base path: {self.rtudata_base_path}, Default output: {self.default_output_path}, Timeout: {self.timeout}s")

    def _check_unc_path_accessible(self) -> bool:
        """
        Check if the UNC RTU data path is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            return os.path.exists(self.rtudata_base_path) and os.path.isdir(self.rtudata_base_path)
        except Exception as e:
            logger.warning(f"Error checking UNC path accessibility: {e}")
            return False

    def check_default_output_path_exists(self) -> bool:
        """
        Check if the default output path exists.

        Returns:
            True if the default output path exists, False otherwise
        """
        try:
            return os.path.exists(self.default_output_path) and os.path.isdir(self.default_output_path)
        except Exception as e:
            logger.warning(f"Error checking default output path: {e}")
            return False

    def get_available_lines(self) -> Dict[str, Any]:
        """
        Get list of available pipeline lines from UNC folder structure.

        Returns:
            Dictionary containing success status and list of available lines
        """
        logger.info(f"Getting available lines from {self.rtudata_base_path}")

        try:
            # Check if UNC path is accessible
            if not self._check_unc_path_accessible():
                return {
                    'success': False,
                    'lines': [],
                    'message': f'UNC path not accessible: {self.rtudata_base_path}'
                }

            # Get all folder names in the UNC path - these represent line IDs
            lines = []
            for item in os.listdir(self.rtudata_base_path):
                item_path = os.path.join(self.rtudata_base_path, item)
                if os.path.isdir(item_path):
                    lines.append({
                        'label': item,  # Use folder name as-is (e.g., "l01", "l02")
                        'value': item
                    })

            # Sort lines by name for better UI
            lines.sort(key=lambda x: x['value'])

            logger.info(f"Successfully retrieved {len(lines)} pipeline lines")

            return {
                'success': True,
                'lines': lines,
                'message': f'Successfully retrieved {len(lines)} lines',
                'unc_path': self.rtudata_base_path
            }

        except Exception as e:
            logger.error(f"Error getting available lines: {e}")
            return {
                'success': False,
                'lines': [],
                'message': f'Error accessing UNC path: {str(e)}'
            }

    def _validate_date_inputs(self, start_date: str = None, end_date: str = None, single_date: str = None) -> Dict[str, Any]:
        """
        Validate date inputs for RTU data fetch.

        Args:
            start_date: Start date string (YYYY-MM-DD format) for date range
            end_date: End date string (YYYY-MM-DD format) for date range
            single_date: Single date string (YYYY-MM-DD format) for single date fetch

        Returns:
            Dictionary containing validation result and parsed dates
        """
        try:
            if single_date:
                # Single date mode - from specified date to current date
                parsed_start = datetime.strptime(single_date, '%Y-%m-%d').date()
                parsed_end = date.today()  # Always use current date as end
                
                if parsed_start > parsed_end:
                    return {
                        'success': False,
                        'message': 'Start date cannot be after current date'
                    }
                
                # Generate list of dates in range (from start date to today)
                dates = []
                current_date = parsed_start
                while current_date <= parsed_end:
                    dates.append(current_date)
                    # Move to next day
                    next_day = datetime.combine(current_date, datetime.min.time()) + \
                              timedelta(days=1)
                    current_date = next_day.date()
                
                return {
                    'success': True,
                    'mode': 'single',
                    'dates': dates,
                    'message': f'Single date mode: {parsed_start} to {parsed_end} ({len(dates)} days)'
                }
            elif start_date and end_date:
                # Date range mode
                parsed_start = datetime.strptime(start_date, '%Y-%m-%d').date()
                parsed_end = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if parsed_start > parsed_end:
                    return {
                        'success': False,
                        'message': 'Start date cannot be after end date'
                    }
                
                # Generate list of dates in range
                dates = []
                current_date = parsed_start
                while current_date <= parsed_end:
                    dates.append(current_date)
                    # Move to next day
                    next_day = datetime.combine(current_date, datetime.min.time()) + \
                              timedelta(days=1)
                    current_date = next_day.date()
                
                return {
                    'success': True,
                    'mode': 'range',
                    'dates': dates,
                    'message': f'Date range mode: {parsed_start} to {parsed_end} ({len(dates)} days)'
                }
            else:
                return {
                    'success': False,
                    'message': 'Either single_date or both start_date and end_date must be provided'
                }

        except ValueError as e:
            return {
                'success': False,
                'message': f'Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error validating dates: {str(e)}'
            }

    def _matches_wildcard_pattern(self, text: str, pattern: str) -> bool:
        """
        Check if text matches a wildcard pattern (case-insensitive).
        
        Args:
            text: The text to check
            pattern: Pattern with * wildcards (e.g., "LPP02WV*", "LPP02*SPSS*")
            
        Returns:
            True if text matches pattern, False otherwise
        """
        if not pattern:
            return True
            
        # Convert to lowercase for case-insensitive matching
        text = text.lower()
        pattern = pattern.lower()
        
        # Escape special regex characters except *
        pattern = re.escape(pattern).replace(r'\*', '.*')
        
        # Add anchors to match the entire string
        pattern = f'^{pattern}$'
        
        return bool(re.match(pattern, text))

    def _get_source_paths_for_dates(self, line_ids: List[str], dates: List[date], server_filter: str = None) -> Dict[str, Any]:
        """
        Get source paths for the specified lines and dates by finding zip files.

        Args:
            line_ids: List of pipeline line IDs
            dates: List of date objects
            server_filter: Optional server filter (e.g., "LPP02WVSPSS15")

        Returns:
            Dictionary containing source paths and validation results
        """
        source_files = []
        missing_dates = []

        try:
            for line_id in line_ids:
                line_path = os.path.join(self.rtudata_base_path, line_id)
                
                if not os.path.exists(line_path):
                    missing_dates.extend([f"Line {line_id} directory not found for date {d.strftime('%Y%m%d')}" for d in dates])
                    continue

                # Get all zip files in the line directory
                try:
                    all_files = os.listdir(line_path)
                    zip_files = [f for f in all_files if f.endswith('.zip')]
                except Exception as e:
                    logger.error(f"Error reading directory {line_path}: {e}")
                    missing_dates.extend([f"Line {line_id} directory read error for date {d.strftime('%Y%m%d')}" for d in dates])
                    continue

                for target_date in dates:
                    date_str = target_date.strftime('%Y%m%d')  # Format: 20250901
                    
                    # Find zip files matching pattern: lineId_YYYYMMDD_HHMM_ServerFilter.zip
                    # Example: l01_20250901_0700_LPP02WVSPSS15.zip
                    pattern = rf'^{re.escape(line_id)}_({re.escape(date_str)})_\d{{4}}_(.+)\.zip$'
                    
                    matching_files = []
                    for zip_file in zip_files:
                        match = re.match(pattern, zip_file)
                        if match:
                            extracted_date = match.group(1)
                            server_part = match.group(2)
                            
                            # Apply server filter if specified
                            if server_filter:
                                if self._matches_wildcard_pattern(server_part, server_filter):
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
                        filter_msg = f" (filter: {server_filter})" if server_filter else ""
                        missing_dates.append(f"Line {line_id}, Date {date_str}{filter_msg}")

            return {
                'success': True,
                'source_files': source_files,
                'missing_dates': missing_dates,
                'total_found': len(source_files),
                'total_missing': len(missing_dates)
            }

        except Exception as e:
            logger.error(f"Error getting source paths: {e}")
            return {
                'success': False,
                'message': f'Error getting source paths: {str(e)}',
                'source_files': [],
                'missing_dates': []
            }

    def fetch_rtu_data(self, line_ids: List[str], output_directory: str, start_date: str = None, 
                       end_date: str = None, single_date: str = None, server_filter: str = None) -> Dict[str, Any]:
        """
        Fetch RTU data for specified lines and date range.

        Args:
            line_ids: List of pipeline line IDs to fetch
            output_directory: Directory to copy RTU data files
            start_date: Start date string (YYYY-MM-DD) for date range
            end_date: End date string (YYYY-MM-DD) for date range  
            single_date: Single date string (YYYY-MM-DD) for single date fetch
            server_filter: Optional server filter (e.g., "LPP02WVSPSS15")

        Returns:
            Dictionary containing fetch operation results
        """
        logger.info(f"Starting RTU data fetch for lines: {line_ids}")

        try:
            # Validate inputs
            if not line_ids:
                return {
                    'success': False,
                    'message': 'No pipeline lines selected'
                }

            if not output_directory:
                return {
                    'success': False,
                    'message': 'Output directory not specified'
                }

            # Validate dates
            date_validation = self._validate_date_inputs(start_date, end_date, single_date)
            if not date_validation['success']:
                return date_validation

            dates = date_validation['dates']
            
            # Check if UNC path is accessible
            if not self._check_unc_path_accessible():
                return {
                    'success': False,
                    'message': f'UNC path not accessible: {self.rtudata_base_path}'
                }

            # Create output directory if it doesn't exist
            try:
                os.makedirs(output_directory, exist_ok=True)
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Cannot create output directory: {str(e)}'
                }

            # Get source paths for all lines and dates
            paths_result = self._get_source_paths_for_dates(line_ids, dates, server_filter)
            if not paths_result['success']:
                return paths_result

            source_files = paths_result['source_files']
            missing_dates = paths_result['missing_dates']

            if not source_files:
                return {
                    'success': False,
                    'message': 'No RTU data found for the specified lines and dates',
                    'missing_dates': missing_dates
                }

            # Process and extract files for each line
            extracted_files = {}  # Track extracted files by line_id
            extract_errors = []

            # Group files by line_id and deduplicate by date (keep first file per date)
            files_by_line = {}
            for file_info in source_files:
                line_id = file_info['line_id']
                date_str = file_info['date_str']
                
                if line_id not in files_by_line:
                    files_by_line[line_id] = {}
                
                # Only keep the first file for each date
                if date_str not in files_by_line[line_id]:
                    files_by_line[line_id][date_str] = file_info
                else:
                    # Log that we're skipping duplicate files
                    logger.info(f"Skipping duplicate file for {line_id} date {date_str}: {file_info['filename']} (keeping {files_by_line[line_id][date_str]['filename']})")

            for line_id, date_files in files_by_line.items():
                try:
                    # Create line output directory: output_dir/line_id/
                    line_output_dir = os.path.join(output_directory, line_id)
                    os.makedirs(line_output_dir, exist_ok=True)
                    
                    extracted_files[line_id] = []
                    
                    for date_str, file_info in date_files.items():
                        source_file_path = file_info['source_path']
                        filename = file_info['filename']
                        
                        try:
                            # Extract zip file
                            with zipfile.ZipFile(source_file_path, 'r') as zip_ref:
                                # Find .dt files in the zip
                                dt_files = [f for f in zip_ref.namelist() if f.endswith('.dt')]
                                
                                if not dt_files:
                                    extract_errors.append(f"No .dt file found in {filename}")
                                    continue
                                
                                # Process each .dt file (usually just one)
                                for dt_file in dt_files:
                                    # Extract the .dt file
                                    dt_content = zip_ref.read(dt_file)
                                    
                                    # Create new filename: line_date.dt (e.g., l05_20250804.dt)
                                    new_filename = f"{line_id}_{date_str}.dt"
                                    output_file_path = os.path.join(line_output_dir, new_filename)
                                    
                                    # Write the extracted content to the new file
                                    with open(output_file_path, 'wb') as output_file:
                                        output_file.write(dt_content)
                                    
                                    extracted_files[line_id].append({
                                        'original_zip': filename,
                                        'extracted_file': new_filename,
                                        'full_path': output_file_path,
                                        'date': date_str,
                                        'server': file_info['server']
                                    })
                                    
                                    logger.info(f"Extracted {dt_file} from {filename} as {new_filename}")
                        
                        except zipfile.BadZipFile:
                            extract_errors.append(f"Invalid zip file: {filename}")
                        except Exception as e:
                            extract_errors.append(f"Error extracting {filename}: {str(e)}")
                    
                    # Create a text file listing all extracted files for this line
                    if extracted_files[line_id]:
                        list_file_path = os.path.join(line_output_dir, f"{line_id}.txt")
                        with open(list_file_path, 'w') as list_file:
                            for file_info in extracted_files[line_id]:
                                list_file.write(f"{file_info['full_path']}\n")
                        
                        logger.info(f"Created file list: {list_file_path}")

                except Exception as e:
                    error_msg = f"Error processing line {line_id}: {str(e)}"
                    extract_errors.append(error_msg)
                    logger.error(error_msg)

            # Prepare result summary
            total_files_extracted = sum(len(files) for files in extracted_files.values())
            
            result = {
                'success': True,
                'message': f'RTU data extraction completed successfully',
                'summary': {
                    'lines_processed': len(extracted_files),
                    'total_files_extracted': total_files_extracted,
                    'output_directory': output_directory
                },
                'extracted_files': extracted_files,
                'extract_errors': extract_errors,
                'missing_dates': missing_dates
            }

            if extract_errors:
                result['message'] += f' (with {len(extract_errors)} errors)'

            logger.info(f"RTU data extraction completed: {total_files_extracted} files extracted")
            return result

        except Exception as e:
            logger.error(f"Error in fetch_rtu_data: {e}")
            return {
                'success': False,
                'message': f'Unexpected error during RTU data fetch: {str(e)}'
            }
