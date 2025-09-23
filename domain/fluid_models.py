"""
Domain models for Fluid ID conversion.
Contains value objects that encapsulate business logic and validation.
"""

from typing import List
from core.interfaces import IValueObject, Result


class FluidId(IValueObject):
    """Value object representing a SCADA Fluid ID."""

    def __init__(self, value: str):
        if not isinstance(value, str):
            raise ValueError("FluidId value must be a string")

        self._validate_fid(value)
        self._value = value.strip()

    @property
    def value(self) -> str:
        """Get the FID value."""
        return self._value

    @property
    def numeric_value(self) -> int:
        """Get the numeric representation of the FID."""
        return int(self._value)

    def _validate_fid(self, value: str) -> None:
        """Validate FID format and constraints."""
        if not value or not value.strip():
            raise ValueError("FluidId cannot be empty")

        try:
            numeric_value = int(value.strip())
            if numeric_value < 0:
                raise ValueError("FluidId must be a non-negative integer")
        except ValueError as e:
            if "non-negative" in str(e):
                raise e
            raise ValueError("FluidId must be a valid numeric value")

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"FluidId('{self._value}')"


class FluidName(IValueObject):
    """Value object representing a Fluid Name."""

    # Valid characters for Fluid Names (same as BASE_DIGITS)
    VALID_CHARACTERS = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
        'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
    ]

    def __init__(self, value: str):
        if not isinstance(value, str):
            raise ValueError("FluidName value must be a string")

        self._validate_fluid_name(value)
        self._value = value.upper().strip()
        self._normalized_value = self._normalize_name(self._value)

    @property
    def value(self) -> str:
        """Get the original fluid name value."""
        return self._value

    @property
    def normalized_value(self) -> str:
        """Get the normalized fluid name (padded with spaces if needed)."""
        return self._normalized_value

    @property
    def length(self) -> int:
        """Get the length of the fluid name."""
        return len(self._value)

    def _validate_fluid_name(self, value: str) -> None:
        """Validate fluid name format and characters."""
        if not value or not value.strip():
            raise ValueError("FluidName cannot be empty")

        # Check for invalid characters
        upper_value = value.upper()
        for char in upper_value:
            if char not in self.VALID_CHARACTERS:
                raise ValueError(f"Invalid character '{char}' in FluidName. "
                                 f"Only alphanumeric characters and spaces are allowed.")

    def _normalize_name(self, value: str) -> str:
        """Normalize the fluid name by padding with spaces if needed."""
        # Apply the same padding logic as the original service
        length = len(value)
        if length == 1:
            return value + "  "  # Pad with 2 spaces
        elif length == 2:
            return value + " "   # Pad with 1 space
        return value

    def get_character_indices(self) -> List[int]:
        """Get the indices of each character in the VALID_CHARACTERS array."""
        return [self.VALID_CHARACTERS.index(char) for char in self._normalized_value]

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"FluidName('{self._value}')"


class ConversionConstants:
    """Constants used in fluid ID conversion calculations."""

    BASIS = 37
    BASE_DIGITS = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
        'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
    ]

    @classmethod
    def get_system_info(cls) -> dict:
        """Get information about the conversion system."""
        return {
            "basis": cls.BASIS,
            "characters": "".join(cls.BASE_DIGITS),
            "description": "37-basis numbering system for SCADA FID to Fluid Name conversion",
            "examples": [
                {"fid": "16292", "fluid_name": "AWB"},
                {"fid": "0", "fluid_name": "0"},
                {"fid": "1", "fluid_name": "1"}
            ],
            "rules": [
                "SCADA FID uses base-37 numbering system",
                "Fluid Names use characters: 0-9, space, A-Z",
                "Names are automatically padded with spaces if needed",
                "Conversion is bidirectional",
                "FID values must be non-negative integers"
            ]
        }
