"""
Service for handling fluid properties data operations with Oracle database.
This service provides functionality to fetch fluid properties and commodities data from SCADA_CMT_PRD database.
"""

import oracledb
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
from pathlib import Path
from services.config_manager import get_config_manager
from services.exceptions import DatabaseConnectionError, QueryExecutionError


class FluidPropertiesService:
    """Service class for fluid properties and commodities data operations."""

    def __init__(self):
        """Initialize the fluid properties service with database configuration."""
        self.config_manager = get_config_manager()
        self._connection_string = None

        # Get property type mappings from config
        test_ids_config = self.config_manager.get_fluid_properties_test_ids()
        units_config = self.config_manager.get_fluid_properties_units()

        self.property_mappings = {
            'Density': {
                'test_ids': test_ids_config.get('density', [50, 71, 106, 158, 160, 229, 274, 277, 279]),
                'unit': units_config.get('density', 'kg/m3')
            },
            'Viscosity': {
                'test_ids': test_ids_config.get('viscosity', [65, 66, 67, 68, 69, 222, 224, 226, 228, 230, 232, 300, 301, 302, 303, 304]),
                'unit': units_config.get('viscosity', 'cSt')
            },
            'Vapor Pressure': {
                'test_ids': test_ids_config.get('vapor_pressure', [58, 161, 299, 309, 242, 249, 254, 256, 266, 284, 292]),
                'unit': units_config.get('vapor_pressure', 'kPa')
            }
        }

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

            # Create Oracle connection using oracledb
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

    def fetch_unique_fluid_names(self) -> List[str]:
        """
        Fetch unique fluid names from the linefill_pcs_xfr table.
        This queries for the last 20 years of data as specified.
        """
        try:
            # Calculate date range (last 20 years)
            end_date = datetime.now()
            start_date = end_date.replace(year=end_date.year - 20)

            sql_query = f"""
                SELECT /*+PARALLEL(8) */ 
                    UNIQUE regexp_substr(file_text, '(\\S*)(\\s)',1,2) fluid 
                FROM linefill_pcs_xfr 
                WHERE linefill_date BETWEEN to_date('{start_date.strftime('%Y%m%d')}','yyyymmdd') 
                    AND to_date('{end_date.strftime('%Y%m%d')}','yyyymmdd') 
                ORDER BY fluid
            """

            df = self._execute_query(sql_query)

            # Filter out NaN/null values and convert to list
            fluids = []
            for fluid in df['FLUID'].tolist():
                if pd.notna(fluid) and fluid.strip():
                    fluids.append(str(fluid).strip())

            return sorted(fluids)

        except Exception as e:
            raise QueryExecutionError(f"Failed to fetch fluid names: {str(e)}")

    def fetch_properties_data(self, start_date: datetime, end_date: datetime, 
                            fluid_name: str, property_type: str) -> pd.DataFrame:
        """
        Fetch properties data based on selected criteria.
        
        Args:
            start_date: Start date for the query
            end_date: End date for the query
            fluid_name: Selected fluid name
            property_type: Selected property type (Density, Viscosity, Vapor Pressure)
        
        Returns:
            DataFrame with properties data
        """
        try:
            # Get property mapping
            if property_type not in self.property_mappings:
                raise ValueError(f"Invalid property type: {property_type}")

            property_config = self.property_mappings[property_type]
            test_ids_str = ','.join(str(id) for id in property_config['test_ids'])
            unit = property_config['unit']

            # Build fluid name filter
            fluid_name_filter = ""
            if fluid_name and fluid_name.strip():
                fluid_name_filter = f"AND cmdt.commodity_id LIKE '%{fluid_name.strip()}%'"

            # Build unit filter - for vapor pressure, include both kPa and kPa abs.
            if property_type == 'Vapor Pressure':
                unit_filter = "AND cstr.unit_of_measure_code IN ('kPa', 'kPa abs.')"
            else:
                unit_filter = f"AND cstr.unit_of_measure_code = '{unit}'"

            sql_query = f"""
                SELECT /*+PARALLEL(auto) */ 
                    cst.sample_date,
                    cmdt.commodity_id,
                    ctta.attribute_name,
                    cstr.test_result_nbr,
                    cstr.unit_of_measure_code 
                FROM 
                    cmdty_sample_test cst,
                    cmdty_sample_test_result cstr,
                    cmt_commodity cmdt,
                    cmt.test_type_attribute ctta 
                WHERE 
                    cst.cmdt_intl_id = cmdt.cmdt_intl_id AND 
                    cst.cmdtst_intl_id = cstr.cmdtst_intl_id AND 
                    cstr.testta_intl_id = ctta.testta_intl_id AND 
                    cstr.testta_intl_id IN ({test_ids_str}) AND 
                    cstr.test_result_nbr IS NOT NULL AND 
                    {unit_filter.replace('AND ', '')} AND 
                    cst.sample_date BETWEEN TO_DATE('{start_date.strftime('%Y%m%d')}','yyyymmdd') 
                        AND TO_DATE('{end_date.strftime('%Y%m%d')}','yyyymmdd') 
                    {fluid_name_filter}
                ORDER BY 
                    cmdt.commodity_id, cst.sample_date, ctta.attribute_name
            """

            return self._execute_query(sql_query)

        except Exception as e:
            raise QueryExecutionError(f"Failed to fetch properties data: {str(e)}")

    def fetch_commodities_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch commodities data for the specified date range.
        
        Args:
            start_date: Start date for the query
            end_date: End date for the query
        
        Returns:
            DataFrame with commodities data
        """
        try:
            sql_query = f"""
                SELECT /*+PARALLEL(auto) */ 
                    UNIQUE regexp_substr(file_text, '(\\S*)(\\s)',1,2) fluid,
                    line_no                                                    
                FROM linefill_pcs_xfr
                WHERE linefill_date BETWEEN TO_DATE('{start_date.strftime('%Y%m%d')}','yyyymmdd') 
                    AND TO_DATE('{end_date.strftime('%Y%m%d')}','yyyymmdd')
                ORDER BY line_no, fluid
            """

            return self._execute_query(sql_query)

        except Exception as e:
            raise QueryExecutionError(f"Failed to fetch commodities data: {str(e)}")

    def save_to_csv(self, data: pd.DataFrame, file_path: str, mode: str) -> bool:
        """
        Save DataFrame to CSV file.
        
        Args:
            data: DataFrame to save
            file_path: Full path where to save the file
            mode: Either 'Properties' or 'Commodities' for filename prefix
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if data.empty:
                raise ValueError("No data to export")

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"FluidProperties_{mode}_{timestamp}.csv"
            full_path = os.path.join(file_path, filename)

            # Save to CSV
            data.to_csv(full_path, index=False)
            return True

        except Exception as e:
            raise QueryExecutionError(f"Failed to save CSV file: {str(e)}")


# Global service instance
_fluid_properties_service = None


def get_fluid_properties_service() -> FluidPropertiesService:
    """Get the global fluid properties service instance."""
    global _fluid_properties_service
    if _fluid_properties_service is None:
        _fluid_properties_service = FluidPropertiesService()
    return _fluid_properties_service
