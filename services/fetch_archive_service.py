"""
Fetch Archive service for retrieving historical pipeline data.
Adapted from LDUTC for DMC requirements - accessing UNC paths and decompressing zip files.
"""

import os
import logging
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from .config_manager import get_config_manager

logger = logging.getLogger(__name__)


class FetchArchiveService:
    """Service to fetch archive data for pipeline lines from UNC paths."""

    def __init__(self):
        """Initialize the FetchArchiveService."""
        # Get configuration manager
        self.config_manager = get_config_manager()

        # Load initial configuration
        self._load_config()

    def _load_config(self):
        """Load configuration settings from the config manager."""
        # Get archive configuration
        archive_config = self.config_manager.get_archive_config()

        # UNC path for archive backup repository
        self.archive_base_path = self.config_manager.get_archive_base_path()

        # Timeout for large file operations
        self.timeout = self.config_manager.get_archive_timeout()

        logger.debug(
            f"Archive configuration loaded - Base path: {self.archive_base_path}, Timeout: {self.timeout}s")

    def _check_unc_path_accessible(self) -> bool:
        """
        Check if the UNC archive path is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            return os.path.exists(self.archive_base_path) and os.path.isdir(self.archive_base_path)
        except Exception as e:
            logger.warning(f"Error checking UNC path accessibility: {e}")
            return False

    def get_available_lines(self) -> Dict[str, Any]:
        """
        Get list of available pipeline lines from UNC folder structure.

        Returns:
            Dictionary containing success status and list of available lines
        """
        logger.info(f"Getting available lines from {self.archive_base_path}")

        try:
            # Check if UNC path is accessible
            if not self._check_unc_path_accessible():
                return {
                    'success': False,
                    'lines': [],
                    'message': f'UNC path not accessible: {self.archive_base_path}'
                }

            # Get all folder names in the UNC path - these represent line IDs
            lines = []
            for item in os.listdir(self.archive_base_path):
                item_path = os.path.join(self.archive_base_path, item)
                if os.path.isdir(item_path):
                    lines.append({
                        # Use folder name as-is (e.g., "l01", "l02")
                        'label': item,
                        'value': item
                    })

            # Sort lines by name for better UI
            lines.sort(key=lambda x: x['value'])

            logger.info(f"Successfully retrieved {len(lines)} pipeline lines")

            return {
                'success': True,
                'lines': lines,
                'message': f'Successfully retrieved {len(lines)} lines',
                'unc_path': self.archive_base_path
            }

        except Exception as e:
            logger.error(f"Error getting available lines: {e}")
            return {
                'success': False,
                'lines': [],
                'message': f'Error accessing UNC path: {str(e)}'
            }

    def fetch_archive_data(
        self,
        archive_date: datetime,
        line_ids: List[str],
        output_directory: str
    ) -> Dict[str, Any]:
        """
        Fetch archive data for specified date and pipeline lines.

        Args:
            archive_date: Date of archive data to fetch
            line_ids: List of pipeline line identifiers
            output_directory: Directory to save and decompress fetched archive files

        Returns:
            Dictionary containing operation results and file paths
        """
        logger.info(
            f"Starting archive fetch for {len(line_ids)} lines on {archive_date.strftime('%Y-%m-%d')}")

        # Check if UNC path is accessible
        if not self._check_unc_path_accessible():
            return {
                'success': False,
                'files': [],
                'failed_lines': [{'line_id': line_id, 'error': 'UNC path not accessible'} for line_id in line_ids],
                'message': f'UNC path not accessible: {self.archive_base_path}',
                'output_directory': output_directory
            }

        # Validate parameters first
        validation_result = self.validate_fetch_parameters(
            archive_date, line_ids, output_directory)
        if not validation_result['success']:
            return validation_result

        try:
            # Ensure output directory exists
            output_path = Path(output_directory)
            output_path.mkdir(parents=True, exist_ok=True)

            fetched_files = []
            failed_fetches = []

            # Fetch data for each line
            for line_id in line_ids:
                try:
                    file_result = self._fetch_line_archive(
                        archive_date, line_id, output_path)

                    if file_result['success']:
                        fetched_files.extend(file_result['files'])
                        logger.info(
                            f"Successfully fetched and decompressed archive for line {line_id}")
                    else:
                        failed_fetches.append({
                            'line_id': line_id,
                            'error': file_result['message']
                        })
                        logger.error(
                            f"Failed to fetch archive for line {line_id}: {file_result['message']}")

                except Exception as e:
                    failed_fetches.append({
                        'line_id': line_id,
                        'error': str(e)
                    })
                    logger.error(
                        f"Exception fetching archive for line {line_id}: {e}")

            # Prepare result
            success = len(fetched_files) > 0
            message = self._create_result_message(
                fetched_files, failed_fetches)

            result = {
                'success': success,
                'files': fetched_files,
                'failed_lines': failed_fetches,
                'message': message,
                'output_directory': str(output_path),
                'fetch_date': archive_date.isoformat(),
                'requested_lines': line_ids
            }

            logger.info(
                f"Archive fetch completed: {len(fetched_files)} files processed, {len(failed_fetches)} failed")
            return result

        except Exception as e:
            logger.error(f"Unexpected error during archive fetch: {e}")
            return {
                'success': False,
                'files': [],
                'failed_lines': [],
                'message': f'Archive fetch failed: {str(e)}',
                'output_directory': output_directory
            }

    def validate_fetch_parameters(
        self,
        archive_date: datetime,
        line_ids: List[str],
        output_directory: str
    ) -> Dict[str, Any]:
        """
        Validate parameters for fetch operation.

        Args:
            archive_date: Date of archive data to fetch
            line_ids: List of pipeline line identifiers
            output_directory: Directory to save fetched archive files

        Returns:
            Dictionary containing validation results
        """
        try:
            errors = []

            # Validate date
            if not archive_date:
                errors.append("Archive date is required")
            elif archive_date > datetime.now():
                errors.append("Archive date cannot be in the future")

            # Validate line IDs
            if not line_ids or len(line_ids) == 0:
                errors.append("At least one pipeline line must be selected")

            # Validate output directory
            if not output_directory or output_directory.strip() == "":
                errors.append("Output directory is required")
            else:
                try:
                    output_path = Path(output_directory)
                    # Try to create the directory to test permissions
                    output_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Invalid output directory: {str(e)}")

            if errors:
                return {
                    'success': False,
                    'message': '; '.join(errors),
                    'errors': errors
                }

            return {
                'success': True,
                'message': 'Parameters validated successfully'
            }

        except Exception as e:
            logger.error(f"Error validating fetch parameters: {e}")
            return {
                'success': False,
                'message': f'Validation error: {str(e)}'
            }

    def _fetch_line_archive(
        self,
        archive_date: datetime,
        line_id: str,
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Fetch and decompress archive data for a single pipeline line from UNC repository.

        Args:
            archive_date: Date of archive data to fetch
            line_id: Pipeline line identifier
            output_path: Path to save and decompress archive files

        Returns:
            Dictionary containing fetch results for the line
        """
        try:
            # Build path to line folder in UNC repository
            # Structure: \\server\path\line_id\YYYYMMDD\*.zip
            date_folder = archive_date.strftime('%Y%m%d')  # Format: 20231226
            line_archive_path = os.path.join(
                self.archive_base_path, line_id, date_folder)

            logger.debug(f"Looking for archive folder: {line_archive_path}")

            # Check if line archive folder exists
            if not os.path.exists(line_archive_path) or not os.path.isdir(line_archive_path):
                date_str = archive_date.strftime('%Y-%m-%d')
                return {
                    'success': False,
                    'files': [],
                    'message': f'No archive data found for {line_id} on {date_str}'
                }

            # Find all zip files in the archive folder
            zip_files = []
            for file in os.listdir(line_archive_path):
                if file.lower().endswith('.zip'):
                    zip_files.append(os.path.join(line_archive_path, file))

            if not zip_files:
                date_str = archive_date.strftime('%Y-%m-%d')
                return {
                    'success': False,
                    'files': [],
                    'message': f'No archive files found for {line_id} on {date_str}'
                }

            # Create line-specific output directory
            line_output_path = output_path / f"{line_id}_{date_folder}"
            line_output_path.mkdir(parents=True, exist_ok=True)

            extracted_files = []
            total_extracted = 0

            # Extract each zip file
            for zip_file_path in zip_files:
                try:
                    zip_filename = os.path.basename(zip_file_path)
                    # Get zip name without extension for renaming
                    zip_name_base = os.path.splitext(zip_filename)[0]

                    logger.info(
                        f"Extracting {zip_filename} to {line_output_path}")

                    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                        # Extract each file and rename it to match the zip file name
                        for member in zip_ref.namelist():
                            # Skip directories
                            if member.endswith('/'):
                                continue

                            # Extract the file to memory first
                            file_data = zip_ref.read(member)

                            # Get the original file extension
                            original_name = os.path.basename(member)
                            _, original_ext = os.path.splitext(original_name)

                            # Create new filename: zip_name + original_extension
                            new_filename = f"{zip_name_base}{original_ext}"
                            new_file_path = line_output_path / new_filename

                            # Write the file with the new name
                            with open(new_file_path, 'wb') as f:
                                f.write(file_data)

                            # Record the extracted file
                            extracted_files.append({
                                'original_zip': zip_filename,
                                'original_filename': original_name,
                                'extracted_file': str(new_file_path),
                                'filename': new_filename,
                                'size_bytes': new_file_path.stat().st_size
                            })
                            total_extracted += 1

                            logger.debug(
                                f"Renamed {original_name} to {new_filename}")

                    logger.info(
                        f"Successfully extracted and renamed files from {zip_filename}")

                except Exception as e:
                    logger.error(f"Error extracting {zip_file_path}: {e}")
                    # Continue with other files even if one fails
                    continue

            if extracted_files:
                logger.info(
                    f"Successfully extracted {total_extracted} files from {len(zip_files)} zip files for line {line_id}")

                return {
                    'success': True,
                    'files': extracted_files,
                    'message': f'Successfully extracted {total_extracted} files from {len(zip_files)} zip archives',
                    'total_zip_files': len(zip_files),
                    'total_extracted_files': total_extracted,
                    'output_directory': str(line_output_path)
                }
            else:
                return {
                    'success': False,
                    'files': [],
                    'message': f'Failed to extract any files from {len(zip_files)} zip archives'
                }

        except FileNotFoundError as e:
            logger.error(f"Archive repository access error for {line_id}: {e}")
            return {
                'success': False,
                'files': [],
                'message': f'Archive repository not accessible: {str(e)}'
            }
        except PermissionError as e:
            logger.error(
                f"Permission error accessing archive for {line_id}: {e}")
            return {
                'success': False,
                'files': [],
                'message': f'Permission denied accessing archive files: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error fetching archive for {line_id}: {e}")
            return {
                'success': False,
                'files': [],
                'message': f'Error fetching archive: {str(e)}'
            }

    def _create_result_message(self, fetched_files: List[Dict], failed_fetches: List[Dict]) -> str:
        """Create a summary message for fetch operation results."""
        success_count = len(fetched_files)
        failure_count = len(failed_fetches)

        if success_count == 0 and failure_count == 0:
            return "No files were processed"
        elif success_count > 0 and failure_count == 0:
            return f"Successfully extracted {success_count} archive file(s)"
        elif success_count == 0 and failure_count > 0:
            # If there's only one failure, show the specific error message
            if failure_count == 1:
                error_message = failed_fetches[0]['error']
                # Check if it's a "no files found" type error
                if "No archive" in error_message or "not found" in error_message:
                    return f"{error_message}. Try again with a different date."
                else:
                    return error_message
            else:
                return f"Failed to extract any archive files ({failure_count} failures)"
        else:
            return f"Extracted {success_count} archive file(s), {failure_count} failed"
