"""
CSV to RTU Converter Service - Refactored Implementation

This service follows SOLID principles and clean architecture patterns.
Uses dependency injection and implements proper interfaces.
"""

import os
import tempfile
import shutil
import pandas as pd
import base64
import io
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.interfaces import ICsvToRtuConverter, ICsvValidator, IRtuDataWriter, Result
from domain.csv_rtu_models import (
    CsvFileMetadata, RtuTimestamp, RtuDataPoint, ConversionRequest,
    ConversionResult, ConversionConstants
)


# RTU Data Writer Implementation
class SpsRtuDataWriter(IRtuDataWriter):
    """RTU data writer using sps_api library."""

    def __init__(self):
        self._sps_api_available = False
        self._api_class = None
        self._model_class = None
        self._init_sps_api()

    def _init_sps_api(self):
        """Initialize sps_api if available."""
        try:
            from sps_api import TodremApi
            from sps_api.model import RtuDataModel
            self._api_class = TodremApi
            self._model_class = RtuDataModel
            self._sps_api_available = True
        except ImportError:
            self._sps_api_available = False

    def is_available(self) -> bool:
        """Check if RTU writer is available."""
        return self._sps_api_available

    def write_rtu_data(self, data_points: List[RtuDataPoint], output_path: str) -> Result[Dict[str, Any]]:
        """Write RTU data points to file using sps_api."""
        if not self._sps_api_available:
            return Result.fail(
                ConversionConstants.SPS_API_NOT_AVAILABLE,
                "Please install sps_api to use RTU conversion"
            )

        api = None
        opened = False

        try:
            # Clean existing file to avoid open failures
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass  # Non-fatal

            # Initialize API
            api = self._SpsTodremApiAdapter(self._api_class, self._model_class)

            # Open RTU file
            total_points = len(data_points)
            channel = api.open_rtu_file(output_path, total_points)
            if channel == 0:
                return Result.fail("Failed to open RTU file", "Could not create RTU file")
            opened = True

            # Write data points
            tags_written = 0
            for data_point in data_points:
                api.write_point(
                    data_point.timestamp.value,
                    data_point.tag_name,
                    data_point.value,
                    data_point.quality
                )
                tags_written += 1

            return Result.ok({
                'tags_written': tags_written,
                'output_path': output_path,
                'output_file': os.path.basename(output_path)
            }, f"Successfully wrote {tags_written} data points")

        except Exception as e:
            return Result.fail(f"Error writing RTU data: {str(e)}", "RTU write operation failed")
        finally:
            # Always attempt to flush and close if we opened a file
            if opened and api:
                try:
                    api.flush()
                except Exception:
                    pass
                try:
                    api.close()
                except Exception:
                    pass

            # Dispose of API resources
            if api:
                try:
                    api.dispose()
                except Exception:
                    pass

    class _SpsTodremApiAdapter:
        """Internal adapter for the sps_api.TodremApi with proper resource management."""

        def __init__(self, api_class, model_class):
            self._api = api_class()
            self._model_class = model_class

        def open_rtu_file(self, file_path: str, no_records: int) -> int:
            return self._api.open_rtu_file(file_path, no_records)

        def write_point(self, timestamp: datetime, tag_name: str, tag_value: float, quality: int) -> None:
            rtu_data = self._model_class(
                timestamp=timestamp,
                tag_name=tag_name,
                tag_value=tag_value,
                quality=quality,
            )
            self._api.write_to_rtu_file(rtu_data)

        def flush(self) -> None:
            self._api.flush_rtu_memory_buffer()

        def close(self) -> None:
            self._api.close_rtu_file()

        def dispose(self) -> None:
            """Best-effort flush+close and attempt additional shutdown hooks."""
            try:
                try:
                    self.flush()
                except Exception:
                    pass
                try:
                    self.close()
                except Exception:
                    pass
            finally:
                for name in ("dispose", "shutdown", "terminate", "disconnect", "finalize"):
                    try:
                        fn = getattr(self._api, name, None)
                        if callable(fn):
                            fn()
                    except Exception:
                        pass


class MockRtuDataWriter(IRtuDataWriter):
    """Mock RTU data writer for testing purposes."""

    def __init__(self):
        self._available = True

    def is_available(self) -> bool:
        """Check if RTU writer is available."""
        return self._available

    def write_rtu_data(self, data_points: List[RtuDataPoint], output_path: str) -> Result[Dict[str, Any]]:
        """Mock implementation that creates a dummy file."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Write a simple text file for testing
            with open(output_path, 'w') as f:
                f.write(f"Mock RTU file - {len(data_points)} data points\n")
                # Write first 5 as sample
                for i, dp in enumerate(data_points[:5]):
                    f.write(
                        f"{dp.timestamp.iso_format}, {dp.tag_name}, {dp.value}, {dp.quality}\n")
                if len(data_points) > 5:
                    f.write(f"... and {len(data_points) - 5} more points\n")

            return Result.ok({
                'tags_written': len(data_points),
                'output_path': output_path,
                'output_file': os.path.basename(output_path)
            }, f"Mock: Successfully wrote {len(data_points)} data points")

        except Exception as e:
            return Result.fail(f"Mock RTU write error: {str(e)}", "Mock RTU write operation failed")


# Main Service Implementation
class CsvToRtuConverterService(ICsvToRtuConverter):
    """CSV to RTU converter service with dependency injection."""

    def __init__(self, csv_validator: ICsvValidator, rtu_writer: IRtuDataWriter):
        """Initialize service with injected dependencies."""
        self._csv_validator = csv_validator
        self._rtu_writer = rtu_writer

    def convert(self, input_value: Any) -> Result[Any]:
        """Convert input value to output format."""
        # This is a generic interface method, delegate to specific methods
        if isinstance(input_value, dict):
            if 'csv_file_path' in input_value and 'output_directory' in input_value:
                return self.convert_file(input_value['csv_file_path'], input_value['output_directory'])
        return Result.fail("Invalid input format", "Use convert_file or convert_multiple_files methods")

    def convert_file(self, csv_file_path: str, output_directory: str) -> Result[Dict[str, Any]]:
        """Convert a single CSV file to RTU format."""
        try:
            # Validate conversion request
            validation_result = self.validate_conversion_request(
                csv_file_path, output_directory)
            if not validation_result.success:
                return Result.fail(validation_result.error, validation_result.message)

            # Validate CSV file and get metadata
            metadata_result = self._csv_validator.validate_file_structure(
                csv_file_path)
            if not metadata_result.success:
                return Result.fail(metadata_result.error, metadata_result.message)

            metadata = metadata_result.data['metadata']

            # Create conversion request
            request = ConversionRequest(
                csv_file_path, output_directory, metadata)

            # Read and parse CSV file
            df = pd.read_csv(csv_file_path)
            data_points = self._parse_csv_to_data_points(df)

            # Write RTU data
            write_result = self._rtu_writer.write_rtu_data(
                data_points, request.expected_rtu_path)
            if not write_result.success:
                result = ConversionResult.create_failure(
                    request, write_result.error)
                return Result.fail(write_result.error, write_result.message)

            # Create successful result
            result = ConversionResult.create_success(
                request,
                len(df),
                write_result.data['tags_written'],
                write_result.data['output_path']
            )

            return Result.ok({
                'success': True,
                'result': result,
                'records_processed': result.records_processed,
                'tags_written': result.tags_written,
                'rtu_file': result.output_filename,
                'rtu_file_path': result.rtu_file_path
            }, "File conversion successful")

        except Exception as e:
            return Result.fail(f"Conversion error: {str(e)}", "File conversion failed")

    def convert_multiple_files(self, csv_file_paths: List[str], output_directory: str) -> Result[Dict[str, Any]]:
        """Convert multiple CSV files to RTU format."""
        try:
            if not csv_file_paths:
                return Result.fail("No files provided", "Please provide CSV files to convert")

            results = []
            successful_conversions = 0
            total_files = len(csv_file_paths)

            for file_path in csv_file_paths:
                filename = os.path.basename(file_path)
                conversion_result = self.convert_file(
                    file_path, output_directory)

                if conversion_result.success:
                    successful_conversions += 1
                    result_data = conversion_result.data
                    results.append({
                        'file': filename,
                        'status': 'success',
                        'output_file': result_data['rtu_file'],
                        'records_processed': result_data['records_processed'],
                        'tags_written': result_data['tags_written']
                    })
                else:
                    results.append({
                        'file': filename,
                        'status': 'failed',
                        'error': conversion_result.error
                    })

            if successful_conversions == 0:
                return Result.fail(
                    "No files were successfully converted",
                    "All conversion attempts failed"
                )

            return Result.ok({
                'success': True,
                'message': f'Successfully converted {successful_conversions} of {total_files} files',
                'results': results,
                'output_directory': output_directory,
                'successful_conversions': successful_conversions,
                'total_files': total_files
            }, f"Batch conversion completed: {successful_conversions}/{total_files} successful")

        except Exception as e:
            return Result.fail(f"Batch conversion error: {str(e)}", "Batch conversion failed")

    def validate_conversion_request(self, csv_file_path: str, output_directory: str) -> Result[bool]:
        """Validate a conversion request before processing."""
        try:
            # Check if RTU writer is available
            if not self._rtu_writer.is_available():
                return Result.fail(
                    ConversionConstants.SPS_API_NOT_AVAILABLE,
                    "RTU writer is not available"
                )

            # Validate output directory
            from validation.csv_validators import create_output_directory_validator
            output_validator = create_output_directory_validator()
            output_result = output_validator.validate(output_directory)
            if not output_result.success:
                return Result.fail(output_result.error, output_result.message)

            return Result.ok(True, "Conversion request is valid")

        except Exception as e:
            return Result.fail(f"Validation error: {str(e)}", "Request validation failed")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the conversion system."""
        try:
            info = {
                'service_name': 'CSV to RTU Converter Service',
                'version': '2.0.0',
                'architecture': 'Clean Architecture with SOLID principles',
                'rtu_writer_available': self._rtu_writer.is_available(),
                'supported_extensions': ConversionConstants.SUPPORTED_CSV_EXTENSIONS,
                'output_extension': ConversionConstants.RTU_EXTENSION,
                'max_file_size_mb': ConversionConstants.MAX_FILE_SIZE_BYTES / (1024 * 1024),
                'min_columns': ConversionConstants.MIN_COLUMNS,
                'max_columns': ConversionConstants.MAX_COLUMNS,
                'quality_values': {
                    'good': ConversionConstants.QUALITY_GOOD,
                    'bad': ConversionConstants.QUALITY_BAD
                }
            }

            return Result.ok(info, "System information retrieved")

        except Exception as e:
            return Result.fail(f"Error getting system info: {str(e)}", "System info retrieval failed")

    def _parse_csv_to_data_points(self, df: pd.DataFrame) -> List[RtuDataPoint]:
        """Parse CSV DataFrame to RTU data points."""
        data_points = []
        header = list(df.columns)

        for _, row in df.iterrows():
            # Parse timestamp from first column
            try:
                timestamp = RtuTimestamp.from_string(str(row.iloc[0]))
            except Exception:
                # Use current time as fallback
                timestamp = RtuTimestamp.now()

            # Process each tag column (skip timestamp column)
            for col_index in range(1, len(header)):
                tag_name = header[col_index]
                value_text = row.iloc[col_index]

                try:
                    data_point = RtuDataPoint.from_csv_data(
                        timestamp.iso_format,
                        tag_name,
                        str(value_text) if value_text is not None else ""
                    )
                    data_points.append(data_point)
                except Exception:
                    # Create data point with bad quality on error
                    data_point = RtuDataPoint(
                        timestamp, tag_name, 0.0, ConversionConstants.QUALITY_BAD)
                    data_points.append(data_point)

        return data_points


class CsvToRtuConverterServiceFromUpload(ICsvToRtuConverter):
    """CSV to RTU converter service that handles uploaded content."""

    def __init__(self, csv_validator: ICsvValidator, rtu_writer: IRtuDataWriter):
        """Initialize service with injected dependencies."""
        self._csv_validator = csv_validator
        self._rtu_writer = rtu_writer
        self._base_service = CsvToRtuConverterService(
            csv_validator, rtu_writer)

    def convert_file(self, csv_file_path: str, output_directory: str) -> Result[Dict[str, Any]]:
        """Convert a single CSV file to RTU format."""
        return self._convert_uploaded_file(csv_file_path, output_directory)

    def convert_multiple_files(self, csv_file_paths: List[str], output_directory: str) -> Result[Dict[str, Any]]:
        """Convert multiple CSV files to RTU format from uploaded content."""
        try:
            if not csv_file_paths:
                return Result.fail("No files provided", "Please provide CSV files to convert")

            results = []
            successful_conversions = 0
            total_files = len(csv_file_paths)

            for file_path in csv_file_paths:
                filename = os.path.basename(file_path)
                conversion_result = self._convert_uploaded_file(
                    file_path, output_directory)

                if conversion_result.success:
                    successful_conversions += 1
                    result_data = conversion_result.data
                    results.append({
                        'file': filename,
                        'status': 'success',
                        'output_file': result_data['rtu_file'],
                        'records_processed': result_data['records_processed'],
                        'tags_written': result_data['tags_written']
                    })
                else:
                    results.append({
                        'file': filename,
                        'status': 'failed',
                        'error': conversion_result.error
                    })

            if successful_conversions == 0:
                return Result.fail(
                    "No files were successfully converted",
                    "All conversion attempts failed"
                )

            return Result.ok({
                'success': True,
                'message': f'Successfully converted {successful_conversions} of {total_files} files',
                'results': results,
                'output_directory': output_directory,
                'successful_conversions': successful_conversions,
                'total_files': total_files
            }, f"Batch conversion completed: {successful_conversions}/{total_files} successful")

        except Exception as e:
            return Result.fail(f"Batch conversion error: {str(e)}", "Batch conversion failed")

    def _convert_uploaded_file(self, temp_file_path: str, output_directory: str) -> Result[Dict[str, Any]]:
        """Convert a temporary uploaded file to RTU format."""
        # Delegate to base service since temp file is already on disk
        return self._base_service.convert_file(temp_file_path, output_directory)

    def validate_conversion_request(self, csv_file_path: str, output_directory: str) -> Result[bool]:
        """Validate a conversion request before processing."""
        return self._base_service.validate_conversion_request(csv_file_path, output_directory)

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the conversion system."""
        return self._base_service.get_system_info()


# Legacy wrapper for backward compatibility
class LegacyCsvToRtuService:
    """Legacy wrapper maintaining old API for backward compatibility."""

    def __init__(self, converter_service: ICsvToRtuConverter):
        self._converter_service = converter_service

    def convert_to_rtu(self, csv_file_paths: List[str], output_directory: str) -> Dict[str, Any]:
        """Legacy method for converting CSV files to RTU."""
        result = self._converter_service.convert_multiple_files(
            csv_file_paths, output_directory)
        return result.to_dict()

    def convert_single_csv_to_rtu(self, csv_file_path: str, output_dir: str) -> Dict[str, Any]:
        """Legacy method for converting single CSV file to RTU."""
        result = self._converter_service.convert_file(
            csv_file_path, output_dir)
        if result.success:
            return result.data
        else:
            return {"success": False, "error": result.error}

    def validate_csv_file(self, file_path: str) -> Dict[str, Any]:
        """Legacy method for validating CSV file."""
        from validation.csv_validators import create_csv_file_validator
        validator = create_csv_file_validator()
        result = validator.validate_file_structure(file_path)
        if result.success:
            return result.data
        else:
            return {'valid': False, 'error': result.error}
