"""
Archive path service for handling UNC path operations.
Follows Single Responsibility Principle - only handles path-related operations.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
from core.interfaces import IArchivePathService, Result
from domain.archive_models import ArchivePath, ArchiveDate, PipelineLine
from services.config_manager import get_config_manager
from logging_config import get_logger

logger = get_logger(__name__)


class ArchivePathService(IArchivePathService):
    """Service for archive path operations using dependency injection."""

    def __init__(self, archive_path: ArchivePath):
        """Initialize with archive path dependency."""
        self._archive_path = archive_path
        logger.debug(f"ArchivePathService initialized with path: {archive_path.value}")

    def get_available_lines(self) -> Result[List[Dict[str, str]]]:
        """Get list of available pipeline lines from archive structure."""
        logger.info(f"Getting available lines from {self._archive_path.value}")

        try:
            # Check if path is accessible
            accessibility_result = self.check_path_accessibility()
            if not accessibility_result.success:
                return Result.fail(
                    accessibility_result.error,
                    f"Cannot access archive path: {self._archive_path.value}"
                )

            # Get all folder names in the archive path - these represent line IDs
            lines = []
            for item in os.listdir(self._archive_path.value):
                item_path = os.path.join(self._archive_path.value, item)
                if os.path.isdir(item_path):
                    try:
                        # Validate line ID using domain model
                        pipeline_line = PipelineLine(item)
                        lines.append({
                            'label': pipeline_line.display_label,
                            'value': pipeline_line.value
                        })
                    except ValueError as e:
                        logger.warning(f"Skipping invalid line folder '{item}': {e}")
                        continue

            # Sort lines by name for better UI
            lines.sort(key=lambda x: x['value'])

            logger.info(f"Successfully retrieved {len(lines)} pipeline lines")

            return Result.ok(lines, f"Successfully retrieved {len(lines)} lines")

        except Exception as e:
            logger.error(f"Error getting available lines: {e}")
            return Result.fail(
                f"Error accessing archive path: {str(e)}",
                "Failed to retrieve pipeline lines"
            )

    def check_path_accessibility(self) -> Result[bool]:
        """Check if archive path is accessible."""
        try:
            is_accessible = self._archive_path.exists()
            if is_accessible:
                return Result.ok(True, "Archive path is accessible")
            else:
                return Result.fail(
                    f"Archive path not accessible: {self._archive_path.value}",
                    "Cannot access archive repository"
                )
        except Exception as e:
            logger.warning(f"Error checking archive path accessibility: {e}")
            return Result.fail(
                f"Error checking path accessibility: {str(e)}",
                "Failed to verify archive path access"
            )

    def get_line_archive_path(self, line_id: str, archive_date: Any) -> Result[str]:
        """Get the archive path for a specific line and date."""
        try:
            # Validate inputs using domain models
            pipeline_line = PipelineLine(line_id)
            
            # Handle different date input types
            if not isinstance(archive_date, ArchiveDate):
                archive_date_obj = ArchiveDate(archive_date)
            else:
                archive_date_obj = archive_date

            # Build path using domain model methods
            line_path = self._archive_path.get_date_path(pipeline_line.value, archive_date_obj)
            
            logger.debug(f"Archive path for {line_id} on {archive_date_obj.iso_format}: {line_path}")
            
            return Result.ok(str(line_path), "Archive path constructed successfully")

        except ValueError as e:
            return Result.fail(str(e), "Invalid input parameters")
        except Exception as e:
            logger.error(f"Error constructing archive path: {e}")
            return Result.fail(f"Error constructing path: {str(e)}", "Failed to build archive path")

    def find_archive_files(self, line_id: str, archive_date: Any) -> Result[List[str]]:
        """Find all archive files for a specific line and date."""
        try:
            # Get archive path for the line and date
            path_result = self.get_line_archive_path(line_id, archive_date)
            if not path_result.success:
                return Result.fail(path_result.error, path_result.message)

            archive_path = path_result.data

            # Check if archive folder exists
            if not os.path.exists(archive_path) or not os.path.isdir(archive_path):
                if isinstance(archive_date, ArchiveDate):
                    date_str = archive_date.iso_format
                else:
                    date_str = str(archive_date)
                
                return Result.fail(
                    f"No archive folder found for {line_id} on {date_str}",
                    "Archive data not available for selected date"
                )

            # Find all zip files in the archive folder
            zip_files = []
            for file in os.listdir(archive_path):
                if file.lower().endswith('.zip'):
                    zip_files.append(os.path.join(archive_path, file))

            if not zip_files:
                if isinstance(archive_date, ArchiveDate):
                    date_str = archive_date.iso_format
                else:
                    date_str = str(archive_date)
                
                return Result.fail(
                    f"No archive files found for {line_id} on {date_str}",
                    "No ZIP files found in archive folder"
                )

            logger.debug(f"Found {len(zip_files)} archive files for {line_id}")
            return Result.ok(zip_files, f"Found {len(zip_files)} archive files")

        except Exception as e:
            logger.error(f"Error finding archive files: {e}")
            return Result.fail(f"Error searching archive files: {str(e)}", "Failed to find archive files")


def create_archive_path_service() -> ArchivePathService:
    """Factory function to create ArchivePathService with configuration."""
    config_manager = get_config_manager()
    archive_base_path = config_manager.get_archive_base_path()
    
    try:
        archive_path = ArchivePath(archive_base_path)
        return ArchivePathService(archive_path)
    except ValueError as e:
        logger.error(f"Invalid archive configuration: {e}")
        raise ValueError(f"Cannot create archive path service: {e}")