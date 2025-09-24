"""
Review file reader service - Implementation of IReviewFileReader interface.
Responsible for reading and validating Review files.
"""

from typing import Dict, Any
import os
from datetime import datetime
from pathlib import Path

from core.interfaces import IReviewFileReader, Result
from domain.review_models import ReviewFilePath, ReviewFileInfo
from logging_config import get_logger

logger = get_logger(__name__)


class ReviewFileReaderService(IReviewFileReader):
    """Service for reading Review file information."""

    def get_file_info(self, file_path: str) -> Result[Dict[str, Any]]:
        """Get Review file information including timestamps and metadata."""
        try:
            # Validate file path
            review_path = ReviewFilePath(file_path)

            if not review_path.exists():
                return Result.fail(f"File not found: {file_path}", "Review file does not exist")

            # Get file information
            file_info = ReviewFileInfo.from_file_path(file_path)

            if not file_info.is_valid:
                return Result.fail(file_info.error_message, "Invalid Review file")

            # Convert to dictionary for compatibility
            info_dict = {
                'file_path': file_info.file_path,
                'filename': file_info.filename,
                'file_size_bytes': file_info.file_size_bytes,
                'file_size_mb': round(file_info.file_size_bytes / (1024 * 1024), 2),
                'last_modified': file_info.last_modified.isoformat(),
                'last_modified_str': file_info.last_modified.strftime('%Y-%m-%d %H:%M:%S'),
                'exists': file_info.exists,
                'is_valid': file_info.is_valid,
                'extension': review_path.extension,
                'csv_filename': review_path.csv_filename
            }

            return Result.ok(info_dict, f"Successfully read Review file info: {file_info.filename}")

        except ValueError as e:
            logger.error(f"Invalid Review file path: {str(e)}")
            return Result.fail(str(e), "Invalid Review file path")
        except Exception as e:
            logger.error(f"Error reading Review file info: {str(e)}")
            return Result.fail(f"File read error: {str(e)}", "Error reading Review file information")

    def validate_file(self, file_path: str) -> Result[bool]:
        """Validate Review file format and accessibility."""
        try:
            # Validate path format
            review_path = ReviewFilePath(file_path)

            # Check if file exists
            if not review_path.exists():
                return Result.fail(f"File not found: {file_path}", "Review file does not exist")

            # Check if file is accessible
            try:
                # Try to open the file to check accessibility
                with open(review_path.value, 'rb') as f:
                    # Read first few bytes to ensure it's accessible
                    f.read(1024)
            except IOError as e:
                return Result.fail(f"File not accessible: {str(e)}", "Review file cannot be read")

            # Check file size (should not be empty)
            file_size = review_path.path_obj.stat().st_size
            if file_size == 0:
                return Result.fail("File is empty", "Review file has no content")

            return Result.ok(True, f"Review file validation successful: {review_path.filename}")

        except ValueError as e:
            logger.error(f"Invalid Review file path: {str(e)}")
            return Result.fail(str(e), "Invalid Review file path")
        except Exception as e:
            logger.error(f"Error validating Review file: {str(e)}")
            return Result.fail(f"Validation error: {str(e)}", "Error validating Review file")
