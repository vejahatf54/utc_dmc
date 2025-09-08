"""
Custom exception classes for the DMC application services.
"""

import logging

logger = logging.getLogger(__name__)


class DMCError(Exception):
    """Base exception class for DMC application."""

    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

        # Log the exception
        logger.error(f"{self.__class__.__name__}: {message}")
        if details:
            logger.error(f"Details: {details}")


class ValidationError(DMCError):
    """Raised when input validation fails."""
    pass


class DataNotFoundError(DMCError):
    """Raised when requested data is not found."""
    pass


class DatabaseError(DMCError):
    """Raised when database operations fail."""
    pass


class ConfigurationError(DMCError):
    """Raised when configuration is invalid."""
    pass


class ProcessingError(DMCError):
    """Raised when data processing operations fail."""
    pass


class ExportError(DMCError):
    """Raised when data export operations fail."""
    pass


class ServiceError(DMCError):
    """Raised when service layer operations fail."""
    pass


class DataProcessingError(ProcessingError):
    """Raised when data processing operations encounter specific errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class QueryExecutionError(DatabaseError):
    """Raised when database query execution fails."""
    pass
