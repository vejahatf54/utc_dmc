"""
Simple OneSource Service for database operations.

This restores the complex logic from the working repository including:
- Loop detection using HydroMilePost values
- Corrected milepost calculation
- Station detection via pump station U-shape patterns
- Proper data processing and column mapping
"""

import pandas as pd
import numpy as np
from typing import Optional
from sqlalchemy import create_engine, text
from services.config_manager import get_config_manager
from services.exceptions import DatabaseError, DataNotFoundError
from logging_config import get_logger

logger = get_logger(__name__)


class OneSourceService:
    """Simple service for querying OneSource database with proper data processing."""

    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self._engine = None
        self.logger = get_logger(f"{__name__}.OneSourceService")
        
        # Constants from original repository
        self.STATION_LOOKBACK = 5
        self.RWMP_TOL = 1e-6

    @property
    def engine(self):
        """Lazy initialization of database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self):
        """Create SQLAlchemy engine based on configuration."""
        try:
            db_type = self.config_manager.get_database_type()
            if db_type == "sqlite":
                sqlite_path = self.config_manager.get_sqlite_path()
                connection_string = f"sqlite:///{sqlite_path}"
            else:
                sql_config = self.config_manager.get_sql_server_config()
                connection_string = (
                    f"mssql+pyodbc://{sql_config['server']}/"
                    f"{sql_config['database']}?driver={sql_config['driver']}&"
                    f"Trusted_Connection=yes"
                )

            engine = create_engine(
                connection_string,
                echo=self.config_manager.get('database.sql_echo', False),
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_timeout=30,
                connect_args={"timeout": 30} if db_type == "sqlite" else {}
            )

            self.logger.info(f"Database engine created successfully - Type: {db_type}")
            return engine

        except Exception as e:
            error_msg = f"Failed to create database engine: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg, str(e))

    def execute_query(self, query: str, params: dict = None) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame."""
        try:
            with self.engine.connect() as connection:
                result = pd.read_sql(query, connection, params=params)
                self.logger.debug(f"Query executed successfully, returned {len(result)} rows")
                return result
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            raise DatabaseError(f"Query execution failed: {str(e)}")

    def get_pipeline_lines(self) -> pd.DataFrame:
        """Get all available pipeline lines."""
        self.logger.info("Fetching pipeline lines from database")
        
        if self.config_manager.get_database_type() == "sqlite":
            query = """
                SELECT DISTINCT PLIntegrityLineSegmentNumber
                FROM PipeAssetInformation_V
                ORDER BY PLIntegrityLineSegmentNumber
            """
        else:  # SQL Server
            query = """
                SELECT DISTINCT PLIntegrityLineSegmentNumber
                FROM BI.PipeAssetInformation_V
                ORDER BY PLIntegrityLineSegmentNumber
            """
        
        return self.execute_query(query)

    def _detect_loop_ranges_by_rwmp(self, df: pd.DataFrame, tol: float = None) -> pd.Series:
        """Array-based loop detection algorithm using HydroMilePost values."""
        if tol is None:
            tol = self.RWMP_TOL

        if "HydroMilePost" not in df.columns:
            return pd.Series(False, index=df.index)

        rwmp = df["HydroMilePost"].to_numpy(dtype=float)
        n = rwmp.size
        loop_flags = np.zeros(n, dtype=bool)

        current_max = -np.inf
        i = 0
        isnan = np.isnan

        while i < n:
            val = rwmp[i]
            if isnan(val):
                i += 1
                continue

            if val >= current_max - tol:
                if val > current_max:
                    current_max = val
                i += 1
                continue

            # Found a decrease -> inside a loop until value > threshold appears
            threshold = current_max
            while i < n:
                v2 = rwmp[i]
                if isnan(v2):
                    loop_flags[i] = True
                    i += 1
                    continue
                if v2 > threshold + tol:
                    current_max = v2
                    break
                else:
                    loop_flags[i] = True
                    i += 1

        return pd.Series(loop_flags, index=df.index)

    def _compute_corrected_milepost_with_loops(self, df: pd.DataFrame, loop_flags: pd.Series) -> pd.Series:
        """Calculate corrected milepost values handling loops properly."""
        n = len(df)
        corrected = np.zeros(n, dtype=float)
        if n == 0:
            return pd.Series(corrected, index=df.index)

        # Extract arrays for performance
        jdm = df["JointDistanceMeters"].to_numpy(
            dtype=float) if "JointDistanceMeters" in df.columns else np.full(n, np.nan)
        loop = loop_flags.to_numpy(dtype=bool)
        start_trap = df["StartTrap"].to_numpy(
            dtype=object) if "StartTrap" in df.columns else np.full(n, None, dtype=object)
        end_trap = df["EndTrap"].to_numpy(
            dtype=object) if "EndTrap" in df.columns else np.full(n, None, dtype=object)

        cum = 0.0
        prev_jdm = np.nan
        prev_start = None
        prev_end = None
        first_nonloop_seen = False
        in_loop = False

        for i in range(n):
            is_loop = bool(loop[i])
            jt = jdm[i]
            trap_pair = (start_trap[i], end_trap[i])

            if not first_nonloop_seen:
                if is_loop:
                    corrected[i] = 0.0
                    in_loop = True
                else:
                    corrected[i] = 0.0
                    cum = 0.0
                    prev_jdm = jt if not np.isnan(jt) else 0.0
                    prev_start, prev_end = trap_pair
                    first_nonloop_seen = True
                    in_loop = False
                continue

            if is_loop:
                corrected[i] = cum
                in_loop = True
                continue

            if in_loop:
                # First non-loop after loop: no step, re-baseline
                corrected[i] = cum
                if not np.isnan(jt):
                    prev_jdm = jt
                prev_start, prev_end = trap_pair
                in_loop = False
                continue

            # Consecutive non-loop rows
            if (prev_start is not None) and ((trap_pair[0] != prev_start) or (trap_pair[1] != prev_end)):
                step = abs(0.0 - jt) if not np.isnan(jt) else 0.0
            else:
                if (not np.isnan(prev_jdm)) and (not np.isnan(jt)):
                    step = abs(jt - prev_jdm)
                else:
                    step = 0.0

            cum += step
            corrected[i] = cum

            if not np.isnan(jt):
                prev_jdm = jt
            prev_start, prev_end = trap_pair

        # Ensure first row = 0.0
        if n > 0:
            corrected[0] = 0.0

        return pd.Series(corrected, index=df.index)

    def get_elevation_profile(self, line_id: str) -> pd.DataFrame:
        """
        Get complete pipeline elevation profile with features and stations.
        This matches the exact logic from the working repository.
        """
        if not line_id:
            raise ValueError("Line ID is required")

        self.logger.info(f"Fetching elevation profile for line {line_id}")

        # Get database-specific queries
        if self.config_manager.get_database_type() == "sqlite":
            elevation_query = text("""
                SELECT DISTINCT
                    GirthWeldAddress,
                    PLIntegrityLineSegmentNumber,
                    JointDistanceMeters,
                    ILIElevationMeters,
                    ILILatitude,
                    ILILongitude,
                    NominalWallThicknessMillimeters,
                    NominalPipeSizeInches,
                    StartTrap,
                    EndTrap,
                    PipeCoatingType,
                    UpstreamPumpStationID,
                    DownstreamPumpStationID,
                    DistanceToDownstreamPumpStationKilometers,
                    HydroMilePost
                FROM PipeAssetInformation_V
                WHERE PLIntegrityLineSegmentNumber = :line
                ORDER BY GirthWeldAddress
            """)

            valves_query = text("""
                SELECT
                    GirthWeldAddress,
                    GROUP_CONCAT(
                        FeatureType || '-' || IFNULL(FeatureComment,'') || '-' || IFNULL(FeatureSubType,''),
                        ' '
                    ) AS Features
                FROM ILIReportFeatureDetailListing_V
                WHERE PLIntegrityLineSegmentNumber = :line
                  AND (
                    FeatureType LIKE '%VALVE%'
                    OR (FeatureType || IFNULL(FeatureComment,'') || IFNULL(FeatureSubType,'')) LIKE '%VALVE%'
                  )
                GROUP BY GirthWeldAddress
                ORDER BY GirthWeldAddress
            """)

        else:  # sqlserver
            elevation_query = text("""
                SELECT DISTINCT
                    GirthWeldAddress,
                    PLIntegrityLineSegmentNumber,
                    JointDistanceMeters,
                    ILIElevationMeters,
                    ILILatitude,
                    ILILongitude,
                    NominalWallThicknessMillimeters,
                    NominalPipeSizeInches,
                    StartTrap,
                    EndTrap,
                    PipeCoatingType,
                    UpstreamPumpStationID,
                    DownstreamPumpStationID,
                    DistanceToDownstreamPumpStationKilometers,
                    RightOfWayMilePost AS HydroMilePost
                FROM BI.PipeAssetInformation_V
                WHERE PLIntegrityLineSegmentNumber = :line
                ORDER BY GirthWeldAddress
            """)

            valves_query = text("""
                SELECT
                    GirthWeldAddress,
                    STUFF((
                        SELECT DISTINCT ' ' + v.FeatureType + '-' + COALESCE(v.FeatureComment,'') + '-' + COALESCE(v.FeatureSubType,'')
                        FROM BI.ILIReportFeatureDetailListing_V v
                        WHERE v.GirthWeldAddress = f.GirthWeldAddress
                          AND v.PLIntegrityLineSegmentNumber = :line
                          AND (
                                v.FeatureType LIKE '%VALVE%'
                                OR (v.FeatureType + COALESCE(v.FeatureComment,'') + COALESCE(v.FeatureSubType,'')) LIKE '%VALVE%'
                              )
                        FOR XML PATH(''), TYPE
                    ).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS Features
                FROM (
                    SELECT DISTINCT GirthWeldAddress
                    FROM BI.PipeAssetInformation_V
                    WHERE PLIntegrityLineSegmentNumber = :line
                ) f
                WHERE EXISTS (
                    SELECT 1 FROM BI.ILIReportFeatureDetailListing_V v2
                    WHERE v2.GirthWeldAddress = f.GirthWeldAddress
                      AND v2.PLIntegrityLineSegmentNumber = :line
                      AND (
                            v2.FeatureType LIKE '%VALVE%'
                            OR (v2.FeatureType + COALESCE(v2.FeatureComment,'') + COALESCE(v2.FeatureSubType,'')) LIKE '%VALVE%'
                          )
                )
                ORDER BY GirthWeldAddress
            """)

        # Read elevation data
        df = self.execute_query(str(elevation_query), {"line": line_id})
        if df.empty:
            raise DataNotFoundError(f"No elevation data found for line {line_id}")

        # Convert numeric columns
        numeric_cols = [
            "JointDistanceMeters",
            "ILIElevationMeters",
            "ILILatitude",
            "ILILongitude",
            "NominalWallThicknessMillimeters",
            "NominalPipeSizeInches",
            "DistanceToDownstreamPumpStationKilometers",
            "HydroMilePost",
        ]
        existing_numeric_cols = [col for col in numeric_cols if col in df.columns]
        df[existing_numeric_cols] = df[existing_numeric_cols].apply(pd.to_numeric, errors="coerce")

        # Stabilize columns using forward and backward fill
        stabilize_cols = [
            "ILIElevationMeters",
            "NominalWallThicknessMillimeters",
            "NominalPipeSizeInches",
            "UpstreamPumpStationID",
            "DownstreamPumpStationID",
            "PipeCoatingType",
            "ILILatitude",
            "ILILongitude"
        ]
        existing_stabilize_cols = [col for col in stabilize_cols if col in df.columns]
        df[existing_stabilize_cols] = df[existing_stabilize_cols].ffill().bfill()

        # Detect loops and compute corrected milepost
        df["LoopFlag"] = self._detect_loop_ranges_by_rwmp(df)
        df["CorrectedMilepost"] = self._compute_corrected_milepost_with_loops(df, df["LoopFlag"])

        # Station detection
        df["Station"] = pd.Series([None] * len(df), dtype=object)

        # First row: populate from StartTrap if available
        if len(df) > 0 and "StartTrap" in df.columns:
            start_trap = df.iloc[0]["StartTrap"]
            if pd.notna(start_trap) and str(start_trap).strip():
                df.at[df.index[0], "Station"] = start_trap

        # Last row: populate from EndTrap if available
        if len(df) > 0 and "EndTrap" in df.columns:
            end_trap = df.iloc[-1]["EndTrap"]
            if pd.notna(end_trap) and str(end_trap).strip():
                df.at[df.index[-1], "Station"] = end_trap

        # Middle stations: detect using U-shape pattern in pump station distances
        if "DistanceToDownstreamPumpStationKilometers" in df.columns:
            nonloop_idx = np.flatnonzero(~df["LoopFlag"].to_numpy(dtype=bool))
            if nonloop_idx.size >= 3:
                d_arr = df["DistanceToDownstreamPumpStationKilometers"].to_numpy(dtype=float)
                down_ids = df["DownstreamPumpStationID"]

                def resolve_station_name(k_mid: int) -> Optional[object]:
                    idx_mid = nonloop_idx[k_mid]
                    name = down_ids.iat[idx_mid]
                    if pd.isna(name):
                        lookback_k = max(0, k_mid - self.STATION_LOOKBACK)
                        name = down_ids.iat[nonloop_idx[lookback_k]]
                    return name

                for k in range(1, nonloop_idx.size - 1):
                    i0, i1, i2 = nonloop_idx[k - 1], nonloop_idx[k], nonloop_idx[k + 1]
                    d0, d1, d2 = d_arr[i0], d_arr[i1], d_arr[i2]
                    if np.isfinite(d0) and np.isfinite(d1) and np.isfinite(d2):
                        if (d0 >= d1) and (d1 <= d2):  # U-shape
                            station_name = resolve_station_name(k)
                            df.at[i1, "Station"] = station_name

        # Merge valve features
        try:
            df_valves = self.execute_query(str(valves_query), {"line": line_id})
            if not df_valves.empty:
                df = pd.merge(df, df_valves, on="GirthWeldAddress", how="left")
            else:
                df["Features"] = None
        except Exception as e:
            self.logger.warning(f"Could not fetch valve features for line {line_id}: {str(e)}")
            df["Features"] = None

        # Final column selection and cleanup
        final_cols = [
            "GirthWeldAddress",
            "HydroMilePost",
            "CorrectedMilepost",
            "ILIElevationMeters",
            "ILILatitude",
            "ILILongitude",
            "NominalWallThicknessMillimeters",
            "NominalPipeSizeInches",
            "Station",
            "PipeCoatingType",
            "Features"
        ]
        existing_cols = [col for col in final_cols if col in df.columns]
        out = df[existing_cols].copy()

        # Fix data types
        for col in ["Features", "Station", "PipeCoatingType"]:
            if col in out.columns:
                out[col] = out[col].astype(object)

        # Preserve station rows when deduplicating
        if "CorrectedMilepost" in out.columns:
            station_present = out["Station"].notna() & out["Station"].astype(str).str.strip().ne("")
            feature_present = out["Features"].notna() & out["Features"].astype(str).str.strip().ne("")

            # Identify start/end trap stations for highest priority
            start_end_station = pd.Series([False] * len(out), dtype=bool)
            if len(out) > 0:
                # Check if first row has station from StartTrap
                if ("StartTrap" in df.columns and
                    out.iloc[0]["Station"] is not None and
                    df.iloc[0]["StartTrap"] is not None and
                        str(out.iloc[0]["Station"]) == str(df.iloc[0]["StartTrap"])):
                    start_end_station.iloc[0] = True

                # Check if last row has station from EndTrap
                if (len(out) > 1 and "EndTrap" in df.columns and
                    out.iloc[-1]["Station"] is not None and
                    df.iloc[-1]["EndTrap"] is not None and
                        str(out.iloc[-1]["Station"]) == str(df.iloc[-1]["EndTrap"])):
                    start_end_station.iloc[-1] = True

            # Priority system: Start/End trap stations = 4, regular stations = 2, features = 1
            out["_prio"] = (start_end_station.astype(int) * 4 +
                            station_present.astype(int) * 2 +
                            feature_present.astype(int))

            out = (out
                   .sort_values(["CorrectedMilepost", "_prio"], ascending=[True, True])
                   .drop_duplicates(subset=["CorrectedMilepost"], keep="last")
                   .drop(columns=["_prio"])
                   .reset_index(drop=True))

        self.logger.info(f"Retrieved {len(out)} elevation points for line {line_id}")
        return out


# Global singleton
_onesource_service = None


def get_onesource_service() -> OneSourceService:
    """Get singleton instance of OneSource service."""
    global _onesource_service
    if _onesource_service is None:
        _onesource_service = OneSourceService()
    return _onesource_service
