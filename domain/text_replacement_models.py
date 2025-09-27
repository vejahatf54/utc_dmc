"""
Domain models for text replacement functionality.
Contains value objects and business entities following SOLID principles.
"""

import os
from typing import List, Tuple
from pathlib import Path
from core.interfaces import IValueObject, Result


class SubstitutionPair(IValueObject):
    """Value object representing a text substitution pair."""

    def __init__(self, old_text: str, new_text: str):
        if not isinstance(old_text, str):
            raise ValueError("Old text must be a string")
        if not isinstance(new_text, str):
            raise ValueError("New text must be a string")

        stripped_old_text = old_text.strip()
        if not stripped_old_text:
            raise ValueError("Old text must be a non-empty string")

        self._old_text = stripped_old_text
        self._new_text = new_text.strip()

    @property
    def old_text(self) -> str:
        """Get the text to be replaced."""
        return self._old_text

    @property
    def new_text(self) -> str:
        """Get the replacement text."""
        return self._new_text

    def is_valid(self) -> bool:
        """Check if the substitution pair is valid."""
        return bool(self._old_text)


class FileExtensionFilter(IValueObject):
    """Value object representing file extension filters."""

    def __init__(self, extensions: List[str]):
        if not extensions:
            raise ValueError("Extensions list cannot be empty")

        # Clean and normalize extensions
        cleaned_extensions = []
        for ext in extensions:
            if not isinstance(ext, str):
                continue
            # Remove dots, asterisks, and whitespace
            clean_ext = ext.strip().lstrip('*').lstrip('.').lower()
            if clean_ext:
                cleaned_extensions.append(clean_ext)

        if not cleaned_extensions:
            raise ValueError("No valid extensions provided")

        self._extensions = cleaned_extensions

    @property
    def extensions(self) -> List[str]:
        """Get the list of valid extensions."""
        return self._extensions.copy()

    def matches_file(self, file_path: str) -> bool:
        """Check if a file matches any of the extensions."""
        if not file_path:
            return False

        file_ext = Path(file_path).suffix.lstrip('.').lower()
        return file_ext in self._extensions


class DirectoryPath(IValueObject):
    """Value object representing a validated directory path."""

    def __init__(self, path: str):
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")

        normalized_path = os.path.normpath(path.strip())
        if not os.path.isdir(normalized_path):
            raise ValueError(f"Directory does not exist: {normalized_path}")

        self._path = normalized_path

    @property
    def path(self) -> str:
        """Get the validated directory path."""
        return self._path

    def find_files(self, extension_filter: FileExtensionFilter) -> List[str]:
        """Find all files in the directory matching the extension filter."""
        matching_files = []

        try:
            for file_path in Path(self._path).rglob("*"):
                if file_path.is_file() and extension_filter.matches_file(str(file_path)):
                    matching_files.append(str(file_path))
        except (OSError, PermissionError):
            # Handle access denied or other OS errors
            pass

        return matching_files


class TextReplacementConfig(IValueObject):
    """Value object representing the configuration for text replacement."""

    def __init__(self, directory: DirectoryPath, substitutions: List[SubstitutionPair],
                 extensions: FileExtensionFilter, match_case: bool = True):
        if not directory:
            raise ValueError("Directory is required")
        if not substitutions:
            raise ValueError("At least one substitution pair is required")
        if not extensions:
            raise ValueError("Extension filter is required")

        # Validate all substitutions
        valid_substitutions = [sub for sub in substitutions if sub.is_valid()]
        if not valid_substitutions:
            raise ValueError("No valid substitution pairs provided")

        self._directory = directory
        self._substitutions = valid_substitutions
        self._extensions = extensions
        self._match_case = match_case

    @property
    def directory(self) -> DirectoryPath:
        """Get the target directory."""
        return self._directory

    @property
    def substitutions(self) -> List[SubstitutionPair]:
        """Get the list of substitution pairs."""
        return self._substitutions.copy()

    @property
    def extensions(self) -> FileExtensionFilter:
        """Get the extension filter."""
        return self._extensions

    @property
    def match_case(self) -> bool:
        """Get the case matching preference."""
        return self._match_case

    def get_target_files(self) -> List[str]:
        """Get all files that should be processed."""
        return self._directory.find_files(self._extensions)


class TextReplacementResult(IValueObject):
    """Value object representing the result of a text replacement operation."""

    def __init__(self, processed_files: int, total_files: int, errors: List[str] = None):
        if processed_files < 0:
            raise ValueError("Processed files count cannot be negative")
        if total_files < 0:
            raise ValueError("Total files count cannot be negative")
        if processed_files > total_files:
            raise ValueError("Processed files cannot exceed total files")

        self._processed_files = processed_files
        self._total_files = total_files
        self._errors = errors or []

    @property
    def processed_files(self) -> int:
        """Get the number of successfully processed files."""
        return self._processed_files

    @property
    def total_files(self) -> int:
        """Get the total number of files found."""
        return self._total_files

    @property
    def errors(self) -> List[str]:
        """Get the list of errors encountered."""
        return self._errors.copy()

    @property
    def success_rate(self) -> float:
        """Get the success rate as a percentage."""
        if self._total_files == 0:
            return 100.0
        return (self._processed_files / self._total_files) * 100

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self._errors) > 0

    def to_summary(self) -> str:
        """Get a human-readable summary of the results."""
        if self._total_files == 0:
            return "No files found to process"

        summary = f"Processed {self._processed_files} of {self._total_files} files"
        if self.has_errors:
            summary += f" with {len(self._errors)} errors"

        return summary
