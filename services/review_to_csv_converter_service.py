"""
Review to CSV converter service - Implementation of IReviewToCsvConverter interface.
Coordinates the complete Review to CSV conversion process.
"""

from typing import Dict, Any, List, Optional
import os
import threading
import time
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from core.interfaces import IReviewToCsvConverter, IReviewFileReader, IReviewProcessor, Result
from domain.review_models import (
    ReviewDirectoryPath, ReviewFilePath, ReviewTimeRange, ReviewPeekFile,
    ReviewProcessingOptions, ReviewConversionResult, ReviewConversionConstants
)
from logging_config import get_logger

logger = get_logger(__name__)


class ReviewToCsvConverterService(IReviewToCsvConverter):
    """Service for converting Review files to CSV format."""

    def __init__(self, file_reader: IReviewFileReader, processor: IReviewProcessor):
        """Initialize the converter service with dependencies."""
        self._file_reader = file_reader
        self._processor = processor
        self._cancel_event = threading.Event()
        self._executor = None
        self._futures = []
        self._lock = threading.Lock()

    def convert(self, input_value: Dict[str, Any]) -> Result[Dict[str, Any]]:
        """Convert input value to output format (implementation of IConverter)."""
        # Extract conversion parameters from input
        directory_path = input_value.get('directory_path')
        output_directory = input_value.get('output_directory')
        processing_options = input_value.get('processing_options', {})

        if not directory_path or not output_directory:
            return Result.fail("Missing required parameters: directory_path and output_directory")

        return self.convert_directory(directory_path, output_directory, processing_options)

    def convert_directory(self, review_directory_path: str, output_directory: str,
                          processing_options: Dict[str, Any] = None) -> Result[Dict[str, Any]]:
        """Convert all Review files in a directory to CSV format."""
        try:
            # Validate directory
            directory_path = ReviewDirectoryPath(review_directory_path)
            if not directory_path.exists():
                return Result.fail(f"Directory not found: {review_directory_path}", "Review directory does not exist")

            # Get all Review files
            review_files = directory_path.get_review_files()
            if not review_files:
                return Result.fail("No Review files found in directory", "Directory contains no .review files")

            # Convert to file paths list
            file_paths = [rf.value for rf in review_files]

            # Use convert_files method
            return self.convert_files(file_paths, output_directory, processing_options)

        except ValueError as e:
            logger.error(f"Invalid directory path: {str(e)}")
            return Result.fail(str(e), "Invalid directory path")
        except Exception as e:
            logger.error(f"Error converting directory: {str(e)}")
            return Result.fail(f"Directory conversion error: {str(e)}", "Error during directory conversion")

    def convert_files(self, review_file_paths: List[str], output_directory: str,
                      processing_options: Dict[str, Any] = None) -> Result[Dict[str, Any]]:
        """Convert specific Review files to CSV format."""
        try:
            if not review_file_paths:
                return Result.fail("No files provided", "No Review files to convert")

            # Validate output directory
            output_path = Path(output_directory)
            if not output_path.exists():
                return Result.fail(f"Output directory not found: {output_directory}", "Output directory does not exist")

            # Parse processing options
            options_result = self._parse_processing_options(
                processing_options or {})
            if not options_result.success:
                return options_result

            options = options_result.data

            # Validate files
            valid_files = []
            invalid_files = []

            for file_path in review_file_paths:
                validation_result = self._file_reader.validate_file(file_path)
                if validation_result.success:
                    valid_files.append(file_path)
                else:
                    invalid_files.append(
                        f"{Path(file_path).name}: {validation_result.error}")

            if not valid_files:
                return Result.fail("No valid Review files found", "All provided files are invalid")

            # Reset cancellation flag
            self._cancel_event.clear()

            # Process files
            start_time = time.time()
            processing_result = self._process_files_parallel(
                valid_files, output_path, options)
            processing_time = time.time() - start_time

            if not processing_result.success:
                return processing_result

            # Always create merged file (merge multiple files or rename single file)
            merge_result = None
            merged_file_path = ""
            if len(valid_files) >= 1:  # Changed from > 1 to >= 1
                merge_result = self._merge_csv_files(
                    output_path, options.merged_filename)
                if merge_result.success:
                    merged_file_path = merge_result.data['merged_file_path']
                else:
                    # If merge fails, the entire conversion should fail
                    return Result.fail(f"Merge failed: {merge_result.error}",
                                       "Failed to create merged CSV file - no individual CSV files were created")

            # Create result
            result_data = {
                'success': True,
                'output_directory': str(output_path),
                'processed_files_count': len(valid_files),
                'invalid_files_count': len(invalid_files),
                'invalid_files': invalid_files,
                'processing_time_seconds': round(processing_time, 2),
                'merged_file_path': merged_file_path,
                'warnings': invalid_files if invalid_files else []
            }

            message = f"Successfully converted {len(valid_files)} Review files to CSV"
            if invalid_files:
                message += f" ({len(invalid_files)} files were invalid)"

            return Result.ok(result_data, message)

        except Exception as e:
            logger.error(f"Error converting Review files: {str(e)}")
            return Result.fail(f"Conversion error: {str(e)}", "Error during Review files conversion")

    def get_directory_info(self, directory_path: str) -> Result[Dict[str, Any]]:
        """Get information about Review files in a directory."""
        try:
            directory = ReviewDirectoryPath(directory_path)
            if not directory.exists():
                return Result.fail(f"Directory not found: {directory_path}", "Directory does not exist")

            review_files = directory.get_review_files()

            # Get detailed info for each file
            files_info = []
            total_size = 0

            for review_file in review_files:
                info_result = self._file_reader.get_file_info(
                    review_file.value)
                if info_result.success:
                    file_info = info_result.data
                    files_info.append(file_info)
                    total_size += file_info['file_size_bytes']

            directory_info = {
                'directory_path': directory_path,
                'review_files_count': len(review_files),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'files': files_info
            }

            return Result.ok(directory_info, f"Found {len(review_files)} Review files in directory")

        except ValueError as e:
            logger.error(f"Invalid directory path: {str(e)}")
            return Result.fail(str(e), "Invalid directory path")
        except Exception as e:
            logger.error(f"Error getting directory info: {str(e)}")
            return Result.fail(f"Directory info error: {str(e)}", "Error getting directory information")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the Review to CSV conversion system."""
        try:
            system_info = ReviewConversionConstants.get_system_info()
            return Result.ok(system_info, "System information retrieved successfully")
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return Result.fail(f"System info error: {str(e)}", "Error getting system information")

    def cancel_conversion(self) -> Result[bool]:
        """Cancel ongoing conversion operations."""
        try:
            logger.warning("Cancelling Review to CSV conversion...")
            self._cancel_event.set()

            # Cancel processor operations
            self._processor.cancel_processing()

            # Cancel futures if executor is running
            with self._lock:
                for future in self._futures:
                    future.cancel()

                if self._executor:
                    self._executor.shutdown(wait=False, cancel_futures=True)

                self._futures.clear()

            return Result.ok(True, "Conversion cancellation requested successfully")

        except Exception as e:
            logger.error(f"Error cancelling conversion: {str(e)}")
            return Result.fail(f"Cancellation error: {str(e)}", "Error cancelling conversion")

    def _parse_processing_options(self, options_dict: Dict[str, Any]) -> Result[ReviewProcessingOptions]:
        """Parse processing options from dictionary."""
        try:
            # Extract required parameters
            start_time = options_dict.get('start_time')
            end_time = options_dict.get('end_time')

            if not start_time or not end_time:
                return Result.fail("Start time and end time are required", "Missing required time parameters")

            # Create time range
            time_range = ReviewTimeRange(start_time, end_time)

            # Extract peek file information
            peek_file_data = options_dict.get('peek_file', {})
            peek_file = ReviewPeekFile.from_uploaded_file(peek_file_data)

            # Extract other options
            dump_all = options_dict.get('dump_all', False)
            frequency_minutes = options_dict.get('frequency_minutes')
            merged_filename = options_dict.get(
                'merged_filename', ReviewConversionConstants.DEFAULT_MERGED_FILENAME)
            parallel_processing = options_dict.get('parallel_processing', True)

            # Create processing options
            processing_options = ReviewProcessingOptions(
                time_range=time_range,
                peek_file=peek_file,
                dump_all=dump_all,
                frequency_minutes=frequency_minutes,
                merged_filename=merged_filename,
                parallel_processing=parallel_processing
            )

            return Result.ok(processing_options, "Processing options parsed successfully")

        except Exception as e:
            logger.error(f"Error parsing processing options: {str(e)}")
            return Result.fail(f"Options parsing error: {str(e)}", "Error parsing processing options")

    def _process_files_parallel(self, file_paths: List[str], output_directory: Path,
                                options: ReviewProcessingOptions) -> Result[Dict[str, Any]]:
        """Process Review files in parallel."""
        try:
            if not options.parallel_processing:
                return self._process_files_sequential(file_paths, output_directory, options)

            # Start parallel processing
            with self._lock:
                self._executor = ThreadPoolExecutor()
                self._futures = []

            successful_files = []
            failed_files = []

            # Submit all tasks
            for file_path in file_paths:
                if self._cancel_event.is_set():
                    break

                future = self._executor.submit(
                    self._process_single_file, file_path, output_directory, options
                )
                with self._lock:
                    self._futures.append(future)

            # Collect results
            for future in as_completed(self._futures):
                if self._cancel_event.is_set():
                    logger.info("Processing cancelled")
                    break

                try:
                    result = future.result()
                    if result.success:
                        successful_files.append(result.data)
                    else:
                        failed_files.append(result.error)
                except Exception as e:
                    logger.error(f"Error processing file: {str(e)}")
                    failed_files.append(str(e))

            # Clean up
            with self._lock:
                if self._executor:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                self._futures.clear()

            if self._cancel_event.is_set():
                return Result.fail("Processing was cancelled", "Operation cancelled by user")

            if not successful_files and failed_files:
                return Result.fail(f"All files failed to process: {'; '.join(failed_files)}", "No files processed successfully")

            result_data = {
                'successful_files': successful_files,
                'failed_files': failed_files,
                'success_count': len(successful_files),
                'failure_count': len(failed_files)
            }

            return Result.ok(result_data, f"Processed {len(successful_files)} files successfully")

        except Exception as e:
            logger.error(f"Error in parallel processing: {str(e)}")
            return Result.fail(f"Parallel processing error: {str(e)}", "Error during parallel processing")

    def _process_files_sequential(self, file_paths: List[str], output_directory: Path,
                                  options: ReviewProcessingOptions) -> Result[Dict[str, Any]]:
        """Process Review files sequentially."""
        successful_files = []
        failed_files = []

        for file_path in file_paths:
            if self._cancel_event.is_set():
                break

            result = self._process_single_file(
                file_path, output_directory, options)
            if result.success:
                successful_files.append(result.data)
            else:
                failed_files.append(result.error)

        if self._cancel_event.is_set():
            return Result.fail("Processing was cancelled", "Operation cancelled by user")

        result_data = {
            'successful_files': successful_files,
            'failed_files': failed_files,
            'success_count': len(successful_files),
            'failure_count': len(failed_files)
        }

        return Result.ok(result_data, f"Processed {len(successful_files)} files successfully")

    def _process_single_file(self, file_path: str, output_directory: Path,
                             options: ReviewProcessingOptions) -> Result[Dict[str, Any]]:
        """Process a single Review file."""
        try:
            review_path = ReviewFilePath(file_path)
            output_file = output_directory / review_path.csv_filename

            # Process the file using the processor service
            result = self._processor.process_review_file(
                review_file_path=file_path,
                output_csv_path=str(output_file),
                start_time=options.time_range.start_time,
                end_time=options.time_range.end_time,
                peek_items=options.peek_file.peek_items,
                dump_all=options.dump_all,
                frequency=options.frequency_minutes
            )

            return result

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return Result.fail(f"File processing error: {str(e)}", f"Error processing {Path(file_path).name}")

    def _merge_csv_files(self, output_directory: Path, merged_filename: str) -> Result[Dict[str, Any]]:
        """Merge all CSV files in the directory into a single file."""
        try:
            csv_files = list(output_directory.glob("*.csv"))

            # Don't include the merged file itself if it already exists
            csv_files = [f for f in csv_files if f.name != merged_filename]

            if not csv_files:
                return Result.fail("No CSV files to merge", "No CSV files found for merging")

            df_list = []
            processed_files = []

            for csv_file in csv_files:
                try:
                    # Read CSV and remove units row (dreview.exe always outputs units as first data row)
                    df = pd.read_csv(
                        csv_file, on_bad_lines='skip', engine='python')

                    # Remove first row (index 0) which is always units in dreview.exe output
                    if len(df) > 0:
                        logger.info(f"Removing units row from {csv_file.name}")
                        df = df.drop(index=0).reset_index(drop=True)

                    if not df.empty:
                        df_list.append(df)
                        processed_files.append(csv_file.name)
                        logger.info(
                            f"Read CSV file: {csv_file.name} with {len(df)} rows")
                    else:
                        logger.warning(
                            f"CSV file {csv_file.name} is empty, skipping")
                except Exception as e:
                    logger.error(
                        f"Error reading CSV file {csv_file.name}: {e}")
                    continue

            if not df_list:
                return Result.fail("No valid CSV files could be read", "All CSV files failed to load")

            # Merge dataframes
            merged_df = pd.concat(df_list, ignore_index=True)

            # Remove duplicates
            initial_row_count = len(merged_df)
            merged_df = merged_df.drop_duplicates().reset_index(drop=True)
            final_row_count = len(merged_df)

            # Save merged file
            merged_path = output_directory / merged_filename
            merged_df.to_csv(merged_path, index=False)

            # Clean up individual CSV files
            for csv_file in csv_files:
                try:
                    csv_file.unlink()
                    logger.info(
                        f"Removed individual CSV file: {csv_file.name}")
                except Exception as e:
                    logger.warning(
                        f"Could not remove CSV file {csv_file.name}: {e}")

            result_data = {
                'merged_file_path': str(merged_path),
                'merged_filename': merged_filename,
                'processed_files': processed_files,
                'initial_rows': initial_row_count,
                'final_rows': final_row_count,
                'duplicates_removed': initial_row_count - final_row_count
            }

            message = f"Merged {len(processed_files)} CSV files into {merged_filename} ({final_row_count} rows)"
            if initial_row_count != final_row_count:
                message += f", removed {initial_row_count - final_row_count} duplicates"

            return Result.ok(result_data, message)

        except Exception as e:
            logger.error(f"Error merging CSV files: {str(e)}")
            return Result.fail(f"Merge error: {str(e)}", "Error merging CSV files")
