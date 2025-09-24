"""
Archive file extractor service for handling ZIP file operations.
Follows Single Responsibility Principle - only handles file extraction operations.
"""

import os
import zipfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
from core.interfaces import IArchiveFileExtractor, Result
from domain.archive_models import OutputDirectory, ArchiveFileInfo, ArchiveDate, PipelineLine
from logging_config import get_logger

logger = get_logger(__name__)


class ArchiveFileExtractor(IArchiveFileExtractor):
    """Service for extracting archive files with proper error handling."""

    def extract_archive_file(self, zip_file_path: str, output_directory: str) -> Result[Dict[str, Any]]:
        """Extract a single archive file to output directory."""
        try:
            if not os.path.exists(zip_file_path):
                return Result.fail(
                    f"Archive file not found: {zip_file_path}",
                    "Archive file does not exist"
                )

            if not zipfile.is_zipfile(zip_file_path):
                return Result.fail(
                    f"Invalid ZIP file: {zip_file_path}",
                    "File is not a valid ZIP archive"
                )

            # Validate output directory using domain model
            try:
                output_dir = OutputDirectory(output_directory)
                output_dir.create_if_not_exists()
            except ValueError as e:
                return Result.fail(str(e), "Invalid output directory")

            extracted_files = []
            zip_filename = os.path.basename(zip_file_path)
            zip_name_base = os.path.splitext(zip_filename)[0]

            logger.info(f"Extracting {zip_filename} to {output_directory}")

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
                    new_file_path = Path(output_directory) / new_filename

                    # Write the file with the new name
                    with open(new_file_path, 'wb') as f:
                        f.write(file_data)

                    # Create archive file info
                    file_info = ArchiveFileInfo(
                        original_zip=zip_filename,
                        original_filename=original_name,
                        extracted_file=str(new_file_path),
                        filename=new_filename,
                        size_bytes=new_file_path.stat().st_size
                    )
                    extracted_files.append(file_info)

                    logger.debug(f"Renamed {original_name} to {new_filename}")

            logger.info(f"Successfully extracted {len(extracted_files)} files from {zip_filename}")

            return Result.ok({
                'extracted_files': extracted_files,
                'zip_file': zip_filename,
                'total_files': len(extracted_files),
                'output_directory': output_directory
            }, f"Successfully extracted {len(extracted_files)} files")

        except PermissionError as e:
            logger.error(f"Permission error extracting {zip_file_path}: {e}")
            return Result.fail(
                f"Permission denied: {str(e)}",
                "Insufficient permissions to extract archive"
            )
        except zipfile.BadZipFile as e:
            logger.error(f"Corrupted ZIP file {zip_file_path}: {e}")
            return Result.fail(
                f"Corrupted ZIP file: {str(e)}",
                "Archive file is corrupted or damaged"
            )
        except Exception as e:
            logger.error(f"Error extracting {zip_file_path}: {e}")
            return Result.fail(
                f"Extraction error: {str(e)}",
                "Failed to extract archive file"
            )

    def extract_multiple_archives(self, zip_file_paths: List[str], 
                                   output_directory: str) -> Result[Dict[str, Any]]:
        """Extract multiple archive files to output directory."""
        try:
            if not zip_file_paths:
                return Result.fail("No archive files provided", "Archive file list is empty")

            # Validate output directory
            try:
                output_dir = OutputDirectory(output_directory)
                output_dir.create_if_not_exists()
            except ValueError as e:
                return Result.fail(str(e), "Invalid output directory")

            all_extracted_files = []
            successful_extractions = 0
            failed_extractions = []

            logger.info(f"Extracting {len(zip_file_paths)} archive files to {output_directory}")

            for zip_file_path in zip_file_paths:
                try:
                    result = self.extract_archive_file(zip_file_path, output_directory)
                    
                    if result.success:
                        extracted_files = result.data['extracted_files']
                        all_extracted_files.extend(extracted_files)
                        successful_extractions += 1
                        logger.debug(f"Successfully extracted {len(extracted_files)} files from {os.path.basename(zip_file_path)}")
                    else:
                        failed_extractions.append({
                            'file': os.path.basename(zip_file_path),
                            'error': result.error
                        })
                        logger.error(f"Failed to extract {os.path.basename(zip_file_path)}: {result.error}")

                except Exception as e:
                    failed_extractions.append({
                        'file': os.path.basename(zip_file_path),
                        'error': str(e)
                    })
                    logger.error(f"Exception extracting {os.path.basename(zip_file_path)}: {e}")

            # Determine overall success
            total_files = len(zip_file_paths)
            success = successful_extractions > 0

            if success:
                message = f"Extracted {successful_extractions}/{total_files} archive files"
                if failed_extractions:
                    message += f", {len(failed_extractions)} failed"
                else:
                    message = f"Successfully extracted all {successful_extractions} archive files"
            else:
                message = f"Failed to extract any archive files ({len(failed_extractions)} failures)"

            logger.info(f"Multiple extraction completed: {message}")

            return Result.ok({
                'extracted_files': all_extracted_files,
                'successful_extractions': successful_extractions,
                'failed_extractions': failed_extractions,
                'total_archives': total_files,
                'total_extracted_files': len(all_extracted_files),
                'output_directory': output_directory
            }, message)

        except Exception as e:
            logger.error(f"Error in multiple archive extraction: {e}")
            return Result.fail(
                f"Multiple extraction error: {str(e)}",
                "Failed to extract multiple archive files"
            )

    def get_archive_info(self, zip_file_path: str) -> Result[Dict[str, Any]]:
        """Get information about an archive file."""
        try:
            if not os.path.exists(zip_file_path):
                return Result.fail(
                    f"Archive file not found: {zip_file_path}",
                    "Archive file does not exist"
                )

            if not zipfile.is_zipfile(zip_file_path):
                return Result.fail(
                    f"Invalid ZIP file: {zip_file_path}",
                    "File is not a valid ZIP archive"
                )

            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                file_list = []
                total_size = 0
                
                for member in zip_ref.namelist():
                    if not member.endswith('/'):  # Skip directories
                        info = zip_ref.getinfo(member)
                        file_list.append({
                            'name': member,
                            'size': info.file_size,
                            'compressed_size': info.compress_size,
                            'date_time': info.date_time
                        })
                        total_size += info.file_size

                archive_info = {
                    'filename': os.path.basename(zip_file_path),
                    'file_count': len(file_list),
                    'total_size': total_size,
                    'files': file_list,
                    'archive_path': zip_file_path
                }

                return Result.ok(archive_info, f"Archive contains {len(file_list)} files")

        except zipfile.BadZipFile as e:
            logger.error(f"Corrupted ZIP file {zip_file_path}: {e}")
            return Result.fail(
                f"Corrupted ZIP file: {str(e)}",
                "Archive file is corrupted or damaged"
            )
        except Exception as e:
            logger.error(f"Error reading archive info {zip_file_path}: {e}")
            return Result.fail(
                f"Archive info error: {str(e)}",
                "Failed to read archive information"
            )


def create_archive_file_extractor() -> ArchiveFileExtractor:
    """Factory function to create ArchiveFileExtractor."""
    return ArchiveFileExtractor()