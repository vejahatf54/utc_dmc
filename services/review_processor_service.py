"""
Review processor service - Implementation of IReviewProcessor interface.
Handles the execution of dreview.exe for processing Review files.
"""

from typing import Dict, Any, List
import os
import subprocess
import time
import threading
import psutil
from pathlib import Path

from core.interfaces import IReviewProcessor, Result
from domain.review_models import ReviewFilePath, ReviewTimeRange, ReviewPeekFile, ReviewConversionConstants
from logging_config import get_logger

logger = get_logger(__name__)


class ReviewProcessorService(IReviewProcessor):
    """Service for processing Review files using dreview.exe."""

    def __init__(self):
        """Initialize the Review processor service."""
        self._cancel_event = threading.Event()
        self._processes = []
        self._lock = threading.Lock()

    def process_review_file(self, review_file_path: str, output_csv_path: str,
                            start_time: str, end_time: str, peek_items: List[str] = None,
                            dump_all: bool = False, frequency: float = None) -> Result[Dict[str, Any]]:
        """Process a single Review file to CSV using dreview.exe."""
        try:
            # Validate input file
            review_path = ReviewFilePath(review_file_path)
            if not review_path.exists():
                return Result.fail(f"Review file not found: {review_file_path}", "Input file does not exist")

            # Validate output directory
            output_path = Path(output_csv_path)
            output_dir = output_path.parent
            if not output_dir.exists():
                return Result.fail(f"Output directory not found: {output_dir}", "Output directory does not exist")

            # Create and validate time range
            time_range = ReviewTimeRange(start_time, end_time)
            if not time_range.is_valid_range():
                return Result.fail("Invalid time range", "Start time must be before end time")

            # Create peek file object
            peek_file = ReviewPeekFile(peek_items or [])

            # Build dreview command
            command_result = self._build_dreview_command(
                review_path, output_path, time_range, peek_file, dump_all, frequency
            )
            if not command_result.success:
                return command_result

            # Execute dreview command
            start_processing_time = time.time()
            execution_result = self._execute_dreview_command(
                command_result.data, review_path.filename)
            processing_time = time.time() - start_processing_time

            if not execution_result.success:
                return execution_result

            # Verify output file was created
            if not output_path.exists():
                return Result.fail("Output CSV file was not created", "dreview.exe did not produce output")

            # Get output file size
            output_size = output_path.stat().st_size

            result_data = {
                'input_file': review_file_path,
                'output_file': str(output_path),
                'file_size_bytes': output_size,
                'processing_time_seconds': round(processing_time, 2),
                'success': True
            }

            return Result.ok(result_data, f"Successfully processed Review file: {review_path.filename}")

        except ValueError as e:
            logger.error(f"Invalid input parameters: {str(e)}")
            return Result.fail(str(e), "Invalid processing parameters")
        except Exception as e:
            logger.error(f"Error processing Review file: {str(e)}")
            return Result.fail(f"Processing error: {str(e)}", "Error during Review file processing")

    def validate_processing_options(self, start_time: str, end_time: str,
                                    peek_items: List[str] = None) -> Result[bool]:
        """Validate Review processing options."""
        try:
            # Validate time range
            time_range = ReviewTimeRange(start_time, end_time)
            if not time_range.is_valid_range():
                return Result.fail("Invalid time range", "Start time must be before end time")

            # Validate peek items
            peek_file = ReviewPeekFile(peek_items or [])

            return Result.ok(True, "Processing options are valid")

        except ValueError as e:
            logger.error(f"Invalid processing options: {str(e)}")
            return Result.fail(str(e), "Invalid processing options")
        except Exception as e:
            logger.error(f"Error validating processing options: {str(e)}")
            return Result.fail(f"Validation error: {str(e)}", "Error validating processing options")

    def cancel_processing(self) -> None:
        """Cancel ongoing processing operations."""
        logger.warning("Cancelling all running Review processing tasks...")
        self._cancel_event.set()

        with self._lock:
            for proc in list(self._processes):
                try:
                    self._kill_process_tree(proc.pid)
                except Exception as ex:
                    logger.error(f"Error terminating process {proc.pid}: {ex}")

            self._processes.clear()

    def _build_dreview_command(self, review_path: ReviewFilePath, output_path: Path,
                               time_range: ReviewTimeRange, peek_file: ReviewPeekFile,
                               dump_all: bool, frequency: float) -> Result[str]:
        """Build the dreview.exe command string."""
        try:
            start_formatted, end_formatted = time_range.format_for_dreview()

            # Build duration argument
            duration_arg = "" if dump_all else f"-DT={frequency}" if frequency else ""

            # Build peek argument
            peek_arg = peek_file.format_for_dreview()
            match_arg = f"-match=({peek_arg})" if peek_arg else ""

            # Build command parts (similar to working legacy implementation)
            cmd_parts = [
                'cmd.exe /C dreview.exe',
                f'"{review_path.value}"'
            ]

            if match_arg:
                cmd_parts.append(match_arg)

            cmd_parts.extend([
                f'-TBEGIN={start_formatted}',
                f'-TEND={end_formatted}'
            ])

            if duration_arg:
                cmd_parts.append(duration_arg)

            cmd_parts.append(f'> "{output_path}"')

            command = ' '.join(cmd_parts)

            logger.debug(f"Built dreview command: {command}")
            return Result.ok(command, "Successfully built dreview command")

        except Exception as e:
            logger.error(f"Error building dreview command: {str(e)}")
            return Result.fail(f"Command build error: {str(e)}", "Error building dreview command")

    def _execute_dreview_command(self, command: str, filename: str) -> Result[Dict[str, Any]]:
        """Execute the dreview command and handle the process."""
        proc = None
        try:
            # Start process
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            with self._lock:
                self._processes.append(proc)

            # Wait for process completion with cancellation check
            while proc.poll() is None:
                if self._cancel_event.is_set():
                    logger.info(
                        f"Cancellation requested, terminating processing of {filename}")
                    self._kill_process_tree(proc.pid)
                    return Result.fail("Processing cancelled", "Operation was cancelled by user")
                time.sleep(0.1)

            # Get process output
            stdout, stderr = proc.communicate()

            # Check return code
            if proc.returncode != 0:
                error_msg = f"dreview.exe failed for {filename}:\n{stderr}" if stderr else f"dreview.exe failed for {filename}"
                logger.error(error_msg)
                return Result.fail(error_msg, "dreview.exe execution failed")

            # Log output for debugging
            if stdout.strip():
                logger.info(f"dreview output for {filename}: {stdout.strip()}")
            if stderr.strip():
                logger.warning(
                    f"dreview warnings for {filename}: {stderr.strip()}")

            return Result.ok({
                'stdout': stdout.strip(),
                'stderr': stderr.strip(),
                'return_code': proc.returncode
            }, f"Successfully executed dreview for {filename}")

        except Exception as e:
            logger.error(f"Error executing dreview command: {str(e)}")
            return Result.fail(f"Execution error: {str(e)}", "Error executing dreview command")
        finally:
            if proc:
                with self._lock:
                    if proc in self._processes:
                        self._processes.remove(proc)

    @staticmethod
    def _kill_process_tree(pid: int) -> None:
        """Kill process and all children using psutil."""
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            logger.info(f"Killed process tree for PID {pid}")
        except psutil.NoSuchProcess:
            logger.info(f"Process {pid} already terminated")
        except Exception as ex:
            logger.error(f"Error killing process tree {pid}: {ex}")

    def _is_file_locked(self, filepath: Path) -> bool:
        """Check if a file is locked by trying to open it in exclusive mode."""
        try:
            with open(filepath, "a"):
                return False
        except IOError:
            return True
