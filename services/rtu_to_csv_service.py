import os
import glob
import asyncio
import subprocess
from datetime import datetime
from collections import defaultdict
import pandas as pd
import logging
import threading

logger = logging.getLogger(__name__)


class RtuFileService:
    def __init__(self, dir_path: str, peek_list: str = "", id_width: int = 4):
        self.dir_path = dir_path
        self.peek_list_argument = peek_list
        self.rtu_file_names = []
        self.id_width = id_width
        self._cancel_event = threading.Event()
        self._active_processes = []
        self._process_lock = threading.Lock()

    def set_rtu_files(self, rtu_file_names):
        """Set the RTU filenames to process."""
        self.rtu_file_names = rtu_file_names

    def set_peek_file(self, peek_file):
        """Reads peek file and prepares argument string."""
        with open(peek_file, "r") as f:
            lines = [l.strip() for l in f if not l.startswith("#")]
        self.peek_list_argument = ",".join(lines)
    
    def cancel_processing(self):
        """Cancel all active processing operations."""
        self._cancel_event.set()
        
        # Kill all active drtu.exe processes
        with self._process_lock:
            for process in self._active_processes[:]:  # Copy list to avoid modification during iteration
                try:
                    if process.poll() is None:  # Process is still running
                        process.terminate()
                        # Give it a moment to terminate gracefully
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()  # Force kill if it doesn't terminate
                except Exception as e:
                    logger.warning(f"Error terminating process: {str(e)}")
            self._active_processes.clear()
    
    def reset_cancel_state(self):
        """Reset the cancellation state for new processing."""
        self._cancel_event.clear()
        with self._process_lock:
            self._active_processes.clear()

    def write_rtu_data_file_to_csv(self, rtu_file, start_time, end_time):
        """Run drtu.exe with arguments to generate .rtu file from .dt input."""
        # Check for cancellation before starting
        if self._cancel_event.is_set():
            raise asyncio.CancelledError("Processing was cancelled")
        
        base_name = os.path.splitext(rtu_file)[0]
        out_file = os.path.join(self.dir_path, base_name + ".rtu")

        # Format datetime strings to match drtu.exe expected format 'yy/mm/dd HH:MM:SS'
        start_str = start_time.strftime("'%y/%m/%d %H:%M:%S'")
        end_str = end_time.strftime("'%y/%m/%d %H:%M:%S'")
        
        # Construct command string
        cmd_string = (
            f'drtu.exe "{os.path.join(self.dir_path, rtu_file)}" '
            f'-match=({self.peek_list_argument}) -IDWIDTH={self.id_width} '
            f'-TBEGIN={start_str} -TEND={end_str} > "{out_file}"'
        )
        
        try:
            # Use Popen to track the process for cancellation
            process = subprocess.Popen(
                cmd_string, 
                shell=True, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Track the process for cancellation
            with self._process_lock:
                self._active_processes.append(process)
            
            try:
                # Wait for process with periodic cancellation checks
                stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
                
                # Remove from active processes
                with self._process_lock:
                    if process in self._active_processes:
                        self._active_processes.remove(process)
                
                # Check if cancelled during processing
                if self._cancel_event.is_set():
                    raise asyncio.CancelledError("Processing was cancelled")
                
                if process.returncode != 0:
                    logger.error(f"drtu.exe failed for {rtu_file}: {stderr}")
                    raise subprocess.CalledProcessError(process.returncode, cmd_string, stderr)
                    
            except subprocess.TimeoutExpired:
                process.terminate()
                with self._process_lock:
                    if process in self._active_processes:
                        self._active_processes.remove(process)
                raise subprocess.CalledProcessError(1, cmd_string, "Process timeout")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"drtu.exe failed for {rtu_file}: {e}")
            raise

    async def fetch_rtu_file_data(self, start_time, end_time):
        """Async entrypoint to process RTU files and merge them into a single CSV."""
        try:
            # Reset cancel state for new processing
            self.reset_cancel_state()
            
            # Check for cancellation before starting
            if self._cancel_event.is_set():
                raise asyncio.CancelledError("Processing was cancelled")
            
            # Process files with cancellation support
            tasks = []
            for f in self.rtu_file_names:
                if self._cancel_event.is_set():
                    break
                task = asyncio.to_thread(
                    self.write_rtu_data_file_to_csv, f, start_time, end_time
                )
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks)

            # Check for cancellation before tabulation
            if self._cancel_event.is_set():
                raise asyncio.CancelledError("Processing was cancelled")

            files = glob.glob(os.path.join(self.dir_path, "*.rtu"))

            # Always tabulate data - merge all RTU files into single CSV
            if files:
                self.tabulate_data(files)

        except asyncio.CancelledError:
            logger.info("RTU processing was cancelled")
            # Clean up any partial .rtu files
            for f in glob.glob(os.path.join(self.dir_path, "*.rtu")):
                try:
                    os.remove(f)
                except:
                    pass
            raise
        except Exception as e:
            logger.error("Error fetching RTU file data", exc_info=True)
            raise

    def tabulate_data(self, files):
        """Parse .rtu files -> deduplicate -> CSV -> merged dataframe."""
        dict_data = defaultdict(list)

        for file in files:
            try:
                with open(file, "r") as f:
                    lines = f.readlines()[1:]  # skip header

                for line in lines:
                    fields = line.split()
                    if len(fields) < 6:
                        continue
                    try:
                        timestamp = datetime.strptime(
                            f"{fields[1]} {fields[2]}", "%y/%m/%d %H:%M:%S"
                        )
                        value = fields[4] if fields[5] == "GOOD" else "NaN"
                        dict_data[fields[3]].append(f"{timestamp:%Y/%m/%d %H:%M:%S},{value}")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing line in {file}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error reading file {file}: {e}")
                continue

        if not dict_data:
            logger.warning("No data found in RTU files")
            return

        unique_dict = self.get_distinct_rows_dictionary(dict_data)
        self.write_unique_dict_to_csv(unique_dict)

        # delete .rtu after processing
        for f in glob.glob(os.path.join(self.dir_path, "*.rtu")):
            try:
                os.remove(f)
            except Exception as e:
                logger.warning(f"Could not remove {f}: {e}")

        # merge all CSVs
        csv_files = glob.glob(os.path.join(self.dir_path, "*.csv"))
        if not csv_files:
            logger.warning("No CSV files generated")
            return
            
        frames = []

        for file in csv_files:
            try:
                df = pd.read_csv(file).sort_values("timestamp")
                df.set_index("timestamp", inplace=True)
                frames.append(df)
            except Exception as e:
                logger.error(f"Error reading CSV {file}: {e}")
                continue

        if frames:
            merged = pd.concat(frames, axis=1).ffill().dropna(how="all")
            merged.to_csv(os.path.join(self.dir_path, "MergedDataFrame.csv"))

            # cleanup intermediate CSVs
            for f in csv_files:
                if "MergedDataFrame" not in f:
                    try:
                        os.remove(f)
                    except Exception as e:
                        logger.warning(f"Could not remove {f}: {e}")
        else:
            logger.error("No valid CSV files to merge")

    def write_unique_dict_to_csv(self, unique_dict):
        """Write dictionary to CSVs (one per key)."""
        for key, values in unique_dict.items():
            values = sorted(set(values))
            header = f"timestamp,{key}"
            values.insert(0, header)
            out_path = os.path.join(self.dir_path, f"{key}.csv")
            with open(out_path, "w") as f:
                f.write("\n".join(values))

    @staticmethod
    def get_distinct_rows_dictionary(dict_data):
        """Deduplicate rows by timestamp (last value wins)."""
        unique_dict = {}
        for key, items in dict_data.items():
            val_dict = {}
            for item in items:
                ts_str, val = item.split(",")
                ts = datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S")
                val_dict[ts] = val
            new_list = [
                f"{ts:%Y/%m/%d %H:%M:%S},{val}" for ts, val in sorted(val_dict.items())
            ]
            unique_dict[key] = new_list
        return unique_dict
