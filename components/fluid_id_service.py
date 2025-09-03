"""
Fluid ID Converter service for DMC application.
Converts between SCADA FID (37-basis numeric) and Fluid Names (alphanumeric).
"""

from typing import Any, Dict


class FluidIdConverterService:
    """Service for converting between SCADA FID (37-basis numeric) and Fluid Names (alphanumeric)."""

    # Base 37 conversion constants and characters
    BASIS = 37
    BASE_DIGITS = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
        'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
    ]

    def convert_fid_to_fluid_name(self, fid: str) -> Dict[str, Any]:
        """Convert SCADA FID (numeric) to Fluid Name (alphanumeric)."""
        try:
            number_to_convert = int(fid)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": "Not a valid 37 basis number",
                "message": "FID must be a valid numeric value"
            }

        if number_to_convert < 0:
            return {
                "success": False,
                "error": "Number must be non-negative",
                "message": "FID cannot be negative"
            }

        if number_to_convert == 0:
            fluid_name_reversed = self.BASE_DIGITS[0]
            return {
                "success": True,
                "fluid_name": fluid_name_reversed,
                "message": f"Converted FID '{fid}' to Fluid Name '{fluid_name_reversed}'"
            }

        converted_number = []
        while number_to_convert != 0:
            converted_number.append(number_to_convert % self.BASIS)
            number_to_convert //= self.BASIS

        result = ''.join(self.BASE_DIGITS[num] for num in converted_number)
        # Reverse the string as per the original C# logic
        fluid_name_reversed = result[::-1]

        return {
            "success": True,
            "fluid_name": fluid_name_reversed,
            "message": f"Converted FID '{fid}' to Fluid Name '{fluid_name_reversed}'"
        }

    def convert_fluid_name_to_fid(self, fluid_name: str) -> Dict[str, Any]:
        """Convert Fluid Name (alphanumeric) to SCADA FID (numeric)."""
        try:
            fluid_name = fluid_name.upper().strip()
            if not fluid_name:
                return {
                    "success": False,
                    "error": "Fluid name cannot be empty",
                    "message": "Please enter a valid fluid name"
                }

            name_length = len(fluid_name)
            sum_value = 0

            # Pad with spaces if needed (like the C# version)
            if name_length == 1:
                fluid_name += "  "
                name_length = len(fluid_name)
            elif name_length == 2:
                fluid_name += " "
                name_length = len(fluid_name)

            for i, letter in enumerate(fluid_name):
                if letter not in self.BASE_DIGITS:
                    return {
                        "success": False,
                        "error": f"Invalid character '{letter}'",
                        "message": "Input should only contain alphanumeric characters and spaces"
                    }

                digit_index = self.BASE_DIGITS.index(letter)
                power = name_length - 1 - i
                sum_value += digit_index * (self.BASIS ** power)

            fid = str(sum_value)
            return {
                "success": True,
                "fid": fid,
                "message": f"Converted Fluid Name '{fluid_name.strip()}' to FID '{fid}'"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Conversion error: {str(e)}",
                "message": "An unexpected error occurred during conversion"
            }

    def get_conversion_info(self) -> Dict[str, Any]:
        """Get information about the conversion system."""
        return {
            "success": True,
            "system_info": {
                "basis": self.BASIS,
                "characters": "".join(self.BASE_DIGITS),
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
        }
