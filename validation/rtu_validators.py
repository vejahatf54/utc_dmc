"""
RTU Data validation layer following Single Responsibility Principle.
Contains validators for RTU data fetch operations.
"""

from typing import Any, List
from datetime import datetime, date
from pathlib import Path

from core.interfaces import IValidator, Result
from domain.rtu_models import (
    RtuDate, RtuDateRange, RtuServerFilter, 
    RtuLineSelection, RtuOutputDirectory
)
from logging_config import get_logger

logger = get_logger(__name__)


class RtuDateInputValidator(IValidator):
    """Validator for RTU date inputs following SRP."""

    def validate(self, date_value: Any) -> Result[RtuDate]:
        """
        Validate a single date input for RTU data fetching.
        
        Args:
            date_value: Date value to validate (string, date, or datetime)
            
        Returns:
            Result containing validated RtuDate domain object
        """
        try:
            if date_value is None:
                return Result.fail("Date value cannot be None")

            # Convert string to date if needed
            if isinstance(date_value, str):
                try:
                    # Try ISO format first (YYYY-MM-DD)
                    parsed_date = datetime.fromisoformat(date_value).date()
                except ValueError:
                    return Result.fail(f"Invalid date format: {date_value}. Expected YYYY-MM-DD format")
            elif isinstance(date_value, datetime):
                parsed_date = date_value.date()
            elif isinstance(date_value, date):
                parsed_date = date_value
            else:
                return Result.fail(f"Invalid date type: {type(date_value)}. Expected string, date, or datetime")

            # Create domain object (will validate business rules)
            rtu_date = RtuDate(parsed_date)
            return Result.ok(rtu_date, f"Valid RTU date: {rtu_date.display_format}")

        except ValueError as e:
            logger.warning(f"RTU date validation failed: {str(e)}")
            return Result.fail(f"Invalid RTU date: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in RTU date validation: {str(e)}")
            return Result.fail(f"Date validation error: {str(e)}")


class RtuDateRangeValidator(IValidator):
    """Validator for RTU date ranges following SRP."""

    def __init__(self, date_validator: RtuDateInputValidator = None):
        """Initialize with optional date validator dependency."""
        self._date_validator = date_validator or RtuDateInputValidator()

    def validate(self, date_range_data: Any) -> Result[RtuDateRange]:
        """
        Validate a date range for RTU data fetching.
        
        Args:
            date_range_data: Dictionary with 'start_date' and optional 'end_date'
            
        Returns:
            Result containing validated RtuDateRange domain object
        """
        try:
            if not isinstance(date_range_data, dict):
                return Result.fail("Date range data must be a dictionary")

            start_date_value = date_range_data.get('start_date')
            end_date_value = date_range_data.get('end_date')

            # Validate start date
            start_result = self._date_validator.validate(start_date_value)
            if not start_result.success:
                return Result.fail(f"Invalid start date: {start_result.error}")

            # Validate end date if provided
            end_date_obj = None
            if end_date_value is not None:
                end_result = self._date_validator.validate(end_date_value)
                if not end_result.success:
                    return Result.fail(f"Invalid end date: {end_result.error}")
                end_date_obj = end_result.data.value

            # Create domain object (will validate range rules)
            date_range = RtuDateRange(start_result.data.value, end_date_obj)
            return Result.ok(date_range, f"Valid RTU date range: {str(date_range)}")

        except ValueError as e:
            logger.warning(f"RTU date range validation failed: {str(e)}")
            return Result.fail(f"Invalid RTU date range: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in RTU date range validation: {str(e)}")
            return Result.fail(f"Date range validation error: {str(e)}")


class RtuLineSelectionValidator(IValidator):
    """Validator for RTU pipeline line selection following SRP."""

    def validate(self, line_ids: Any) -> Result[RtuLineSelection]:
        """
        Validate pipeline line selection for RTU data fetching.
        
        Args:
            line_ids: List of line ID strings
            
        Returns:
            Result containing validated RtuLineSelection domain object
        """
        try:
            if line_ids is None:
                return Result.fail("Line selection cannot be None")

            if not isinstance(line_ids, list):
                return Result.fail("Line selection must be a list")

            if len(line_ids) == 0:
                return Result.fail("At least one pipeline line must be selected")

            # Validate each line ID
            for line_id in line_ids:
                if not isinstance(line_id, str):
                    return Result.fail(f"Line ID must be a string: {line_id}")
                if not line_id.strip():
                    return Result.fail("Line IDs cannot be empty")

            # Create domain object (will validate line ID rules)
            line_selection = RtuLineSelection(line_ids)
            return Result.ok(line_selection, f"Valid line selection: {str(line_selection)}")

        except ValueError as e:
            logger.warning(f"RTU line selection validation failed: {str(e)}")
            return Result.fail(f"Invalid line selection: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in RTU line selection validation: {str(e)}")
            return Result.fail(f"Line selection validation error: {str(e)}")


class RtuOutputDirectoryValidator(IValidator):
    """Validator for RTU output directory following SRP."""

    def validate(self, directory_path: Any) -> Result[RtuOutputDirectory]:
        """
        Validate output directory for RTU data fetching.
        
        Args:
            directory_path: Directory path string
            
        Returns:
            Result containing validated RtuOutputDirectory domain object
        """
        try:
            if directory_path is None:
                return Result.fail("Output directory cannot be None")

            # Convert Path objects to strings
            if hasattr(directory_path, '__fspath__'):  # Path-like object
                directory_path = str(directory_path)
            elif not isinstance(directory_path, str):
                return Result.fail("Output directory must be a string or Path object")

            if not directory_path.strip():
                return Result.fail("Output directory cannot be empty")

            # Create domain object (will validate directory rules)
            output_dir = RtuOutputDirectory(directory_path)
            
            # Additional validation for accessibility
            if not output_dir.is_writable:
                return Result.fail(f"Output directory is not writable: {directory_path}")

            return Result.ok(output_dir, f"Valid output directory: {output_dir.path_str}")

        except ValueError as e:
            logger.warning(f"RTU output directory validation failed: {str(e)}")
            return Result.fail(f"Invalid output directory: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in RTU output directory validation: {str(e)}")
            return Result.fail(f"Output directory validation error: {str(e)}")


class RtuServerFilterValidator(IValidator):
    """Validator for RTU server filter patterns following SRP."""

    def validate(self, filter_pattern: Any) -> Result[RtuServerFilter]:
        """
        Validate server filter pattern for RTU data fetching.
        
        Args:
            filter_pattern: Server filter pattern string (can be None for no filter)
            
        Returns:
            Result containing validated RtuServerFilter domain object
        """
        try:
            # Allow None or empty string (no filtering)
            if filter_pattern is None or (isinstance(filter_pattern, str) and not filter_pattern.strip()):
                server_filter = RtuServerFilter(None)
                return Result.ok(server_filter, "No server filter (all servers)")

            if not isinstance(filter_pattern, str):
                return Result.fail("Server filter must be a string or None")

            # Create domain object (will validate pattern rules)
            server_filter = RtuServerFilter(filter_pattern)
            return Result.ok(server_filter, f"Valid server filter: {str(server_filter)}")

        except ValueError as e:
            logger.warning(f"RTU server filter validation failed: {str(e)}")
            return Result.fail(f"Invalid server filter: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in RTU server filter validation: {str(e)}")
            return Result.fail(f"Server filter validation error: {str(e)}")


class RtuParallelWorkersValidator(IValidator):
    """Validator for parallel workers configuration following SRP."""

    def __init__(self, min_workers: int = 1, max_workers: int = 8):
        """Initialize with worker limits."""
        self._min_workers = min_workers  
        self._max_workers = max_workers

    def validate(self, workers_value: Any) -> Result[int]:
        """
        Validate parallel workers configuration.
        
        Args:
            workers_value: Number of parallel workers
            
        Returns:
            Result containing validated worker count
        """
        try:
            if workers_value is None:
                # Use default value
                return Result.ok(4, "Using default parallel workers: 4")

            if not isinstance(workers_value, (int, float)):
                return Result.fail("Parallel workers must be a number")

            workers = int(workers_value)

            if workers < self._min_workers:
                return Result.fail(f"Parallel workers must be at least {self._min_workers}")

            if workers > self._max_workers:
                return Result.fail(f"Parallel workers cannot exceed {self._max_workers}")

            return Result.ok(workers, f"Valid parallel workers: {workers}")

        except (ValueError, TypeError) as e:
            logger.warning(f"RTU parallel workers validation failed: {str(e)}")
            return Result.fail(f"Invalid parallel workers value: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in RTU parallel workers validation: {str(e)}")
            return Result.fail(f"Parallel workers validation error: {str(e)}")


class CompositeRtuValidator(IValidator):
    """Composite validator for complete RTU fetch request following SRP."""

    def __init__(self, 
                 date_validator: RtuDateInputValidator = None,
                 date_range_validator: RtuDateRangeValidator = None,
                 line_validator: RtuLineSelectionValidator = None,
                 directory_validator: RtuOutputDirectoryValidator = None,
                 filter_validator: RtuServerFilterValidator = None,
                 workers_validator: RtuParallelWorkersValidator = None):
        """Initialize with validator dependencies."""
        self._date_validator = date_validator or RtuDateInputValidator()
        self._date_range_validator = date_range_validator or RtuDateRangeValidator(self._date_validator)
        self._line_validator = line_validator or RtuLineSelectionValidator()
        self._directory_validator = directory_validator or RtuOutputDirectoryValidator()
        self._filter_validator = filter_validator or RtuServerFilterValidator()
        self._workers_validator = workers_validator or RtuParallelWorkersValidator()

    def validate(self, fetch_request: Any) -> Result[dict]:
        """
        Validate complete RTU fetch request.
        
        Args:
            fetch_request: Dictionary containing all fetch parameters
            
        Returns:
            Result containing validated domain objects
        """
        try:
            if not isinstance(fetch_request, dict):
                return Result.fail("Fetch request must be a dictionary")

            validation_results = {}
            errors = []

            # Validate date mode and dates
            mode = fetch_request.get('mode', 'single')
            if mode == 'single':
                single_date = fetch_request.get('single_date')
                date_result = self._date_validator.validate(single_date)
                if date_result.success:
                    # Create date range from single date to today
                    date_range = RtuDateRange(date_result.data.value)
                    validation_results['date_range'] = date_range
                else:
                    errors.append(f"Single date: {date_result.error}")
            else:  # range mode
                date_range_data = {
                    'start_date': fetch_request.get('start_date'),
                    'end_date': fetch_request.get('end_date')
                }
                range_result = self._date_range_validator.validate(date_range_data)
                if range_result.success:
                    validation_results['date_range'] = range_result.data
                else:
                    errors.append(f"Date range: {range_result.error}")

            # Validate line selection
            line_ids = fetch_request.get('selected_lines', [])
            line_result = self._line_validator.validate(line_ids)
            if line_result.success:
                validation_results['line_selection'] = line_result.data
            else:
                errors.append(f"Line selection: {line_result.error}")

            # Validate output directory
            output_dir = fetch_request.get('output_directory')
            dir_result = self._directory_validator.validate(output_dir)
            if dir_result.success:
                validation_results['output_directory'] = dir_result.data
            else:
                errors.append(f"Output directory: {dir_result.error}")

            # Validate server filter (optional)
            server_filter = fetch_request.get('server_filter')
            filter_result = self._filter_validator.validate(server_filter)
            if filter_result.success:
                validation_results['server_filter'] = filter_result.data
            else:
                errors.append(f"Server filter: {filter_result.error}")

            # Validate parallel workers
            workers = fetch_request.get('max_parallel_workers', 4)
            workers_result = self._workers_validator.validate(workers)
            if workers_result.success:
                validation_results['max_parallel_workers'] = workers_result.data
            else:
                errors.append(f"Parallel workers: {workers_result.error}")

            # Return results
            if errors:
                return Result.fail(f"Validation failed: {'; '.join(errors)}")
            else:
                return Result.ok(validation_results, "All fetch request parameters validated successfully")

        except Exception as e:
            logger.error(f"Unexpected error in composite RTU validation: {str(e)}")
            return Result.fail(f"Validation error: {str(e)}")

    def validate_all(self, inputs: dict) -> Result[dict]:
        """Alias for main validate method for backward compatibility."""
        return self.validate(inputs)

    def validate_dates(self, start_date: Any, end_date: Any = None) -> Result[RtuDateRange]:
        """Validate date range specifically."""
        date_range_data = {'start_date': start_date}
        if end_date is not None:
            date_range_data['end_date'] = end_date
        
        return self._date_range_validator.validate(date_range_data)

    def validate_lines(self, lines: Any) -> Result[RtuLineSelection]:
        """Validate line selection specifically."""
        return self._line_validator.validate(lines)

    def validate_directory(self, directory: Any) -> Result[RtuOutputDirectory]:
        """Validate output directory specifically."""
        return self._directory_validator.validate(directory)


# Factory functions for creating pre-configured validators
def create_rtu_date_validator() -> RtuDateInputValidator:
    """Create a pre-configured RTU date validator."""
    return RtuDateInputValidator()


def create_rtu_date_range_validator() -> RtuDateRangeValidator:
    """Create a pre-configured RTU date range validator."""
    date_validator = create_rtu_date_validator()
    return RtuDateRangeValidator(date_validator)


def create_rtu_line_validator() -> RtuLineSelectionValidator:
    """Create a pre-configured RTU line selection validator."""
    return RtuLineSelectionValidator()


def create_rtu_directory_validator() -> RtuOutputDirectoryValidator:
    """Create a pre-configured RTU output directory validator."""
    return RtuOutputDirectoryValidator()


def create_rtu_server_filter_validator() -> RtuServerFilterValidator:
    """Create a pre-configured RTU server filter validator."""
    return RtuServerFilterValidator()


def create_rtu_workers_validator() -> RtuParallelWorkersValidator:
    """Create a pre-configured RTU parallel workers validator."""
    return RtuParallelWorkersValidator()


def create_composite_rtu_validator() -> CompositeRtuValidator:
    """Create a pre-configured composite RTU validator with all dependencies."""
    date_validator = create_rtu_date_validator()
    date_range_validator = create_rtu_date_range_validator()
    line_validator = create_rtu_line_validator()
    directory_validator = create_rtu_directory_validator()
    filter_validator = create_rtu_server_filter_validator()
    workers_validator = create_rtu_workers_validator()
    
    return CompositeRtuValidator(
        date_validator=date_validator,
        date_range_validator=date_range_validator,
        line_validator=line_validator,
        directory_validator=directory_validator,
        filter_validator=filter_validator,
        workers_validator=workers_validator
    )