"""
Service for handling linefill data operations with Oracle database.
This service provides functionality to fetch linefill data from SCADA_CMT_PRD database.
"""

import oracledb
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
from pathlib import Path
from services.config_manager import get_config_manager
from services.exceptions import DatabaseConnectionError, QueryExecutionError


class LinefillService:
    """Service class for linefill data operations."""

    def __init__(self):
        """Initialize the linefill service with database configuration."""
        self.config_manager = get_config_manager()
        self._connection_string = None

    def _get_connection_string(self) -> str:
        """Get Oracle database connection string from config."""
        if not self._connection_string:
            self._connection_string = self.config_manager.get_oracle_connection_string()
        return self._connection_string

    def _get_database_connection(self):
        """Create and return Oracle database connection."""
        try:
            connection_string = self._get_connection_string()
            # Parse connection string: "Data Source=ewrv0405.cnpl.enbridge.com:1521/cmt_rep.CNPL.ENBRIDGE.COM;User Id=MAKELINEFILL_INTFAC;Password=Hu2vDX0wr12VfCdB;"
            parts = connection_string.split(';')
            data_source = None
            user_id = None
            password = None

            for part in parts:
                if part.strip().startswith('Data Source'):
                    data_source = part.split('=')[1].strip()
                elif part.strip().startswith('User Id'):
                    user_id = part.split('=')[1].strip()
                elif part.strip().startswith('Password'):
                    password = part.split('=')[1].strip()

            if not all([data_source, user_id, password]):
                raise DatabaseConnectionError(
                    "Invalid connection string format")

            # Create Oracle connection using oracledb (this was working before)
            connection = oracledb.connect(
                user=user_id,
                password=password,
                dsn=data_source
            )
            return connection

        except oracledb.Error as e:
            raise DatabaseConnectionError(
                f"Failed to connect to Oracle database: {str(e)}")
        except Exception as e:
            raise DatabaseConnectionError(
                f"Unexpected error connecting to database: {str(e)}")

    def _execute_query(self, sql_query: str) -> pd.DataFrame:
        """Execute SQL query using direct Oracle connection."""
        try:
            connection = self._get_database_connection()
            # Use pandas with warning suppression for Oracle connections
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                df = pd.read_sql(sql_query, connection)
            connection.close()
            return df
        except Exception as e:
            raise QueryExecutionError(f"Failed to execute query: {str(e)}")

    def fetch_list_of_distinct_lines_from_cmt(self) -> List[str]:
        """
        Fetch distinct line numbers from the linefill_pcs_xfr table.
        Returns a list of line numbers as strings (integers without decimals).
        """
        try:
            # Read the SQL query from file
            sql_file_path = Path(__file__).parent.parent / \
                "sql" / "DistinctLinesQuery.sql"
            with open(sql_file_path, 'r') as file:
                sql_query = file.read()

            # Execute query
            df = self._execute_query(sql_query)

            # Filter out NaN/null values and convert to integers, then to strings
            lines = []
            for line in df['LINE_NO'].tolist():
                try:
                    # Skip NaN, None, and empty values
                    if pd.notna(line) and line is not None and str(line).strip() != '':
                        # Convert to float first, then int to handle decimal numbers
                        line_num = int(float(line))
                        lines.append(str(line_num))
                except (ValueError, TypeError, OverflowError):
                    # Skip any values that can't be converted to integer
                    continue

            # Remove duplicates and sort numerically
            return sorted(set(lines), key=int)

        except Exception as e:
            raise QueryExecutionError(
                f"Failed to fetch distinct lines: {str(e)}")

    def fetch_linefill(self, line_no: str, linefill_start_time: datetime,
                       batch_boundary: Optional[str] = None) -> List[str]:
        """
        Fetch linefill data for a specific line and timestamp.

        Args:
            line_no: Line number to fetch data for
            linefill_start_time: Start time for linefill data
            batch_boundary: Optional batch boundary filter

        Returns:
            List of new_file_text strings from the query result
        """
        try:
            # Read the SQL query from file
            sql_file_path = Path(__file__).parent.parent / \
                "sql" / "LinefillQuery.sql"
            with open(sql_file_path, 'r') as file:
                sql_query = file.read()

            # Format the timestamp for Oracle query (HH24MI DD-Mon-YYYY)
            formatted_time = linefill_start_time.strftime('%H%M %d-%b-%Y')

            # Replace parameters in SQL query
            sql_query = sql_query.replace('%line%', line_no)
            sql_query = sql_query.replace(
                '%lineFillStartTime%', formatted_time)

            # Execute query using SQLAlchemy
            df = self._execute_query(sql_query)

            if df.empty:
                return []

            # Return the new_file_text column as a list
            return df['NEW_FILE_TEXT'].tolist()

        except Exception as e:
            raise QueryExecutionError(
                f"Failed to fetch linefill data for line {line_no}: {str(e)}")

    def fetch_multiple_linefill(self, line_numbers: List[str],
                                start_time: datetime, end_time: datetime,
                                frequency: str, batch_boundary: Optional[str] = None) -> Dict[str, List[Tuple[datetime, List[str]]]]:
        """
        Fetch linefill data for multiple lines across a time range.

        Args:
            line_numbers: List of line numbers to fetch data for
            start_time: Start of time range
            end_time: End of time range
            frequency: Frequency for data points ('Hourly', 'Daily', 'Weekly', 'Monthly')
            batch_boundary: Optional batch boundary filter

        Returns:
            Dictionary mapping line_no -> list of (timestamp, data) tuples
        """
        results = {}
        failed_lines = []

        # Generate timestamps based on frequency
        timestamps = self._generate_timestamps(start_time, end_time, frequency)

        for line_no in line_numbers:
            line_results = []
            line_failed = False

            for timestamp in timestamps:
                try:
                    data = self.fetch_linefill(
                        line_no, timestamp, batch_boundary)
                    if data:  # Only add if we got data
                        line_results.append((timestamp, data))
                except Exception as e:
                    print(
                        f"Failed to fetch data for line {line_no} at {timestamp}: {str(e)}")
                    line_failed = True
                    break

            if line_failed:
                failed_lines.append(line_no)
            else:
                results[line_no] = line_results

        if failed_lines:
            # Store failed lines for notification
            self._failed_lines = failed_lines

        return results

    def _generate_timestamps(self, start_time: datetime, end_time: datetime, frequency: str) -> List[datetime]:
        """Generate list of timestamps based on frequency."""
        timestamps = []
        current_time = start_time

        if frequency == 'Hourly':
            delta = timedelta(hours=1)
        elif frequency == 'Daily':
            delta = timedelta(days=1)
        elif frequency == 'Weekly':
            delta = timedelta(weeks=1)
        elif frequency == 'Monthly':
            # Approximate monthly as 30 days
            delta = timedelta(days=30)
        else:
            # Default to daily
            delta = timedelta(days=1)

        while current_time <= end_time:
            timestamps.append(current_time)
            current_time += delta

        return timestamps

    def get_failed_lines(self) -> List[str]:
        """Get list of lines that failed during the last fetch operation."""
        return getattr(self, '_failed_lines', [])

    def clear_failed_lines(self):
        """Clear the list of failed lines."""
        self._failed_lines = []

    def save_linefill_data(self, filename: str, content: str, save_directory: str = None) -> str:
        """
        Save linefill data to a text file.

        Args:
            filename: Name of the file (without extension)
            content: Content to save
            save_directory: Directory to save the file (optional)

        Returns:
            Full path of the saved file
        """
        try:
            if save_directory is None:
                # Use default directory or let user choose
                save_directory = Path.home() / "Downloads" / "LinefillData"

            save_path = Path(save_directory)
            save_path.mkdir(parents=True, exist_ok=True)

            # Ensure filename has .txt extension
            if not filename.endswith('.txt'):
                filename += '.txt'

            file_path = save_path / filename

            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)

            return str(file_path)

        except Exception as e:
            raise Exception(f"Failed to save file {filename}: {str(e)}")


# Singleton instance
_linefill_service = None


def get_linefill_service() -> LinefillService:
    """Get the singleton linefill service instance."""
    global _linefill_service
    if _linefill_service is None:
        _linefill_service = LinefillService()
    return _linefill_service
