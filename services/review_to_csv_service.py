import os
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import threading
import time
import psutil  # pip install psutil
from logging_config import get_logger

logger = get_logger(__name__)


class ReviewCsvService:
    def __init__(self, folder_path: str, start_time: str, end_time: str, peek_list=None, dump_all=False, freq=None, merged_file="merged.csv"):
        """
        :param folder_path: Folder containing .review files
        :param start_time: Start time in 'yy/MM/dd_HH:mm:ss' format
        :param end_time: End time in 'yy/MM/dd_HH:mm:ss' format
        :param peek_list: List of items for -match argument
        :param dump_all: Boolean flag for duration text
        :param freq: Frequency for -DT if dump_all is False
        :param merged_file: Name of final merged CSV file
        """
        self.folder_path = Path(folder_path)
        self.start_time = start_time
        self.end_time = end_time
        self.peek_list = peek_list or []
        self.dump_all = dump_all
        self.freq = freq
        self.merged_file = merged_file

        # Cancellation and process tracking
        self._cancel_event = threading.Event()
        self._processes = []

        # Executor tracking
        self._executor = None
        self._futures = []

        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise ValueError(f"{folder_path} is not a valid directory")

        self.review_files = list(self.folder_path.glob("*.review"))
        if not self.review_files:
            logger.warning("No .review files found in the folder")

    def set_peek_file(self, peek_file_path: str):
        """Read peek file and extract arguments."""
        with open(peek_file_path, "r") as f:
            lines = [line.strip() for line in f if not line.startswith("#")]
            self.peek_list = lines

    def _write_review_to_csv(self, review_file: Path):
        """Run dreview.exe to generate CSV."""
        if self._cancel_event.is_set():
            logger.info("Skipping %s (cancel requested)", review_file)
            return

        csv_file = self.folder_path / f"{review_file.stem}.csv"

        if csv_file.exists() and self._is_file_locked(csv_file):
            raise IOError(f"File {csv_file} is used by another process")

        duration_text = "" if self.dump_all else f"-DT={self.freq or ''}"
        peek_arg = ",".join(self.peek_list)
        cmd = (
            f'cmd.exe /C dreview.exe "{review_file}" -match=({peek_arg}) '
            f'-TBEGIN={self.start_time} -TEND={self.end_time} {duration_text} > "{csv_file}"'
        )

        proc = None
        try:
            # Start process with proper PID tracking and redirect stdout/stderr to capture output
            proc = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self._processes.append(proc)

            while proc.poll() is None:
                if self._cancel_event.is_set():
                    logger.info(
                        "Cancellation requested, terminating %s", review_file)
                    self._kill_process_tree(proc.pid)
                    return
                time.sleep(0.1)

            stdout, stderr = proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(
                    f"dreview.exe failed for {review_file}:\n{stderr}")

            # Log the dreview output to log file instead of terminal
            if stdout.strip():
                logger.info("dreview output for %s: %s",
                            review_file, stdout.strip())
            if stderr.strip():
                logger.warning("dreview warnings for %s: %s",
                               review_file, stderr.strip())

            logger.info("Successfully processed %s", review_file)

        except Exception as ex:
            if csv_file.exists():
                csv_file.unlink()
            logger.error("Error processing file %s: %s", review_file, ex)
            raise
        finally:
            if proc and proc in self._processes:
                self._processes.remove(proc)

    @staticmethod
    def _is_file_locked(filepath: Path):
        """Check if a file is locked by trying to open it in exclusive mode."""
        try:
            with open(filepath, "a"):
                return False
        except IOError:
            return True

    def fetch_review_file_data(self):
        """Process all review files in parallel."""
        if not self.review_files:
            logger.warning("No review files to process")
            return

        self._cancel_event.clear()
        self._executor = ThreadPoolExecutor()

        try:
            self._futures = [
                self._executor.submit(self._write_review_to_csv, f)
                for f in self.review_files
            ]

            for future in as_completed(self._futures):
                if self._cancel_event.is_set():
                    logger.info("Fetch stopped due to cancellation")
                    break
                try:
                    future.result()  # propagate exceptions
                except Exception as ex:
                    logger.error("Error processing review file: %s", ex)

        except Exception as ex:
            logger.error("Error during fetch_review_file_data: %s",
                         ex, exc_info=True)
            raise
        finally:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._futures.clear()

    def cancel(self):
        """Cancel all running tasks and processes."""
        logger.warning("Cancelling all running tasks...")
        self._cancel_event.set()

        # Cancel futures
        for f in self._futures:
            f.cancel()

        # Kill all running processes
        for proc in list(self._processes):
            try:
                self._kill_process_tree(proc.pid)
            except Exception as ex:
                logger.error("Error terminating process %s: %s", proc.pid, ex)

        self._processes.clear()
        self._cleanup_partial_files()

    @staticmethod
    def _kill_process_tree(pid):
        """Kill process and all children using psutil."""
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            logger.info("Killed process tree for PID %s", pid)
        except psutil.NoSuchProcess:
            logger.info("Process %s already terminated", pid)
        except Exception as ex:
            logger.error("Error killing process tree %s: %s", pid, ex)

    def _cleanup_partial_files(self):
        """Remove partial CSV files created during cancelled operations."""
        for csv_file in self.folder_path.glob("*.csv"):
            # Don't remove the merged file if it exists
            if csv_file.name == self.merged_file:
                continue
            try:
                csv_file.unlink()
                logger.info("Removed partial file %s", csv_file)
            except Exception as ex:
                logger.warning(
                    "Could not remove partial file %s: %s", csv_file, ex)

    def clean_csv_files(self):
        """Remove second line from all CSV files in the folder (except merged file)."""
        for csv_file in self.folder_path.glob("*.csv"):
            # Skip the merged file during cleaning
            if csv_file.name == self.merged_file:
                continue

            try:
                lines = csv_file.read_text().splitlines()
                if len(lines) > 1:
                    lines.pop(1)
                    csv_file.write_text("\n".join(lines))
            except Exception as e:
                logger.warning(
                    "Could not clean CSV file %s: %s", csv_file.name, e)

    def merge_csv_files(self):
        """Merge all CSVs into a single file and clean up individual files."""
        csv_files = list(self.folder_path.glob("*.csv"))
        if not csv_files:
            logger.warning("No CSV files to merge")
            return

        df_list = []
        for f in csv_files:
            try:
                # Read with error handling for inconsistent field counts
                df = pd.read_csv(f, on_bad_lines='skip', engine='python')
                if not df.empty:
                    df_list.append(df)
                    logger.info(
                        f"Successfully read CSV file: {f.name} with {len(df)} rows")
                else:
                    logger.warning(f"CSV file {f.name} is empty, skipping")
            except Exception as e:
                logger.error(f"Error reading CSV file {f.name}: {e}")
                # Try alternative reading methods
                try:
                    df = pd.read_csv(f, sep=',', quoting=1,
                                     on_bad_lines='skip', engine='python')
                    if not df.empty:
                        df_list.append(df)
                        logger.info(
                            f"Successfully read CSV file with alternative method: {f.name}")
                except Exception as e2:
                    logger.error(
                        f"Failed to read CSV file {f.name} with alternative method: {e2}")
                    continue

        if not df_list:
            logger.error("No valid CSV files could be read for merging")
            return

        merged_df = pd.concat(df_list, ignore_index=True)

        # Remove duplicate rows to keep only distinct rows
        initial_row_count = len(merged_df)
        merged_df = merged_df.drop_duplicates().reset_index(drop=True)
        final_row_count = len(merged_df)

        if initial_row_count != final_row_count:
            logger.info(
                f"Removed {initial_row_count - final_row_count} duplicate rows, keeping {final_row_count} distinct rows")

        merged_path = self.folder_path / self.merged_file
        merged_df.to_csv(merged_path, index=False)
        logger.info("Merged CSV saved to %s with %d rows",
                    merged_path, len(merged_df))

        # Clean up individual CSV files after successful merge
        for csv_file in csv_files:
            if csv_file.name != self.merged_file:  # Don't delete the merged file
                try:
                    csv_file.unlink()
                    logger.info("Removed individual CSV file: %s",
                                csv_file.name)
                except Exception as e:
                    logger.warning(
                        "Could not remove CSV file %s: %s", csv_file.name, e)

    def run(self):
        """Complete workflow: fetch, clean, merge."""
        try:
            self.fetch_review_file_data()

            # Check if cancelled before continuing
            if self._cancel_event.is_set():
                logger.info("Processing cancelled before cleaning CSV files")
                return

            self.clean_csv_files()

            # Check if cancelled before merging
            if self._cancel_event.is_set():
                logger.info("Processing cancelled before merging CSV files")
                return

            self.merge_csv_files()

        except Exception as ex:
            logger.error(
                "Error during review processing workflow: %s", ex, exc_info=True)
            # Clean up partial files on error
            self._cleanup_partial_files()
            raise
