"""
Fluid ID page controller following MVC pattern.
Handles UI logic and coordinates between UI components and business services.
"""

from typing import Dict, Any, Tuple
import dash_mantine_components as dmc
from core.interfaces import IPageController, IFluidIdConverter, Result
from components.bootstrap_icon import BootstrapIcon


class FluidIdPageController(IPageController):
    """Controller for Fluid ID converter page."""

    def __init__(self, converter_service: IFluidIdConverter):
        """Initialize controller with converter service."""
        self._converter_service = converter_service

    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle input changes and return UI updates."""
        if not value or value.strip() == "":
            return Result.ok({
                "fluid_name_value": "",
                "fid_value": "",
                "message": ""
            }, "Input cleared")

        try:
            if input_id == 'fid-input':
                return self._handle_fid_input(value.strip())
            elif input_id == 'fluid-name-input':
                return self._handle_fluid_name_input(value.strip())
            else:
                return Result.fail(f"Unknown input ID: {input_id}", "Invalid input source")

        except Exception as e:
            return Result.fail(f"Controller error: {str(e)}", "An unexpected error occurred")

    def _handle_fid_input(self, fid_value: str) -> Result[Dict[str, Any]]:
        """Handle FID input and convert to fluid name."""
        result = self._converter_service.fid_to_fluid_name(fid_value)

        if result.success:
            message = self._create_success_alert(
                f"Converted: {fid_value} → {result.data}")
            return Result.ok({
                "fluid_name_value": result.data,
                "fid_value": fid_value,
                "message": message
            }, "FID conversion successful")
        else:
            message = self._create_error_alert(result.error)
            return Result.ok({
                "fluid_name_value": "",
                "fid_value": fid_value,
                "message": message
            }, "FID conversion failed")

    def _handle_fluid_name_input(self, fluid_name_value: str) -> Result[Dict[str, Any]]:
        """Handle fluid name input and convert to FID."""
        result = self._converter_service.fluid_name_to_fid(fluid_name_value)

        if result.success:
            message = self._create_success_alert(
                f"Converted: {fluid_name_value} → {result.data}")
            return Result.ok({
                "fluid_name_value": fluid_name_value,
                "fid_value": result.data,
                "message": message
            }, "Fluid name conversion successful")
        else:
            message = self._create_error_alert(result.error)
            return Result.ok({
                "fluid_name_value": fluid_name_value,
                "fid_value": "",
                "message": message
            }, "Fluid name conversion failed")

    def _create_success_alert(self, message: str) -> dmc.Alert:
        """Create a success alert component."""
        return dmc.Alert(
            title="Conversion Successful",
            children=message,
            color="green",
            icon=BootstrapIcon(icon="check")
        )

    def _create_error_alert(self, error: str) -> dmc.Alert:
        """Create an error alert component."""
        return dmc.Alert(
            title="Conversion Error",
            children=error,
            color="red",
            icon=BootstrapIcon(icon="exclamation-circle")
        )

    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get system information for the help modal."""
        return self._converter_service.get_system_info()

    def handle_modal_toggle(self, n_clicks: int, current_opened: bool) -> bool:
        """Handle help modal toggle."""
        if n_clicks:
            return not current_opened
        return current_opened


class FluidIdUIResponseFormatter:
    """Formats controller responses for Dash callbacks."""

    @staticmethod
    def format_conversion_response(result: Result[Dict[str, Any]]) -> Tuple[str, str, Any]:
        """Format controller result for Dash callback return."""
        if result.success:
            data = result.data
            return (
                data.get("fluid_name_value", ""),
                data.get("fid_value", ""),
                data.get("message", "")
            )
        else:
            # Return error state
            return "", "", FluidIdUIResponseFormatter._create_error_message(result.error)

    @staticmethod
    def _create_error_message(error: str) -> dmc.Alert:
        """Create error message component."""
        return dmc.Alert(
            title="System Error",
            children=error,
            color="red",
            icon=BootstrapIcon(icon="exclamation-triangle")
        )
