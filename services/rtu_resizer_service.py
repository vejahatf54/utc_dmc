"""
RTU Resizer Service - Implementation of IRtuResizer interface.
Responsible for RTU file resizing operations following Single Responsibility Principle.
"""

from typing import Dict, Any, Optional
import os
from datetime import datetime
from pathlib import Path

from core.interfaces import IRtuResizer, IRtuFileReader, Result
from domain.rtu_models import RtuFilePath, RtuTimeRange, RtuConversionConstants
# Import the existing service for actual operations
from services.rtu_service import RTUService
from logging_config import get_logger

logger = get_logger(__name__)


class RtuResizerService(IRtuResizer):
    """Service for resizing RTU files."""

    def __init__(self, file_reader: IRtuFileReader):
        """Initialize the RTU resizer service."""
        self._rtu_service = RTUService()
        self._file_reader = file_reader

    def resize_file(self, input_file_path: str, output_file_path: str,
                    start_time: str = None, end_time: str = None,
                    tag_mapping_file: str = None) -> Result[Dict[str, Any]]:
        """Resize RTU file by time range with optional tag mapping."""
        try:
            # Validate resize request
            validation_result = self.validate_resize_request(
                input_file_path, output_file_path, start_time, end_time)
            if not validation_result.success:
                return Result.fail(validation_result.error, "Invalid resize request")

            # Get original file info for comparison
            original_info_result = self._file_reader.get_file_info(
                input_file_path)
            if not original_info_result.success:
                return Result.fail(original_info_result.error, "Cannot read input file information")

            original_info = original_info_result.data

            # Perform resize operation using existing RTU service
            # Note: RTU service returns integer (points written), not a dictionary
            points_written = self._rtu_service.resize_rtu(
                input_file=input_file_path,
                output_file=output_file_path,
                start_time=start_time,
                end_time=end_time,
                tag_mapping_file=tag_mapping_file
            )

            # RTU service returns integer on success, raises exception on failure
            if points_written >= 0:
                # Get resized file info
                resized_info_result = self._file_reader.get_file_info(
                    output_file_path)
                resized_info = resized_info_result.data if resized_info_result.success else {}

                result_data = {
                    'input_file': input_file_path,
                    'output_file': output_file_path,
                    'input_points': original_info.get('total_points', 0),
                    'output_points': points_written,  # Use the actual points written
                    'input_tags': original_info.get('tags_count', 0),
                    'output_tags': resized_info.get('tags_count', 0) if resized_info else 0,
                    'processing_time': 0,  # RTU service doesn't return timing info
                    'original_time_range': {
                        'start': original_info.get('first_timestamp'),
                        'end': original_info.get('last_timestamp')
                    },
                    'resized_time_range': {
                        'start': resized_info.get('first_timestamp'),
                        'end': resized_info.get('last_timestamp')
                    } if resized_info else None,
                    'tag_mapping_applied': tag_mapping_file is not None,
                    'file_size_bytes': os.path.getsize(output_file_path) if os.path.exists(output_file_path) else 0
                }

                return Result.ok(result_data, f"Successfully resized RTU file: {Path(output_file_path).name}")
            else:
                return Result.fail("No points written", "RTU resize operation failed")

        except Exception as e:
            logger.error(f"Error resizing RTU file: {str(e)}")
            return Result.fail(f"Resize error: {str(e)}", "Error during RTU file resize")

    def get_file_info(self, file_path: str) -> Result[Dict[str, Any]]:
        """Get RTU file information for resizing operations."""
        return self._file_reader.get_file_info(file_path)

    def validate_resize_request(self, input_file_path: str, output_file_path: str,
                                start_time: str = None, end_time: str = None) -> Result[bool]:
        """Validate a resize request before processing."""
        try:
            # Validate input file
            input_validation = self._file_reader.validate_file(input_file_path)
            if not input_validation.success:
                return Result.fail(input_validation.error, "Invalid input file")

            # Validate output file path
            try:
                output_path = Path(output_file_path)
                if not output_path.parent.exists():
                    return Result.fail("Output directory does not exist", f"Directory not found: {output_path.parent}")

                # Check if output file has valid RTU extension
                if output_path.suffix.lower() not in RtuConversionConstants.SUPPORTED_OUTPUT_EXTENSIONS:
                    return Result.fail(f"Invalid output file extension: {output_path.suffix}",
                                       f"Supported extensions: {RtuConversionConstants.SUPPORTED_OUTPUT_EXTENSIONS}")
            except Exception as e:
                return Result.fail(f"Invalid output path: {str(e)}", "Invalid output file path")

            # Validate time range if provided
            if start_time or end_time:
                time_validation = self._validate_time_range(
                    input_file_path, start_time, end_time)
                if not time_validation.success:
                    return time_validation

            return Result.ok(True, "Resize request validation successful")

        except Exception as e:
            logger.error(f"Error validating resize request: {str(e)}")
            return Result.fail(f"Validation error: {str(e)}", "Error validating resize request")

    def convert(self, input_data: Any, **kwargs) -> Result[Dict[str, Any]]:
        """Generic convert method required by IConverter interface."""
        # Delegate to specific resize_file method
        if isinstance(input_data, str):
            output_file = kwargs.get(
                'output_file_path', kwargs.get('output_file', ''))
            start_time = kwargs.get('start_time')
            end_time = kwargs.get('end_time')
            tag_mapping_file = kwargs.get('tag_mapping_file')
            return self.resize_file(input_data, output_file, start_time, end_time, tag_mapping_file)
        else:
            return Result.fail("Invalid input type", "Expected file path as string")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the RTU resizing system."""
        try:
            system_info = RtuConversionConstants.get_system_info()
            system_info.update({
                'operation_type': 'RTU Resize',
                'supports_time_range': True,
                'supports_tag_mapping': True,
                'preserves_data_integrity': True,
                'time_format_required': RtuConversionConstants.TIME_FORMAT_DMY
            })
            return Result.ok(system_info, "RTU resizer system information retrieved")
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return Result.fail(f"System info error: {str(e)}", "Error retrieving system information")

    def _validate_time_range(self, input_file_path: str, start_time: str = None,
                             end_time: str = None) -> Result[bool]:
        """Validate time range against file bounds."""
        try:
            # Get file info to check time bounds
            file_info_result = self._file_reader.get_file_info(input_file_path)
            if not file_info_result.success:
                return Result.fail(file_info_result.error, "Cannot validate time range - file info unavailable")

            file_info = file_info_result.data
            file_start = file_info.get('first_timestamp')
            file_end = file_info.get('last_timestamp')

            if not file_start or not file_end:
                return Result.fail("Invalid file timestamps", "Cannot validate time range - file timestamps unavailable")

            # Parse and validate time strings
            parsed_start = None
            parsed_end = None

            if start_time:
                try:
                    parsed_start = datetime.strptime(
                        start_time, RtuConversionConstants.TIME_FORMAT_DMY)
                except ValueError:
                    return Result.fail(f"Invalid start time format: {start_time}",
                                       f"Expected format: {RtuConversionConstants.TIME_FORMAT_DMY}")

            if end_time:
                try:
                    parsed_end = datetime.strptime(
                        end_time, RtuConversionConstants.TIME_FORMAT_DMY)
                except ValueError:
                    return Result.fail(f"Invalid end time format: {end_time}",
                                       f"Expected format: {RtuConversionConstants.TIME_FORMAT_DMY}")

            # Validate time range logic
            if parsed_start and parsed_end and parsed_start >= parsed_end:
                return Result.fail("Start time must be before end time", "Invalid time range")

            # Check bounds (warnings, not errors)
            warnings = []
            if parsed_start and parsed_start < file_start:
                warnings.append(
                    f"Start time is before file start ({file_start.strftime(RtuConversionConstants.TIME_FORMAT_DMY)})")

            if parsed_end and parsed_end > file_end:
                warnings.append(
                    f"End time is after file end ({file_end.strftime(RtuConversionConstants.TIME_FORMAT_DMY)})")

            # Time range is valid even with warnings
            message = "Time range validation successful"
            if warnings:
                message += f" (Warnings: {'; '.join(warnings)})"

            return Result.ok(True, message)

        except Exception as e:
            logger.error(f"Error validating time range: {str(e)}")
            return Result.fail(f"Time validation error: {str(e)}", "Error validating time range")
