"""
Input validators for Fluid ID conversion.
Each validator follows Single Responsibility Principle.
"""

from typing import Any
from core.interfaces import IValidator, Result


class FluidIdInputValidator(IValidator):
    """Validates SCADA Fluid ID input."""

    def validate(self, value: Any) -> Result[bool]:
        """Validate FID input format and constraints."""
        if value is None:
            return Result.fail("FluidId cannot be None", "Please provide a valid FID value")

        if not isinstance(value, str):
            return Result.fail("FluidId must be a string", "FID input must be text")

        value = value.strip()
        if not value:
            return Result.fail("FluidId cannot be empty", "Please enter a FID value")

        try:
            numeric_value = int(value)
            if numeric_value < 0:
                return Result.fail("FluidId must be non-negative", "FID cannot be negative")
        except ValueError:
            return Result.fail("FluidId must be numeric", "FID must be a valid number")

        return Result.ok(True, "FID input is valid")


class FluidNameInputValidator(IValidator):
    """Validates Fluid Name input."""

    VALID_CHARACTERS = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
        'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
    ]

    def validate(self, value: Any) -> Result[bool]:
        """Validate fluid name input format and characters."""
        if value is None:
            return Result.fail("FluidName cannot be None", "Please provide a valid fluid name")

        if not isinstance(value, str):
            return Result.fail("FluidName must be a string", "Fluid name input must be text")

        value = value.strip()
        if not value:
            return Result.fail("FluidName cannot be empty", "Please enter a fluid name")

        # Check for invalid characters
        upper_value = value.upper()
        for char in upper_value:
            if char not in self.VALID_CHARACTERS:
                return Result.fail(
                    f"Invalid character '{char}' in FluidName",
                    f"Character '{char}' is not allowed. Use only alphanumeric characters and spaces."
                )

        return Result.ok(True, "Fluid name input is valid")


class NonEmptyStringValidator(IValidator):
    """Validates that a string is not empty or None."""

    def __init__(self, field_name: str = "Value"):
        self._field_name = field_name

    def validate(self, value: Any) -> Result[bool]:
        """Validate that value is a non-empty string."""
        if value is None:
            return Result.fail(f"{self._field_name} cannot be None", f"Please provide a valid {self._field_name.lower()}")

        if not isinstance(value, str):
            return Result.fail(f"{self._field_name} must be a string", f"{self._field_name} must be text")

        if not value.strip():
            return Result.fail(f"{self._field_name} cannot be empty", f"Please enter a {self._field_name.lower()}")

        return Result.ok(True, f"{self._field_name} is valid")


class CompositeValidator(IValidator):
    """Validator that combines multiple validators using AND logic."""

    def __init__(self, *validators: IValidator):
        self._validators = validators

    def validate(self, value: Any) -> Result[bool]:
        """Validate using all validators. Fails if any validator fails."""
        for validator in self._validators:
            result = validator.validate(value)
            if not result.success:
                return result

        return Result.ok(True, "All validations passed")


# Factory functions for common validator combinations
def create_fid_validator() -> IValidator:
    """Create a complete FID validator."""
    return CompositeValidator(
        NonEmptyStringValidator("FluidId"),
        FluidIdInputValidator()
    )


def create_fluid_name_validator() -> IValidator:
    """Create a complete fluid name validator."""
    return CompositeValidator(
        NonEmptyStringValidator("FluidName"),
        FluidNameInputValidator()
    )
