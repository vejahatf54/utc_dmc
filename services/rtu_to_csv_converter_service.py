"""
RTU to CSV Converter Service - Implementation of IRtuToCSVConverter interface.
Responsible for RTU to CSV conversion operations following Single Responsibility Principle.
"""

from typing import Dict, Any, List, Optional
import os
from datetime import datetime
from pathlib import Path

from core.interfaces import IRtuToCSVConverter, IRtuFileReader, Result
from domain.rtu_models import RtuFilePath, RtuProcessingOptions, RtuConversionConstants
# Import the existing service for actual operations
from services.rtu_service import RTUService
from logging_config import get_logger

logger = get_logger(__name__)


class RtuToCsvConverterService(IRtuToCSVConverter):
    """Service for converting RTU files to CSV format."""

    def __init__(self, file_reader: IRtuFileReader):
        """Initialize the RTU to CSV converter service."""
        self._rtu_service = RTUService()
        self._file_reader = file_reader

    def convert_file(self, rtu_file_path: str, output_directory: str,
                     processing_options: Dict[str, Any] = None) -> Result[Dict[str, Any]]:
        """Convert a single RTU file to CSV format."""
        try:
            # Validate input file
            validation_result = self._file_reader.validate_file(rtu_file_path)
            if not validation_result.success:
                return Result.fail(validation_result.error, "Invalid RTU file")

            # Validate output directory
            if not os.path.exists(output_directory):
                return Result.fail("Output directory not found", f"Directory does not exist: {output_directory}")

            # Create processing options
            options = self._create_processing_options(processing_options or {})

            # Generate output file path
            rtu_path = RtuFilePath(rtu_file_path)
            output_filename = f"{rtu_path.path_obj.stem}.csv"
            output_file_path = os.path.join(output_directory, output_filename)

            # Perform conversion using existing RTU service
            start_time = None
            end_time = None
            if options.time_range:
                if options.time_range.has_start_time:
                    start_time = options.time_range.format_start_time()
                if options.time_range.has_end_time:
                    end_time = options.time_range.format_end_time()

            conversion_result = self._rtu_service.export_csv_flat(
                input_file=rtu_file_path,
                output_file=output_file_path,
                start_time=start_time,
                end_time=end_time,
                tags_file=options.tags_file,
                enable_sampling=options.enable_sampling,
                sample_interval=options.sample_interval,
                sample_mode=options.sample_mode
            )

            if conversion_result and conversion_result.get('success', False):
                result_data = {
                    'output_file': output_file_path,
                    'input_file': rtu_file_path,
                    'records_processed': conversion_result.get('records_processed', 0),
                    'processing_time': conversion_result.get('processing_time', 0),
                    'file_size_bytes': os.path.getsize(output_file_path) if os.path.exists(output_file_path) else 0
                }
                return Result.ok(result_data, f"Successfully converted RTU file to CSV: {output_filename}")
            else:
                error_msg = conversion_result.get(
                    'error', 'Unknown conversion error') if conversion_result else 'Conversion failed'
                return Result.fail(error_msg, "RTU to CSV conversion failed")

        except ValueError as e:
            logger.error(f"Invalid file path: {str(e)}")
            return Result.fail(str(e), "Invalid file path")
        except Exception as e:
            logger.error(f"Error converting RTU to CSV: {str(e)}")
            return Result.fail(f"Conversion error: {str(e)}", "Error during RTU to CSV conversion")

    def convert_multiple_files(self, rtu_file_paths: List[str], output_directory: str,
                               processing_options: Dict[str, Any] = None) -> Result[Dict[str, Any]]:
        """Convert multiple RTU files to CSV format."""
        try:
            if not rtu_file_paths:
                return Result.fail("No files provided", "No RTU files to convert")

            # Validate output directory
            if not os.path.exists(output_directory):
                return Result.fail("Output directory not found", f"Directory does not exist: {output_directory}")

            successful_conversions = []
            failed_conversions = []
            total_records = 0
            total_processing_time = 0

            # Convert each file
            for file_path in rtu_file_paths:
                try:
                    result = self.convert_file(
                        file_path, output_directory, processing_options)
                    if result.success:
                        successful_conversions.append({
                            'input_file': file_path,
                            'output_file': result.data['output_file'],
                            'records_processed': result.data.get('records_processed', 0)
                        })
                        total_records += result.data.get(
                            'records_processed', 0)
                        total_processing_time += result.data.get(
                            'processing_time', 0)
                    else:
                        failed_conversions.append({
                            'input_file': file_path,
                            'error': result.error
                        })
                except Exception as e:
                    failed_conversions.append({
                        'input_file': file_path,
                        'error': str(e)
                    })

            result_data = {
                'successful_conversions': successful_conversions,
                'failed_conversions': failed_conversions,
                'total_files_processed': len(successful_conversions),
                'total_files_failed': len(failed_conversions),
                'total_records_processed': total_records,
                'total_processing_time': total_processing_time,
                'output_directory': output_directory
            }

            if successful_conversions:
                message = f"Converted {len(successful_conversions)} files successfully"
                if failed_conversions:
                    message += f" ({len(failed_conversions)} failed)"
                return Result.ok(result_data, message)
            else:
                return Result.fail("All conversions failed", "No files were successfully converted")

        except Exception as e:
            logger.error(f"Error converting multiple RTU files: {str(e)}")
            return Result.fail(f"Multiple conversion error: {str(e)}", "Error during multiple RTU to CSV conversion")

    def get_file_info(self, file_path: str) -> Result[Dict[str, Any]]:
        """Get RTU file information."""
        return self._file_reader.get_file_info(file_path)

    def convert(self, input_data: Any, **kwargs) -> Result[Dict[str, Any]]:
        """Generic convert method required by IConverter interface."""
        # Delegate to specific convert_file method
        if isinstance(input_data, str):
            output_dir = kwargs.get('output_directory', '')
            processing_options = kwargs.get('processing_options')
            return self.convert_file(input_data, output_dir, processing_options)
        else:
            return Result.fail("Invalid input type", "Expected file path as string")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the RTU to CSV conversion system."""
        try:
            system_info = RtuConversionConstants.get_system_info()
            system_info.update({
                'conversion_type': 'RTU to CSV',
                'supported_sampling_modes': ['actual', 'interpolated'],
                'default_csv_format': 'flat',
                'parallel_processing_supported': True
            })
            return Result.ok(system_info, "RTU to CSV system information retrieved")
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return Result.fail(f"System info error: {str(e)}", "Error retrieving system information")

    def _create_processing_options(self, options_dict: Dict[str, Any]) -> RtuProcessingOptions:
        """Create processing options from dictionary."""
        from domain.rtu_models import RtuTimeRange

        # Parse time range if provided
        time_range = None
        if options_dict.get('start_time') or options_dict.get('end_time'):
            start_time = None
            end_time = None

            if options_dict.get('start_time'):
                if isinstance(options_dict['start_time'], str):
                    start_time = datetime.strptime(
                        options_dict['start_time'], RtuConversionConstants.TIME_FORMAT_DMY)
                else:
                    start_time = options_dict['start_time']

            if options_dict.get('end_time'):
                if isinstance(options_dict['end_time'], str):
                    end_time = datetime.strptime(
                        options_dict['end_time'], RtuConversionConstants.TIME_FORMAT_DMY)
                else:
                    end_time = options_dict['end_time']

            if start_time or end_time:
                time_range = RtuTimeRange(start_time, end_time)

        return RtuProcessingOptions(
            enable_peek_file_filtering=options_dict.get(
                'enable_peek_file_filtering', False),
            peek_file_pattern=options_dict.get('peek_file_pattern', "*.dt"),
            time_range=time_range,
            tags_file=options_dict.get('tags_file'),
            selected_tags=options_dict.get('selected_tags'),
            enable_sampling=options_dict.get('enable_sampling', False),
            sample_interval=options_dict.get('sample_interval', 60),
            sample_mode=options_dict.get('sample_mode', "actual"),
            output_format="csv",
            output_directory=options_dict.get('output_directory'),
            enable_parallel_processing=options_dict.get(
                'enable_parallel_processing', True),
            max_workers=options_dict.get('max_workers'),
            tag_mapping_file=options_dict.get('tag_mapping_file'),
            tag_renaming_enabled=options_dict.get(
                'tag_renaming_enabled', False)
        )
