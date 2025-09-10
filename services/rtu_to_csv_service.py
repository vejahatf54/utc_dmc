import os
import glob
import subprocess
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import psutil  # pip install psutil

logger = logging.getLogger(__name__)


class RtuFileService:
    def __init__(self, dir_path: str, peek_list: str = "", id_width: int = 4, max_workers: int = 4):
        self.dir_path = Path(dir_path)
        self.peek_list_argument = peek_list
        self.rtu_file_names = []  # .dt files
        self.id_width = id_width
        self.max_workers = max_workers

        # Cancellation and process tracking
        self._cancel_event = threading.Event()
        self._processes = []

        # Executor tracking
        self._executor = None
        self._futures = []

    # ------------------------------
    # Setup methods
    # ------------------------------
    def set_rtu_files(self):
        self.rtu_file_names = list(self.dir_path.glob("*.dt"))
        if not self.rtu_file_names:
            logger.warning(
                "No .dt files found in directory: %s", self.dir_path)

    def set_peek_file(self, peek_file):
        try:
            with open(peek_file, "r") as f:
                lines = [l.strip()
                         for l in f if l.strip() and not l.startswith("#")]
            self.peek_list_argument = ",".join(lines)
        except Exception as ex:
            logger.error("Failed to read peek file %s: %s", peek_file, ex)
            raise

    # ------------------------------
    # Core methods
    # ------------------------------
    def write_rtu_data_file_to_csv(self, rtu_file, start_time, end_time):
        if self._cancel_event.is_set():
            logger.info("Skipping %s (cancel requested)", rtu_file)
            return

        rtu_file = Path(rtu_file)
        out_file = self.dir_path / (rtu_file.stem + ".rtu")

        cmd = (f'cmd.exe /C "drtu.exe "{rtu_file}" ' f'-match=({self.peek_list_argument}) -IDWIDTH={self.id_width} ' f'-TBEGIN={start_time:%y/%m/%d_%H:%M:%S} ' f'-TEND={end_time:%y/%m/%d_%H:%M:%S} > "{out_file}""')

        proc = None
        try:
            # Start process without shell=True for safer PID tracking
            proc = subprocess.Popen(cmd, shell=True)
            self._processes.append(proc)

            while proc.poll() is None:
                if self._cancel_event.is_set():
                    logger.info(
                        "Cancellation requested, terminating %s", rtu_file)
                    self._kill_process_tree(proc.pid)
                    return
                time.sleep(0.1)

            if proc.returncode != 0:
                stdout, stderr = proc.communicate()
                raise RuntimeError(
                    f"drtu.exe failed for {rtu_file}:\n{stderr.decode()}")

            logger.info("Successfully processed %s", rtu_file)

        except Exception as ex:
            logger.error("Error running drtu.exe for %s: %s", rtu_file, ex)
            raise
        finally:
            if proc and proc in self._processes:
                self._processes.remove(proc)

    def fetch_rtu_file_data(self, start_time, end_time):
        self._cancel_event.clear()
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

        try:
            self._futures = [
                self._executor.submit(
                    self.write_rtu_data_file_to_csv, f, start_time, end_time)
                for f in self.rtu_file_names
            ]

            for future in as_completed(self._futures):
                if self._cancel_event.is_set():
                    logger.info("Fetch stopped due to cancellation")
                    break
                future.result()  # propagate exceptions

            if not self._cancel_event.is_set():
                files = list(self.dir_path.glob("*.rtu"))
                if files:
                    self.tabulate_data(files)
                else:
                    logger.warning("No .rtu files generated to tabulate")

        except Exception as ex:
            logger.error("Error during fetch_rtu_file_data: %s",
                         ex, exc_info=True)
            raise
        finally:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._futures.clear()

    def cancel(self):
        logger.warning("Cancelling all running tasks...")
        self._cancel_event.set()

        for f in self._futures:
            f.cancel()

        for proc in list(self._processes):
            try:
                self._kill_process_tree(proc.pid)
            except Exception as ex:
                logger.error("Error terminating process %s: %s", proc.pid, ex)

        self._processes.clear()
        self._cleanup_partial_files()

    # ------------------------------
    # Data handling
    # ------------------------------
    def tabulate_data(self, files):
        try:
            dict_data = defaultdict(list)
            for file in files:
                with open(file, "r") as f:
                    lines = f.readlines()[1:]  # skip header

                for line in lines:
                    fields = line.split()
                    if len(fields) < 6:
                        continue
                    try:
                        timestamp = datetime.strptime(
                            f"{fields[1]} {fields[2]}", "%y/%m/%d %H:%M:%S")
                        value = fields[4] if fields[5] == "GOOD" else "NaN"
                        dict_data[fields[3]].append(
                            f"{timestamp:%Y/%m/%d %H:%M:%S},{value}")
                    except Exception as ex:
                        logger.warning(
                            "Skipping malformed line in %s: %s", file, ex)

            unique_dict = self.get_distinct_rows_dictionary(dict_data)
            self.write_unique_dict_to_csv(unique_dict)

            for f in files:
                f.unlink()

            # merge CSVs
            csv_files = list(self.dir_path.glob("*.csv"))
            frames = []
            for file in csv_files:
                try:
                    df = pd.read_csv(file).sort_values("timestamp")
                    df.set_index("timestamp", inplace=True)
                    frames.append(df)
                except Exception as ex:
                    logger.error("Failed to load CSV %s: %s", file, ex)

            if frames:
                merged = pd.concat(frames, axis=1).ffill().dropna(how="all")
                merged.to_csv(self.dir_path / "MergedDataFrame.csv")

            for f in csv_files:
                if "MergedDataFrame" not in f.name:
                    f.unlink()

        except Exception as ex:
            logger.error("Tabulation failed: %s", ex, exc_info=True)
            raise

    def write_unique_dict_to_csv(self, unique_dict):
        for key, values in unique_dict.items():
            try:
                values = sorted(set(values))
                header = f"timestamp,{key}"
                values.insert(0, header)
                out_path = self.dir_path / f"{key}.csv"
                with open(out_path, "w") as f:
                    f.write("\n".join(values))
            except Exception as ex:
                logger.error("Failed to write CSV for %s: %s", key, ex)

    @staticmethod
    def get_distinct_rows_dictionary(dict_data):
        unique_dict = {}
        for key, items in dict_data.items():
            val_dict = {}
            for item in items:
                ts_str, val = item.split(",")
                ts = datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S")
                val_dict[ts] = val
            new_list = [f"{ts:%Y/%m/%d %H:%M:%S},{val}" for ts,
                        val in sorted(val_dict.items())]
            unique_dict[key] = new_list
        return unique_dict

    # ------------------------------
    # Cleanup
    # ------------------------------
    def _cleanup_partial_files(self):
        for ext in ("*.rtu", "*.csv"):
            for f in self.dir_path.glob(ext):
                try:
                    f.unlink()
                    logger.info("Removed partial file %s", f)
                except Exception:
                    pass

    @staticmethod
    def _kill_process_tree(pid):
        """Kill process and all children using psutil."""
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
        logger.info("Killed process tree for PID %s", pid)
