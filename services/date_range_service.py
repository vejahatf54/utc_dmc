"""
Date Range Service for WUTC Application.
Provides centralized date range generation with frequency patterns.
Based on UTC_Core patterns for comprehensive date/time handling.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Union, Optional
from enum import Enum
import calendar
from logging_config import get_logger

logger = get_logger(__name__)


class FrequencyType(Enum):
    """Enumeration of supported frequency types."""
    HOURLY = "Hourly"
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"


class DateRangeService:
    """Service for generating date ranges with various frequency patterns."""

    @staticmethod
    def get_frequency_options() -> List[Dict[str, str]]:
        """Get list of available frequency options for UI components."""
        return [
            {"value": FrequencyType.HOURLY.value, "label": "Hourly"},
            {"value": FrequencyType.DAILY.value, "label": "Daily"},
            {"value": FrequencyType.WEEKLY.value, "label": "Weekly"},
            {"value": FrequencyType.MONTHLY.value, "label": "Monthly"}
        ]

    @staticmethod
    def validate_date_inputs(
        start_date: Union[str, date, datetime] = None,
        end_date: Union[str, date, datetime] = None,
        single_date: Union[str, date, datetime] = None,
        frequency: str = "Daily"
    ) -> Dict[str, Any]:
        """
        Validate date inputs and return processed date information.
        
        Args:
            start_date: Start date for range mode
            end_date: End date for range mode  
            single_date: Single date (will use start_date to current date)
            frequency: Frequency pattern for data points
            
        Returns:
            Dictionary containing validation results and processed dates
        """
        try:
            # Validate frequency
            if frequency not in [f.value for f in FrequencyType]:
                return {
                    'success': False,
                    'message': f'Invalid frequency: {frequency}. Must be one of: {[f.value for f in FrequencyType]}'
                }

            # Helper function to parse date
            def parse_date_input(date_input: Union[str, date, datetime]) -> date:
                if isinstance(date_input, str):
                    return datetime.strptime(date_input, '%Y-%m-%d').date()
                elif isinstance(date_input, datetime):
                    return date_input.date()
                elif isinstance(date_input, date):
                    return date_input
                else:
                    raise ValueError(f"Invalid date type: {type(date_input)}")

            if single_date:
                # Single date mode: from single_date to current date
                parsed_start = parse_date_input(single_date)
                parsed_end = date.today()
                
                if parsed_start > parsed_end:
                    return {
                        'success': False,
                        'message': 'Start date cannot be after current date'
                    }
                
                dates = DateRangeService.generate_date_range(
                    parsed_start, parsed_end, frequency)
                
                return {
                    'success': True,
                    'mode': 'single',
                    'dates': dates,
                    'start_date': parsed_start,
                    'end_date': parsed_end,
                    'frequency': frequency,
                    'message': f'Single date mode: {parsed_start} to {parsed_end} ({len(dates)} intervals)'
                }
                
            elif start_date and end_date:
                # Date range mode
                parsed_start = parse_date_input(start_date)
                parsed_end = parse_date_input(end_date)
                
                if parsed_start > parsed_end:
                    return {
                        'success': False,
                        'message': 'Start date cannot be after end date'
                    }
                
                dates = DateRangeService.generate_date_range(
                    parsed_start, parsed_end, frequency)
                
                return {
                    'success': True,
                    'mode': 'range',
                    'dates': dates,
                    'start_date': parsed_start,
                    'end_date': parsed_end,
                    'frequency': frequency,
                    'message': f'Date range mode: {parsed_start} to {parsed_end} ({len(dates)} intervals)'
                }
            else:
                return {
                    'success': False,
                    'message': 'Either single_date or both start_date and end_date must be provided'
                }

        except ValueError as e:
            return {
                'success': False,
                'message': f'Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error validating dates: {str(e)}'
            }

    @staticmethod
    def generate_date_range(
        start_date: Union[date, datetime], 
        end_date: Union[date, datetime], 
        frequency: str
    ) -> List[date]:
        """
        Generate list of dates based on frequency pattern.
        
        Args:
            start_date: Start date
            end_date: End date
            frequency: Frequency type
            
        Returns:
            List of dates based on frequency
        """
        # Convert to date objects if needed
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()

        dates = []
        current_date = start_date

        if frequency == FrequencyType.DAILY.value:
            while current_date <= end_date:
                dates.append(current_date)
                current_date += timedelta(days=1)
                
        elif frequency == FrequencyType.WEEKLY.value:
            while current_date <= end_date:
                dates.append(current_date)
                current_date += timedelta(weeks=1)
                
        elif frequency == FrequencyType.MONTHLY.value:
            while current_date <= end_date:
                dates.append(current_date)
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
                    
        elif frequency == FrequencyType.HOURLY.value:
            # For hourly, we return dates but note this is meant for datetime processing
            # The calling service should handle hourly intervals within each date
            while current_date <= end_date:
                dates.append(current_date)
                current_date += timedelta(days=1)
        else:
            # Default to daily
            logger.warning(f"Unknown frequency '{frequency}', defaulting to daily")
            while current_date <= end_date:
                dates.append(current_date)
                current_date += timedelta(days=1)

        return dates

    @staticmethod
    def generate_datetime_range(
        start_datetime: datetime, 
        end_datetime: datetime, 
        frequency: str
    ) -> List[datetime]:
        """
        Generate list of datetime objects based on frequency pattern.
        This is useful for services that need specific time intervals.
        
        Args:
            start_datetime: Start datetime
            end_datetime: End datetime
            frequency: Frequency type
            
        Returns:
            List of datetime objects based on frequency
        """
        timestamps = []
        current_time = start_datetime

        if frequency == FrequencyType.HOURLY.value:
            delta = timedelta(hours=1)
        elif frequency == FrequencyType.DAILY.value:
            delta = timedelta(days=1)
        elif frequency == FrequencyType.WEEKLY.value:
            delta = timedelta(weeks=1)
        elif frequency == FrequencyType.MONTHLY.value:
            # Approximate monthly as 30 days for datetime intervals
            delta = timedelta(days=30)
        else:
            # Default to daily
            logger.warning(f"Unknown frequency '{frequency}', defaulting to daily")
            delta = timedelta(days=1)

        while current_time <= end_datetime:
            timestamps.append(current_time)
            current_time += delta

        return timestamps

    @staticmethod
    def get_frequency_description(frequency: str) -> str:
        """Get human-readable description of frequency."""
        descriptions = {
            FrequencyType.HOURLY.value: "Every hour",
            FrequencyType.DAILY.value: "Every day",
            FrequencyType.WEEKLY.value: "Every week",
            FrequencyType.MONTHLY.value: "Every month"
        }
        return descriptions.get(frequency, "Unknown frequency")

    @staticmethod
    def calculate_estimated_intervals(
        start_date: Union[date, datetime], 
        end_date: Union[date, datetime], 
        frequency: str
    ) -> int:
        """
        Calculate estimated number of intervals for a date range and frequency.
        
        Args:
            start_date: Start date
            end_date: End date
            frequency: Frequency type
            
        Returns:
            Estimated number of intervals
        """
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()

        total_days = (end_date - start_date).days + 1

        if frequency == FrequencyType.HOURLY.value:
            return total_days * 24
        elif frequency == FrequencyType.DAILY.value:
            return total_days
        elif frequency == FrequencyType.WEEKLY.value:
            return max(1, total_days // 7)
        elif frequency == FrequencyType.MONTHLY.value:
            return max(1, total_days // 30)
        else:
            return total_days  # Default to daily
