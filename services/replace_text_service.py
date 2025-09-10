import csv
import os
import re
from pathlib import Path
from typing import List
from logging_config import get_logger

# Setup logger
logger = get_logger(__name__)

class ReplaceTextService:
    def __init__(self):
        self.csv_file_path: str | None = None
        self.folder_path: str | None = None

    def set_csv_file(self, csv_file_path: str):
        """Set the path to the CSV file containing substitutions."""
        if not os.path.isfile(csv_file_path):
            logger.error("CSV file does not exist: %s", csv_file_path)
            raise FileNotFoundError(f"CSV file does not exist: {csv_file_path}")
        self.csv_file_path = csv_file_path
        logger.debug("CSV file set to: %s", csv_file_path)

    def set_folder_path(self, folder_path: str):
        """Set the folder containing files to process."""
        if not os.path.isdir(folder_path):
            logger.error("Folder path does not exist: %s", folder_path)
            raise FileNotFoundError(f"Folder path does not exist: {folder_path}")
        self.folder_path = folder_path
        logger.debug("Folder path set to: %s", folder_path)

    def _load_substitutions(self) -> List[tuple[str, str]]:
        """Load substitution pairs from CSV."""
        substitutions = []
        with open(self.csv_file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) >= 2 and row[0].strip() and row[1].strip():
                    substitutions.append((row[0].strip(), row[1].strip()))
        if not substitutions:
            logger.warning("No valid substitutions found in CSV file.")
        return substitutions

    @staticmethod
    def _replace_text(content: str, old: str, new: str, match_case: bool) -> str:
        """Replace text in a string, respecting case sensitivity."""
        if match_case:
            return content.replace(old, new)
        else:
            pattern = re.compile(re.escape(old), re.IGNORECASE)
            return pattern.sub(new, content)

    def replace_in_files(self, extensions: list[str], match_case: bool = False):
        """Replace text in all files with the given extensions under the folder sequentially."""
        if not self.csv_file_path or not self.folder_path:
            raise ValueError("CSV file and folder path must be set before replacing text.")

        # Clean and validate extensions
        extensions = [ext.strip().lower() for ext in extensions if ext.strip()]
        if not extensions:
            raise ValueError("Please specify at least one valid file extension.")

        substitutions = self._load_substitutions()
        if not substitutions:
            return

        # Find files to process
        files_to_process = [
            f for f in Path(self.folder_path).rglob("*")
            if f.is_file() and f.suffix.lstrip(".").lower() in extensions
        ]
        if not files_to_process:
            logger.warning("No files found with the specified extensions: %s", extensions)
            return

        logger.debug("Found %d files to process.", len(files_to_process))

        # Process files sequentially
        for file_path in files_to_process:
            try:
                content = file_path.read_text(encoding="utf-8")
                for old, new in substitutions:
                    content = self._replace_text(content, old, new, match_case)
                file_path.write_text(content, encoding="utf-8")
                logger.debug("Processed file: %s", file_path)
            except Exception as e:
                logger.error("Failed to process file %s: %s", file_path, e)

        logger.debug("All files processed successfully.")


# -------------------------
# Example usage:
# -------------------------
# if __name__ == "__main__":
#     service = ReplaceTextService()
#     service.set_csv_file("substitutions.csv")
#     service.set_folder_path("C:/MyFiles")
#     service.replace_in_files(["txt", "md"], match_case=False)
