"""
RTU File Reader Service - Implementation of IRtuFileReader interface.
Responsible for reading RTU file information following Single Responsibility Principle.
"""

from typing import Dict, Any
import os
from datetime import datetime
from pathlib import Path

from core.interfaces import IRtuFileReader, Result
from domain.rtu_models import RtuFilePath, RtuFileInfo, RtuConversionConstants
# Import the existing service for actual operations
from services.rtu_service import RTUService
from logging_config import get_logger

logger = get_logger(__name__)


class RtuFileReaderService(IRtuFileReader):
    """Service for reading RTU file information."""

    def __init__(self):
        """Initialize the RTU file reader service."""
        self._rtu_service = RTUService()

    def get_file_info(self, file_path: str) -> Result[Dict[str, Any]]:
        """Get RTU file information including timestamps and counts."""
        try:
            # Validate file path using domain model
            rtu_path = RtuFilePath(file_path)
            if not rtu_path.exists():
                return Result.fail("File not found", f"RTU file not found: {file_path}")

            # Use existing RTU service to get file info
            file_info = self._rtu_service.get_file_info(file_path)

            if not file_info:
                return Result.fail("Failed to read file info", "Could not extract RTU file information")

            # Validate and structure the response
            first_timestamp = file_info.get('first_timestamp')
            last_timestamp = file_info.get('last_timestamp')

            if not first_timestamp or not last_timestamp:
                return Result.fail("Invalid file timestamps", "RTU file contains invalid timestamp data")

            result_data = {
                'file_path': str(rtu_path),
                'filename': rtu_path.filename,
                'first_timestamp': first_timestamp,
                'last_timestamp': last_timestamp,
                'total_points': file_info.get('total_points', 0),
                'tags_count': file_info.get('tags_count', 0),
                'duration_seconds': (last_timestamp - first_timestamp).total_seconds()
            }

            return Result.ok(result_data, f"Successfully read RTU file info: {rtu_path.filename}")

        except ValueError as e:
            logger.error(f"Invalid file path: {str(e)}")
            return Result.fail(str(e), "Invalid RTU file path")
        except Exception as e:
            logger.error(f"Error reading RTU file info: {str(e)}")
            return Result.fail(f"File info error: {str(e)}", "Error reading RTU file information")

    def validate_file(self, file_path: str) -> Result[bool]:
        """Validate RTU file format and accessibility."""
        try:
            # Use domain model for path validation
            rtu_path = RtuFilePath(file_path)

            if not rtu_path.exists():
                return Result.fail("File not found", f"RTU file not found: {file_path}")

            # Check if file is accessible and not empty
            file_size = rtu_path.path_obj.stat().st_size
            if file_size == 0:
                return Result.fail("Empty file", "RTU file is empty")

            # Try to read basic file info to validate format
            try:
                file_info = self._rtu_service.get_file_info(file_path)
                if not file_info:
                    return Result.fail("Invalid RTU format", "File does not appear to be a valid RTU file")

                return Result.ok(True, f"RTU file validation successful: {rtu_path.filename}")
            except Exception as e:
                return Result.fail(f"RTU format validation failed: {str(e)}", "Invalid RTU file format")

        except ValueError as e:
            logger.error(f"File validation error: {str(e)}")
            return Result.fail(str(e), "File validation failed")
        except Exception as e:
            logger.error(f"Unexpected error during file validation: {str(e)}")
            return Result.fail(f"Validation error: {str(e)}", "Error validating RTU file")
