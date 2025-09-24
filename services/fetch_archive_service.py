"""
Refactored Fetch Archive service following SOLID principles.
Uses dependency injection and separates concerns for better testability and maintainability.
"""

from typing import List, Dict, Any
from datetime import datetime
from core.interfaces import IFetchArchiveService, IArchiveValidator, IArchivePathService, IArchiveFileExtractor, Result
from domain.archive_models import (
    ArchiveDate, PipelineLine, OutputDirectory, FetchArchiveRequest, 
    FetchArchiveResult, ArchiveFileInfo, ArchiveConversionConstants
)
from logging_config import get_logger

logger = get_logger(__name__)


class FetchArchiveService(IFetchArchiveService):
    """
    Refactored fetch archive service using dependency injection.
    Follows SOLID principles with separated concerns.
    """

    def __init__(self, 
                 validator: IArchiveValidator,
                 path_service: IArchivePathService,
                 file_extractor: IArchiveFileExtractor):
        """Initialize service with dependency injection."""
        self._validator = validator
        self._path_service = path_service
        self._file_extractor = file_extractor
        logger.debug("FetchArchiveService initialized with dependency injection")

    def fetch_archive_data(self, archive_date: Any, line_ids: List[str], 
                           output_directory: str) -> Result[Dict[str, Any]]:
        """Fetch archive data for specified date and pipeline lines."""
        logger.info(f"Starting archive fetch for {len(line_ids)} lines on {archive_date}")

        try:
            # Validate parameters using validator
            validation_result = self.validate_fetch_parameters(archive_date, line_ids, output_directory)
            if not validation_result.success:
                return Result.fail(validation_result.error, validation_result.message)

            # Create domain objects
            archive_date_obj = ArchiveDate(archive_date) if not isinstance(archive_date, ArchiveDate) else archive_date
            pipeline_lines = [PipelineLine(line_id) for line_id in line_ids]
            output_dir = OutputDirectory(output_directory)
            
            # Create fetch request
            fetch_request = FetchArchiveRequest(
                archive_date=archive_date_obj,
                pipeline_lines=pipeline_lines,
                output_directory=output_dir
            )

            # Process each line
            all_extracted_files = []
            failed_lines = []

            for pipeline_line in fetch_request.pipeline_lines:
                try:
                    line_result = self._process_single_line(
                        pipeline_line, 
                        fetch_request.archive_date, 
                        fetch_request.output_directory
                    )

                    if line_result.success:
                        all_extracted_files.extend(line_result.data['files'])
                        logger.info(f"Successfully processed line {pipeline_line.value}")
                    else:
                        failed_lines.append({
                            'line_id': pipeline_line.value,
                            'error': line_result.error
                        })
                        logger.error(f"Failed to process line {pipeline_line.value}: {line_result.error}")

                except Exception as e:
                    failed_lines.append({
                        'line_id': pipeline_line.value,
                        'error': str(e)
                    })
                    logger.error(f"Exception processing line {pipeline_line.value}: {e}")

            # Create result
            success = len(all_extracted_files) > 0
            message = self._create_result_message(all_extracted_files, failed_lines)

            result_data = {
                'success': success,
                'files': [file_info.__dict__ for file_info in all_extracted_files],
                'failed_lines': failed_lines,
                'message': message,
                'output_directory': output_dir.value,
                'fetch_date': archive_date_obj.iso_format,
                'requested_lines': [line.value for line in pipeline_lines]
            }

            logger.info(f"Archive fetch completed: {len(all_extracted_files)} files, {len(failed_lines)} failed")
            return Result.ok(result_data, message)

        except Exception as e:
            logger.error(f"Unexpected error during archive fetch: {e}")
            return Result.fail(f"Archive fetch failed: {str(e)}", "Unexpected error occurred")

    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """Get list of available pipeline lines."""
        return self._path_service.get_available_lines()

    def validate_fetch_parameters(self, archive_date: Any, line_ids: List[str], 
                                  output_directory: str) -> Result[bool]:
        """Validate parameters for fetch operation."""
        return self._validator.validate_fetch_request(archive_date, line_ids, output_directory)

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the archive system."""
        try:
            system_info = ArchiveConversionConstants.get_system_info()
            
            # Add path accessibility info
            path_check = self._path_service.check_path_accessibility()
            system_info['archive_path_accessible'] = path_check.success
            if not path_check.success:
                system_info['archive_path_error'] = path_check.error

            # Add available lines count
            lines_result = self.get_available_lines()
            if lines_result.success:
                system_info['available_lines_count'] = len(lines_result.data)
            else:
                system_info['available_lines_count'] = 0
                system_info['lines_error'] = lines_result.error

            return Result.ok(system_info, "System information retrieved successfully")

        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return Result.fail(f"System info error: {str(e)}", "Failed to retrieve system information")

    def convert(self, input_value: Any) -> Result[Any]:
        """Convert input value to output format (required by IConverter interface)."""
        # This method is required by IConverter but not directly used
        # Could be implemented for batch processing if needed
        return Result.ok(input_value, "No conversion performed")

    def _process_single_line(self, pipeline_line: PipelineLine, archive_date: ArchiveDate, 
                             output_dir: OutputDirectory) -> Result[Dict[str, Any]]:
        """Process archive data for a single pipeline line."""
        try:
            # Find archive files for this line and date
            files_result = self._path_service.find_archive_files(pipeline_line.value, archive_date)
            if not files_result.success:
                return Result.fail(files_result.error, files_result.message)

            zip_files = files_result.data

            # Create line-specific output directory
            line_output_path = output_dir.get_line_output_path(pipeline_line.value, archive_date)
            line_output_path.mkdir(parents=True, exist_ok=True)

            # Extract all archive files for this line
            extraction_result = self._file_extractor.extract_multiple_archives(
                zip_files, str(line_output_path)
            )

            if extraction_result.success:
                extracted_files = []
                for file_dict in extraction_result.data['extracted_files']:
                    # Convert dict back to ArchiveFileInfo if needed
                    if isinstance(file_dict, dict):
                        file_info = ArchiveFileInfo(**file_dict)
                    else:
                        file_info = file_dict
                    extracted_files.append(file_info)

                return Result.ok({
                    'files': extracted_files,
                    'line_id': pipeline_line.value,
                    'output_directory': str(line_output_path),
                    'total_files': len(extracted_files)
                }, f"Successfully processed {len(extracted_files)} files for line {pipeline_line.value}")
            else:
                return Result.fail(extraction_result.error, extraction_result.message)

        except Exception as e:
            logger.error(f"Error processing line {pipeline_line.value}: {e}")
            return Result.fail(f"Line processing error: {str(e)}", f"Failed to process line {pipeline_line.value}")

    def _create_result_message(self, fetched_files: List[ArchiveFileInfo], 
                               failed_fetches: List[Dict[str, str]]) -> str:
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


class LegacyFetchArchiveService:
    """
    Legacy wrapper service for backward compatibility.
    Maintains the old API while using the new architecture internally.
    """

    def __init__(self, new_service: FetchArchiveService):
        """Initialize with the new service implementation."""
        self._new_service = new_service
        logger.debug("LegacyFetchArchiveService initialized for backward compatibility")

    def get_available_lines(self) -> Dict[str, Any]:
        """Get available lines using legacy format."""
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

    def fetch_archive_data(self, archive_date: datetime, line_ids: List[str], 
                           output_directory: str) -> Dict[str, Any]:
        """Fetch archive data using legacy format."""
        result = self._new_service.fetch_archive_data(archive_date, line_ids, output_directory)
        
        # Convert Result to legacy dictionary format
        if result.success:
            return result.data
        else:
            return {
                'success': False,
                'files': [],
                'failed_lines': [],
                'message': result.error,
                'output_directory': output_directory
            }

    def validate_fetch_parameters(self, archive_date: datetime, line_ids: List[str], 
                                  output_directory: str) -> Dict[str, Any]:
        """Validate parameters using legacy format."""
        result = self._new_service.validate_fetch_parameters(archive_date, line_ids, output_directory)
        
        if result.success:
            return {
                'success': True,
                'message': 'Parameters validated successfully'
            }
        else:
            return {
                'success': False,
                'message': result.error
            }