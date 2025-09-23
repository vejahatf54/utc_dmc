"""
Core interfaces and contracts for the WUTC application.
Defines abstract base classes that enforce SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar, Generic


# Result pattern for consistent error handling
T = TypeVar('T')


class Result(Generic[T]):
    """Result pattern implementation for error handling without exceptions."""

    def __init__(self, success: bool, data: T = None, error: str = None, message: str = None):
        self._success = success
        self._data = data
        self._error = error
        self._message = message

    @property
    def success(self) -> bool:
        return self._success

    @property
    def data(self) -> T:
        return self._data

    @property
    def error(self) -> str:
        return self._error

    @property
    def message(self) -> str:
        return self._message

    @classmethod
    def ok(cls, data: T, message: str = None) -> 'Result[T]':
        """Create a successful result."""
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(cls, error: str, message: str = None) -> 'Result[T]':
        """Create a failed result."""
        return cls(success=False, error=error, message=message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format for compatibility."""
        result = {
            "success": self._success,
            "message": self._message or ""
        }

        if self._success and self._data is not None:
            if hasattr(self._data, '__dict__'):
                result.update(self._data.__dict__)
            else:
                result["data"] = self._data

        if not self._success and self._error:
            result["error"] = self._error

        return result


# Domain Model Interface
class IValueObject(ABC):
    """Interface for value objects - immutable objects with value equality."""

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))


# Validation Interface
class IValidator(ABC):
    """Interface for input validation."""

    @abstractmethod
    def validate(self, value: Any) -> Result[bool]:
        """Validate the given value and return a Result."""
        pass


# Service Interfaces
class IConverter(ABC):
    """Interface for conversion services."""

    @abstractmethod
    def convert(self, input_value: Any) -> Result[Any]:
        """Convert input value to output format."""
        pass


class IFluidIdConverter(IConverter):
    """Interface for Fluid ID conversion operations."""

    @abstractmethod
    def fid_to_fluid_name(self, fid: str) -> Result[str]:
        """Convert SCADA FID to Fluid Name."""
        pass

    @abstractmethod
    def fluid_name_to_fid(self, fluid_name: str) -> Result[str]:
        """Convert Fluid Name to SCADA FID."""
        pass

    @abstractmethod
    def get_system_info(self) -> Result[Dict[str, Any]]:
        """Get information about the conversion system."""
        pass


# UI Controller Interface
class IPageController(ABC):
    """Interface for page controllers that handle UI logic."""

    @abstractmethod
    def handle_input_change(self, input_id: str, value: str) -> Result[Dict[str, Any]]:
        """Handle input changes and return UI updates."""
        pass


# Repository Pattern (for future database operations)
class IRepository(ABC, Generic[T]):
    """Generic repository interface for data access."""

    @abstractmethod
    def get_by_id(self, id: Any) -> Result[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    def save(self, entity: T) -> Result[T]:
        """Save entity."""
        pass


# Configuration Interface
class IConfigurable(ABC):
    """Interface for configurable components."""

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the component with given settings."""
        pass


# Factory Interface
class IFactory(ABC, Generic[T]):
    """Interface for factory classes."""

    @abstractmethod
    def create(self, *args, **kwargs) -> T:
        """Create an instance of type T."""
        pass
