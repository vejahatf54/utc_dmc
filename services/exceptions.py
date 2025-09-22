"""
Custom exception classes for the WUTC application services.
"""

from logging_config import get_logger

logger = get_logger(__name__)


class WUTCError(Exception):
    """Base exception class for WUTC application."""

    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

        # Log the exception
        logger.error(f"{self.__class__.__name__}: {message}")
        if details:
            logger.error(f"Details: {details}")


class ValidationError(WUTCError):
    """Raised when input validation fails."""
    pass


class DataNotFoundError(WUTCError):
    """Raised when requested data is not found."""
    pass


class DatabaseError(WUTCError):
    """Raised when database operations fail."""
    pass


class ConfigurationError(WUTCError):
    """Raised when configuration is invalid."""
    pass


class ProcessingError(WUTCError):
    """Raised when data processing operations fail."""
    pass


class ExportError(WUTCError):
    """Raised when data export operations fail."""
    pass


class ServiceError(WUTCError):
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
