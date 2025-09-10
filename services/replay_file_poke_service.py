import os
from datetime import datetime
from pathlib import Path
from typing import List, Iterable
from logging_config import get_logger

logger = get_logger(__name__)


class Poke:
    def __init__(self, sps_command: str, model_device: str, sps_attribute: str,
                 poke_value: str, poke_time: datetime, override_exp: str):
        self.sps_command = sps_command
        self.model_device = model_device
        self.sps_attribute = sps_attribute
        self.poke_value = poke_value
        self.poke_time = poke_time
        self.override_exp = override_exp

    def __eq__(self, other):
        if not isinstance(other, Poke):
            return False
        return (self.sps_command == other.sps_command and
                self.model_device == other.model_device and
                self.sps_attribute == other.sps_attribute and
                self.poke_value == other.poke_value and
                self.poke_time == other.poke_time and
                self.override_exp == other.override_exp)

    def __hash__(self):
        return hash((self.sps_command, self.model_device, self.sps_attribute,
                     self.poke_value, self.poke_time, self.override_exp))

    def to_statement(self) -> str:
        return (f"{self.sps_command} {self.model_device}:{self.sps_attribute}={self.poke_value}, "
                f"TIME=\"{self.poke_time:%y/%m/%d %H:%M:%S}\", OVERRIDE.EXPR={self.override_exp}")


class UtcReplayFilePokeExtractorService:
    def __init__(self):
        self._poke_statements: List[str] = []

    def process_replay_files(self, replay_files: List[str]) -> None:
        """
        Read replay files, extract valid poke statements, deduplicate, sort by time,
        and prepare final poke statements.
        """
        overrides = []

        for file_path in replay_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                overrides.extend(self._fetch_valid_overrides(lines))
            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {e}")

        unique_pokes = self._fetch_unique_pokes(overrides)
        self._poke_statements = [p.to_statement() for p in unique_pokes]

    def save_to_file(self, output_file: str) -> None:
        """
        Save processed poke statements to an .inc file.
        """
        if not self._poke_statements:
            logger.warning("No poke statements to save.")
            return

        Path(output_file).write_text("\n".join(self._poke_statements), encoding="utf-8")
        logger.info(f"Saved {len(self._poke_statements)} poke statements to {output_file}")
        # Silently save without logging

    @staticmethod
    def _fetch_valid_overrides(override_statements: Iterable[str]) -> List[str]:
        result = []
        for line in override_statements:
            x = line.strip().upper()
            if (x.startswith("POKE") or x.startswith("SET")) and "TIME=\"" in x and "D0" not in x and "V0" not in x:
                result.append(x)
        return result

    @staticmethod
    def _fetch_unique_pokes(list_of_override_statements: Iterable[str]) -> List[Poke]:
        pokes = []
        for item in list_of_override_statements:
            # remove system time suffix if present
            item = item.split("/* SYSTIME=")[0].strip()

            try:
                sps_command = item.split()[0].strip()
                model_device = item.split("=")[0].split(":")[0].split()[-1].strip().upper()
                sps_attribute = item.split("=")[0].split(":")[-1].strip().upper()
                poke_value = item.split(", TIME=")[0].split("=")[-1].replace('"', " ").strip().upper()
                poke_time_str = item.split(", TIME=")[1].split(",")[0].replace('"', " ").strip()
                poke_time = datetime.strptime(poke_time_str, "%y/%m/%d %H:%M:%S")
                override_exp = "YES" if ", OVERRIDE.EXPR=" in item else "NO"

                pokes.append(Poke(sps_command, model_device, sps_attribute,
                                  poke_value, poke_time, override_exp))
            except Exception as e:
                logger.warning(f"Skipping malformed line: {item} ({e})")

        unique_sorted = sorted(set(pokes), key=lambda p: p.poke_time)
        return unique_sorted

    def get_poke_statements(self) -> List[str]:
        return self._poke_statements
