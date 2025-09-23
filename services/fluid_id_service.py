"""
Refactored Fluid ID Converter service following SOLID principles.
Uses dependency injection, domain models, and proper separation of concerns.
"""

from typing import Dict, Any
from core.interfaces import IFluidIdConverter, IValidator, Result
from domain.fluid_models import FluidId, FluidName, ConversionConstants
from validation.input_validators import create_fid_validator, create_fluid_name_validator


class FluidIdConverterService(IFluidIdConverter):
    """
    Service for converting between SCADA FID and Fluid Names.
    Follows Single Responsibility Principle and uses dependency injection.
    """

    def __init__(self, fid_validator: IValidator = None, fluid_name_validator: IValidator = None):
        """Initialize the service with optional validators."""
        self._fid_validator = fid_validator or create_fid_validator()
        self._fluid_name_validator = fluid_name_validator or create_fluid_name_validator()

    def convert(self, input_value: Any) -> Result[Any]:
        """
        Generic convert method - tries to determine input type and convert accordingly.
        This satisfies the IConverter interface.
        """
        if not isinstance(input_value, str):
            return Result.fail("Input must be a string", "Please provide a valid string input")

        input_value = input_value.strip()

        # Try to determine if it's a FID (numeric) or fluid name
        try:
            int(input_value)
            # It's numeric, treat as FID
            return self.fid_to_fluid_name(input_value)
        except ValueError:
            # It's not numeric, treat as fluid name
            return self.fluid_name_to_fid(input_value)

    def fid_to_fluid_name(self, fid: str) -> Result[str]:
        """Convert SCADA FID to Fluid Name."""
        # Validate input
        validation_result = self._fid_validator.validate(fid)
        if not validation_result.success:
            return Result.fail(validation_result.error, validation_result.message)

        try:
            # Create domain object
            fluid_id = FluidId(fid)

            # Perform conversion using domain logic
            fluid_name_value = self._convert_fid_to_name(
                fluid_id.numeric_value)

            return Result.ok(
                fluid_name_value,
                f"Converted FID '{fid}' to Fluid Name '{fluid_name_value}'"
            )

        except ValueError as e:
            return Result.fail(str(e), "Invalid FID format")
        except Exception as e:
            return Result.fail(f"Conversion error: {str(e)}", "An unexpected error occurred during conversion")

    def fluid_name_to_fid(self, fluid_name: str) -> Result[str]:
        """Convert Fluid Name to SCADA FID."""
        # Validate input
        validation_result = self._fluid_name_validator.validate(fluid_name)
        if not validation_result.success:
            return Result.fail(validation_result.error, validation_result.message)

        try:
            # Create domain object
            fluid_name_obj = FluidName(fluid_name)

            # Perform conversion using domain logic
            fid_value = self._convert_name_to_fid(fluid_name_obj)

            return Result.ok(
                str(fid_value),
                f"Converted Fluid Name '{fluid_name}' to FID '{fid_value}'"
            )

        except ValueError as e:
            return Result.fail(str(e), "Invalid fluid name format")
        except Exception as e:
            return Result.fail(f"Conversion error: {str(e)}", "An unexpected error occurred during conversion")

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the conversion system."""
        try:
            info = ConversionConstants.get_system_info()
            return Result.ok(info, "System information retrieved successfully")
        except Exception as e:
            return Result.fail(f"Error retrieving system info: {str(e)}", "Could not get system information")

    def _convert_fid_to_name(self, fid_value: int) -> str:
        """Convert numeric FID to fluid name string."""
        if fid_value == 0:
            return ConversionConstants.BASE_DIGITS[0]

        converted_number = []
        while fid_value != 0:
            converted_number.append(fid_value % ConversionConstants.BASIS)
            fid_value //= ConversionConstants.BASIS

        result = ''.join(
            ConversionConstants.BASE_DIGITS[num] for num in converted_number)
        # Reverse the string as per the original logic
        return result[::-1]

    def _convert_name_to_fid(self, fluid_name: FluidName) -> int:
        """Convert fluid name object to numeric FID."""
        normalized_name = fluid_name.normalized_value
        name_length = len(normalized_name)
        sum_value = 0

        for i, letter in enumerate(normalized_name):
            digit_index = ConversionConstants.BASE_DIGITS.index(letter)
            power = name_length - 1 - i
            sum_value += digit_index * (ConversionConstants.BASIS ** power)

        return sum_value


# Backward compatibility - create legacy-compatible service
class LegacyFluidIdConverterService:
    """
    Legacy-compatible wrapper that maintains the original API.
    This helps with gradual migration from the old service.
    """

    def __init__(self):
        self._service = FluidIdConverterService()

    def convert_fid_to_fluid_name(self, fid: str) -> Dict[str, Any]:
        """Convert FID to fluid name - legacy format."""
        result = self._service.fid_to_fluid_name(fid)

        if result.success:
            return {
                "success": True,
                "fluid_name": result.data,
                "message": result.message
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": result.message
            }

    def convert_fluid_name_to_fid(self, fluid_name: str) -> Dict[str, Any]:
        """Convert fluid name to FID - legacy format."""
        result = self._service.fluid_name_to_fid(fluid_name)

        if result.success:
            return {
                "success": True,
                "fid": result.data,
                "message": result.message
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": result.message
            }

    def get_conversion_info(self) -> Dict[str, Any]:
        """Get conversion info - legacy format."""
        result = self._service.get_system_info()

        if result.success:
            return {
                "success": True,
                "system_info": result.data,
                "message": result.message
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": result.message
            }
