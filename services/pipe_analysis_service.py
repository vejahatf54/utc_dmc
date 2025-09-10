"""
Pipe Analysis Service

Handles pipe segment analysis, wall thickness calculations, and data formatting
for pipeline elevation profile processing. Moved from elevation.py UI layer
for better separation of concerns and testability.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass
from logging_config import get_logger

from services.exceptions import ServiceError, DataProcessingError


@dataclass
class PipeSegment:
    """Represents a pipe segment with its properties."""
    pipe_name: str
    length: float
    od: float
    wt: float
    start_distance: float
    end_distance: float


@dataclass
class RDPResult:
    """Result of Ramer-Douglas-Peucker algorithm."""
    reduced_df: pd.DataFrame
    flags: np.ndarray
    original_count: int
    reduced_count: int
    compression_ratio: float


class PipeAnalysisService:
    """
    Service for analyzing pipe segments, calculating wall thickness,
    and formatting pipe data for export.
    """

    def __init__(self):
        """Initialize the pipe analysis service."""
        self.logger = get_logger(f"{__name__}.PipeAnalysisService")

    def nps_to_actual_od(self, nps: float) -> float:
        """
        Convert Nominal Pipe Size (NPS) to actual Outside Diameter (OD) in inches.
        
        Based on ASME B36.10M standard for steel pipes.
        
        Args:
            nps: Nominal Pipe Size in inches
            
        Returns:
            Actual Outside Diameter in inches
            
        Raises:
            DataProcessingError: If NPS value is invalid
        """
        try:
            if not isinstance(nps, (int, float)):
                raise DataProcessingError(f"NPS must be numeric, got {type(nps)}")
                
            if nps <= 0:
                raise DataProcessingError(f"NPS must be positive, got {nps}")
                
            if nps > 100:  # Reasonable upper limit
                self.logger.warning(f"Very large NPS value: {nps} inches")
                
            self.logger.debug(f"Converting NPS {nps} to actual OD")
            
            # Standard NPS to OD conversion table
            # For NPS <= 12", OD = NPS + some offset
            # For NPS >= 14", OD = NPS (they are the same)
            nps_to_od_map = {
                0.5: 0.840,
                0.75: 1.050,
                1.0: 1.315,
                1.25: 1.660,
                1.5: 1.900,
                2.0: 2.375,
                2.5: 2.875,
                3.0: 3.500,
                3.5: 4.000,
                4.0: 4.500,
                5.0: 5.563,
                6.0: 6.625,
                8.0: 8.625,
                10.0: 10.750,
                12.0: 12.750,
                # For NPS >= 14", OD = NPS
                14.0: 14.000,
                16.0: 16.000,
                18.0: 18.000,
                20.0: 20.000,
                22.0: 22.000,
                24.0: 24.000,
                26.0: 26.000,
                28.0: 28.000,
                30.0: 30.000,
                32.0: 32.000,
                34.0: 34.000,
                36.0: 36.000,
                38.0: 38.000,
                40.0: 40.000,
                42.0: 42.000,
                44.0: 44.000,
                46.0: 46.000,
                48.0: 48.000,
                50.0: 50.000,
                52.0: 52.000,
                54.0: 54.000,
                56.0: 56.000,
                58.0: 58.000,
                60.0: 60.000,
                62.0: 62.000,
                64.0: 64.000,
                66.0: 66.000,
                68.0: 68.000,
                70.0: 70.000,
                72.0: 72.000,
            }
            
            # Handle exact matches first
            if nps in nps_to_od_map:
                od = nps_to_od_map[nps]
                self.logger.debug(f"Exact match: NPS {nps} -> OD {od}")
                return od
            
            # For NPS >= 14", OD equals NPS
            if nps >= 14.0:
                self.logger.debug(f"Large pipe: NPS {nps} -> OD {nps}")
                return nps
                
            # For intermediate values <= 12", interpolate or find closest match
            if nps <= 12.0:
                sorted_nps = sorted([k for k in nps_to_od_map.keys() if k <= 12.0])
                
                # Find the closest NPS values for interpolation
                lower_nps = None
                upper_nps = None
                
                for std_nps in sorted_nps:
                    if std_nps <= nps:
                        lower_nps = std_nps
                    elif std_nps > nps and upper_nps is None:
                        upper_nps = std_nps
                        break
                
                # Interpolate or use closest match
                if lower_nps is not None and upper_nps is not None:
                    # Linear interpolation
                    lower_od = nps_to_od_map[lower_nps]
                    upper_od = nps_to_od_map[upper_nps]
                    ratio = (nps - lower_nps) / (upper_nps - lower_nps)
                    od = lower_od + ratio * (upper_od - lower_od)
                    self.logger.debug(f"Interpolated: NPS {nps} -> OD {od:.3f}")
                    return od
                elif lower_nps is not None:
                    od = nps_to_od_map[lower_nps]
                    self.logger.debug(f"Using lower bound: NPS {nps} -> OD {od}")
                    return od
                elif upper_nps is not None:
                    od = nps_to_od_map[upper_nps]
                    self.logger.debug(f"Using upper bound: NPS {nps} -> OD {od}")
                    return od
            
            # Fallback for very large pipes not in the table
            self.logger.warning(f"Using fallback OD=NPS for unusual pipe size: {nps}")
            return nps
            
        except (TypeError, ValueError) as e:
            raise DataProcessingError(f"Invalid NPS value: {e}") from e
        except Exception as e:
            raise DataProcessingError(f"Invalid NPS value: {e}") from e

    def get_pipes_csv_headers(self, dist_unit: str = 'mi') -> List[str]:
        """
        Get the correct column headers for pipes.csv based on distance unit.
        
        Args:
            dist_unit: Distance unit ('km', 'mi', 'm')
            
        Returns:
            List of column headers
        """
        if dist_unit == 'km':
            length_unit = 'km'
            wt_unit = 'mm'
        elif dist_unit == 'mi':
            length_unit = 'mi'
            wt_unit = 'in'
        else:  # 'm'
            length_unit = 'm'
            wt_unit = 'in'
        
        # OD is always in inches regardless of user selection
        od_unit = 'in'

        return [f'Pipe_Name', f'Length_{length_unit}', f'OD_{od_unit}', f'WT_{wt_unit}']

    def simplify_dataframe_rdp(
        self,
        df: pd.DataFrame,
        epsilon: float,
        extra_keep_mask: Optional[np.ndarray] = None,
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Simplify elevation data using Ramer-Douglas-Peucker algorithm.
        
        Args:
            df: DataFrame with 'Milepost' and 'Elevation' columns
            epsilon: RDP tolerance value
            extra_keep_mask: Optional mask of points to force keep
            
        Returns:
            Tuple of (reduced_df, flags)
        """
        try:
            if df.empty or 'Milepost' not in df.columns or 'Elevation' not in df.columns:
                raise DataProcessingError("DataFrame must have 'Milepost' and 'Elevation' columns")
                
            x = df['Milepost'].to_numpy(dtype=float)
            y = df['Elevation'].to_numpy(dtype=float)

            # Compute base RDP keep mask
            base_keep_mask = self._rdp_keep_mask(
                x, y, epsilon,
                must_keep_mask=(extra_keep_mask.astype(bool) if extra_keep_mask is not None else None)
            )
            
            keep_mask = base_keep_mask
            flags = keep_mask.astype(int)
            reduced_df = df.loc[keep_mask].copy().reset_index(drop=True)
            
            return reduced_df, flags
            
        except Exception as e:
            self.logger.error(f"Error in RDP simplification: {e}")
            if isinstance(e, DataProcessingError):
                raise
            raise DataProcessingError(f"RDP simplification failed: {e}")

    def _rdp_keep_mask(
        self,
        x: np.ndarray,
        y: np.ndarray,
        epsilon: float,
        must_keep_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Core Ramer-Douglas-Peucker algorithm implementation.
        
        Args:
            x: X coordinates (distance)
            y: Y coordinates (elevation)
            epsilon: Tolerance value
            must_keep_mask: Points that must be kept
            
        Returns:
            Boolean mask of points to keep
        """
        n = x.shape[0]
        if n <= 2:
            return np.ones(n, dtype=bool)
            
        keep = np.zeros(n, dtype=bool)
        keep[0] = True
        keep[-1] = True
        
        if must_keep_mask is not None:
            keep |= must_keep_mask.astype(bool)
            
        stack = [(0, n - 1)]
        while stack:
            start, end = stack.pop()
            if end <= start + 1:
                continue
                
            x1, y1 = x[start], y[start]
            x2, y2 = x[end], y[end]
            idxs = np.arange(start + 1, end)
            
            if idxs.size == 0:
                continue
                
            px = x[idxs]
            py = y[idxs]
            dx = (x2 - x1)
            
            if dx == 0:
                y_line = np.full_like(py, y1, dtype=float)
            else:
                t = (px - x1) / dx
                y_line = y1 + t * (y2 - y1)
                
            dists = np.abs(py - y_line)
            max_rel = np.argmax(dists)
            max_dist = float(dists[max_rel])
            max_idx = int(idxs[max_rel])
            
            if must_keep_mask is not None and must_keep_mask[max_idx]:
                keep[max_idx] = True
                stack.append((start, max_idx))
                stack.append((max_idx, end))
                continue
                
            if max_dist > epsilon:
                keep[max_idx] = True
                stack.append((start, max_idx))
                stack.append((max_idx, end))
                
        if must_keep_mask is not None:
            keep |= must_keep_mask.astype(bool)
            
        return keep

    def detect_pipe_size_changes(self, df: pd.DataFrame) -> List[Tuple[float, float, float, float, int]]:
        """
        Detect where pipe sizes change and return positions for dividers.
        
        Args:
            df: DataFrame with pipe size and distance data
            
        Returns:
            List of tuples: (x_pos, y_pos, prev_size, curr_size, index)
        """
        try:
            if df.empty or 'NominalPipeSizeInches' not in df.columns:
                return []

            pipe_sizes = pd.to_numeric(df['NominalPipeSizeInches'], errors='coerce')
            pipe_sizes = pipe_sizes.ffill().bfill()

            divider_positions = []
            for i in range(1, len(pipe_sizes)):
                if not pd.isna(pipe_sizes.iloc[i]) and not pd.isna(pipe_sizes.iloc[i-1]):
                    if pipe_sizes.iloc[i] != pipe_sizes.iloc[i-1]:
                        # Check if segments on both sides are more than 1 km
                        prev_segment_length = self._calculate_segment_length(df, pipe_sizes, i, 'prev')
                        curr_segment_length = self._calculate_segment_length(df, pipe_sizes, i, 'curr')

                        # Only include divider if both segments are > 1000 meters (1 km)
                        if prev_segment_length > 1000 and curr_segment_length > 1000:
                            x_pos = df['Milepost'].iloc[i]
                            y_pos = df['Elevation'].iloc[i]
                            prev_size = pipe_sizes.iloc[i-1]
                            curr_size = pipe_sizes.iloc[i]
                            divider_positions.append((x_pos, y_pos, prev_size, curr_size, i))

            return divider_positions
            
        except Exception as e:
            self.logger.error(f"Error detecting pipe size changes: {e}")
            return []

    def _calculate_segment_length(
        self,
        df: pd.DataFrame,
        pipe_sizes: pd.Series,
        index: int,
        direction: str
    ) -> float:
        """Calculate segment length in specified direction from pipe size change."""
        try:
            if direction == 'prev':
                for j in range(index-1, -1, -1):
                    if j == 0 or (not pd.isna(pipe_sizes.iloc[j-1]) and 
                                  pipe_sizes.iloc[j-1] != pipe_sizes.iloc[index-1]):
                        return df['DistanceMeters'].iloc[index-1] - df['DistanceMeters'].iloc[j]
            else:  # 'curr'
                for j in range(index, len(pipe_sizes)):
                    if j == len(pipe_sizes)-1 or (not pd.isna(pipe_sizes.iloc[j+1]) and 
                                                  pipe_sizes.iloc[j+1] != pipe_sizes.iloc[index]):
                        return df['DistanceMeters'].iloc[j] - df['DistanceMeters'].iloc[index]
            return 0
        except Exception:
            return 0

    def create_pipes_dataframe(
        self,
        df_current: pd.DataFrame,
        reduced_df: Optional[pd.DataFrame] = None,
        segments: Optional[List[Tuple]] = None,
        dist_unit: str = 'mi'
    ) -> pd.DataFrame:
        """
        Create a pipes.csv DataFrame with pipe segments, lengths, OD, and wall thickness.
        
        Args:
            df_current: Full elevation profile data
            reduced_df: Reduced/simplified elevation data (optional)
            segments: List of (start_idx, end_idx, seg_df) tuples (optional)
            dist_unit: Distance unit for naming ('km', 'mi', 'm')
            
        Returns:
            DataFrame with pipe segment data
        """
        try:
            # Determine units for headers and conversions
            if dist_unit == 'km':
                length_unit = 'km'
                wt_unit = 'mm'
            elif dist_unit == 'mi':
                length_unit = 'mi'
                wt_unit = 'in'
            else:  # 'm'
                length_unit = 'm'
                wt_unit = 'in'

            # OD is always in inches regardless of user selection
            od_unit = 'in'

            # If segments are provided, use them directly
            if segments and reduced_df is not None:
                return self._create_pipes_from_segments(
                    df_current, segments, dist_unit, length_unit, od_unit, wt_unit
                )
            else:
                return self._create_pipes_fallback(
                    df_current, dist_unit, length_unit, od_unit, wt_unit
                )
                
        except Exception as e:
            self.logger.error(f"Error creating pipes dataframe: {e}")
            headers = self.get_pipes_csv_headers(dist_unit)
            return pd.DataFrame(columns=headers)

    def _format_distance_for_name(self, dist_val: float, unit: str) -> str:
        """Format distance value for pipe naming."""
        try:
            s = f"{dist_val:.3f}"
        except Exception:
            s = str(dist_val)
        return s.replace('.', '')

    def _create_pipes_from_segments(
        self,
        df_current: pd.DataFrame,
        segments: List[Tuple],
        dist_unit: str,
        length_unit: str,
        od_unit: str,
        wt_unit: str
    ) -> pd.DataFrame:
        """Create pipes dataframe from provided segments."""
        pipes_data = []

        for start_idx_seg, end_idx, seg_df in segments:
            # Use TL_ naming convention (Transfer Line)
            distance_val = float(seg_df['Milepost'].iloc[0])
            pipe_name = f"TL_{self._format_distance_for_name(distance_val, dist_unit)}"

            # Calculate pipe segment length in user units
            segment_length_user_units = seg_df['Milepost'].iloc[-1] - seg_df['Milepost'].iloc[0]

            # Get original data rows for this segment
            matching_rows = self._get_matching_rows(df_current, seg_df, start_idx_seg, end_idx)
            
            if matching_rows.empty:
                continue

            # Extract OD and calculate WT
            od_inches = self._extract_od_from_rows(matching_rows)
            wt_avg = self.calculate_volume_conserving_wt(
                matching_rows, segment_length_user_units, od_inches, dist_unit
            )

            # OD is always in inches and formatted with zero decimal places
            od_final = od_inches
            wt_final = wt_avg  # Already in correct units from calculate_volume_conserving_wt

            pipes_data.append({
                f'Pipe_Name': pipe_name,
                f'Length_{length_unit}': round(segment_length_user_units, 3),
                f'OD_{od_unit}': round(od_final, 3),  # Three decimal places for OD
                f'WT_{wt_unit}': round(wt_final, 4)
            })

        return pd.DataFrame(pipes_data)

    def _create_pipes_fallback(
        self,
        df_current: pd.DataFrame,
        dist_unit: str,
        length_unit: str,
        od_unit: str,
        wt_unit: str
    ) -> pd.DataFrame:
        """Create pipes dataframe using fallback approach."""
        if df_current.empty:
            headers = self.get_pipes_csv_headers(dist_unit)
            return pd.DataFrame(columns=headers)

        # Simple single pipe case
        pipe_name = "TL_0000"

        # Get total length
        total_length = self._calculate_total_length(df_current, dist_unit)
        
        # Get average OD and WT
        od_inches = self._extract_od_from_rows(df_current)
        wt_mm = self._extract_wt_from_rows(df_current)

        # OD is always in inches and formatted with zero decimal places
        od_final = od_inches
        wt_final = wt_mm if wt_unit == 'mm' else wt_mm / 25.4

        result_data = [{
            f'Pipe_Name': pipe_name,
            f'Length_{length_unit}': round(total_length, 3),
            f'OD_{od_unit}': round(od_final, 3),  # Three decimal places for OD
            f'WT_{wt_unit}': round(wt_final, 4)
        }]

        return pd.DataFrame(result_data)

    def _get_matching_rows(
        self,
        df_current: pd.DataFrame,
        seg_df: pd.DataFrame,
        start_idx_seg: int,
        end_idx: int
    ) -> pd.DataFrame:
        """Get matching rows from original data for segment."""
        matching_rows = pd.DataFrame()
        
        try:
            # Try distance-based matching first
            if 'DistanceMeters' in seg_df.columns and 'DistanceMeters' in df_current.columns:
                start_dm = pd.to_numeric(seg_df['DistanceMeters'].iloc[0], errors='coerce')
                end_dm = pd.to_numeric(seg_df['DistanceMeters'].iloc[-1], errors='coerce')
                
                if pd.notna(start_dm) and pd.notna(end_dm):
                    d0, d1 = (float(start_dm), float(end_dm))
                    if d1 < d0:
                        d0, d1 = d1, d0
                    matching_rows = df_current[
                        (pd.to_numeric(df_current['DistanceMeters'], errors='coerce') >= d0) &
                        (pd.to_numeric(df_current['DistanceMeters'], errors='coerce') <= d1)
                    ].copy()
        except Exception:
            pass

        # Fallback approaches
        if matching_rows.empty:
            if 'OrigRowID' in seg_df.columns and len(seg_df) > 0:
                orig_ids = seg_df['OrigRowID'].astype(int).tolist()
                if orig_ids:
                    try:
                        matching_rows = df_current.iloc[orig_ids]
                    except Exception:
                        matching_rows = df_current.iloc[:len(seg_df)]
                else:
                    matching_rows = df_current.iloc[:len(seg_df)]
            else:
                # Final fallback: assume sequential rows
                matching_rows = df_current.iloc[start_idx_seg:end_idx+1]

        return matching_rows

    def _extract_od_from_rows(self, rows: pd.DataFrame) -> float:
        """Extract actual outer diameter from rows, converting from NPS if needed."""
        nps_inches = 24.0  # Default NPS value
        
        possible_od_columns = ['NominalPipeSizeInches']
        for col in possible_od_columns:
            if col in rows.columns:
                od_data = pd.to_numeric(rows[col], errors='coerce').dropna()
                if not od_data.empty:
                    nps_inches = od_data.mean()
                    break
        
        # Convert NPS to actual OD
        actual_od = self.nps_to_actual_od(nps_inches)
        return actual_od

    def _extract_wt_from_rows(self, rows: pd.DataFrame) -> float:
        """Extract wall thickness from rows."""
        wt_mm = 12.7  # Default value
        
        if 'NominalWallThicknessMillimeters' in rows.columns:
            wt_data = pd.to_numeric(rows['NominalWallThicknessMillimeters'], errors='coerce').dropna()
            if not wt_data.empty:
                wt_mm = wt_data.median()
                
        return wt_mm

    def _calculate_total_length(self, df_current: pd.DataFrame, dist_unit: str) -> float:
        """Calculate total length of pipeline."""
        if 'DistanceMeters' in df_current.columns:
            total_length_m = df_current['DistanceMeters'].iloc[-1] - df_current['DistanceMeters'].iloc[0]
            if dist_unit == 'km':
                return total_length_m / 1000
            elif dist_unit == 'mi':
                return total_length_m / 1609.34
            else:
                return total_length_m
        else:
            return 1000  # Default 1000 units

    def calculate_volume_conserving_wt(
        self,
        matching_rows: pd.DataFrame,
        segment_length_user_units: float,
        od_inches: float,
        dist_unit: str
    ) -> float:
        """
        Calculate volume-conserving wall thickness for the segment.
        
        Args:
            matching_rows: DataFrame with original pipeline data
            segment_length_user_units: Total segment length in user units
            od_inches: Average outer diameter in inches
            dist_unit: Distance unit ('km', 'mi', 'm')
            
        Returns:
            Volume-conserving wall thickness in appropriate units
        """
        try:
            df = matching_rows.copy()

            # Get wall thickness data
            if 'NominalWallThicknessMillimeters' in df.columns:
                wt_mm = pd.to_numeric(df['NominalWallThicknessMillimeters'], errors='coerce')
            else:
                # Fallback: estimate from OD (assume ~6% of diameter for steel pipe)
                wt_mm = pd.Series([od_inches * 25.4 * 0.06] * len(df))

            # Get distance data
            distances_m = self._get_distance_data(df)
            
            if distances_m is None:
                # No distance data - use simple mean
                wt_mm = wt_mm.ffill().bfill()
                avg_wt_mm = float(wt_mm.mean()) if not wt_mm.empty else (od_inches * 25.4 * 0.06)
                return avg_wt_mm if dist_unit == 'km' else (avg_wt_mm / 25.4)

            # Clean and process data
            valid_mask = wt_mm.notna() & distances_m.notna()
            if not valid_mask.any():
                avg_wt_mm = od_inches * 25.4 * 0.06
                return avg_wt_mm if dist_unit == 'km' else (avg_wt_mm / 25.4)

            wt_clean = wt_mm[valid_mask].values
            dist_clean = distances_m[valid_mask].values

            # Sort by distance
            sort_idx = np.argsort(dist_clean)
            wt_clean = wt_clean[sort_idx]
            dist_clean = dist_clean[sort_idx]

            # Calculate volume-conserving wall thickness
            avg_wt_mm = self._calculate_volume_conserving_thickness(
                wt_clean, dist_clean, od_inches
            )

            # Apply reasonable bounds
            min_wt = 0.1  # minimum 0.1mm
            max_wt = od_inches * 25.4 / 4.0  # maximum 25% of OD
            avg_wt_mm = max(min_wt, min(max_wt, avg_wt_mm))

            # Return in appropriate units
            return avg_wt_mm if dist_unit == 'km' else (avg_wt_mm / 25.4)

        except Exception as e:
            self.logger.error(f"Error calculating volume conserving WT: {e}")
            # Fallback calculation
            avg_wt_mm = od_inches * 25.4 * 0.06
            return avg_wt_mm if dist_unit == 'km' else (avg_wt_mm / 25.4)

    def _get_distance_data(self, df: pd.DataFrame) -> Optional[pd.Series]:
        """Extract distance data from dataframe."""
        if 'DistanceMeters' in df.columns:
            return pd.to_numeric(df['DistanceMeters'], errors='coerce')
        elif 'JointDistanceMeters' in df.columns:
            return pd.to_numeric(df['JointDistanceMeters'], errors='coerce')
        else:
            return None

    def _calculate_volume_conserving_thickness(
        self,
        wt_clean: np.ndarray,
        dist_clean: np.ndarray,
        od_inches: float
    ) -> float:
        """Calculate the volume-conserving wall thickness."""
        if len(wt_clean) == 1:
            return float(wt_clean[0])
        elif len(wt_clean) == 2:
            return float((wt_clean[0] + wt_clean[1]) / 2.0)
        else:
            # Multiple points - use distance-weighted integration
            segment_lengths = np.diff(dist_clean)
            od_mm = od_inches * 25.4

            steel_volumes = []
            for i in range(len(segment_lengths)):
                wt_segment = wt_clean[i]
                length_segment = segment_lengths[i]

                if wt_segment > 0 and length_segment > 0:
                    # Cross-sectional area of steel
                    r_outer = od_mm / 2.0
                    r_inner = max(0, r_outer - wt_segment)
                    steel_area_mm2 = np.pi * (r_outer**2 - r_inner**2)
                    
                    # Volume of steel in this segment
                    steel_volume = steel_area_mm2 * length_segment * 1000  # mm³
                    steel_volumes.append(steel_volume)
                else:
                    steel_volumes.append(0.0)

            if steel_volumes:
                total_steel_volume = sum(steel_volumes)
                total_length_mm = sum(segment_lengths) * 1000
                r_outer_mm = od_mm / 2.0

                if total_length_mm > 0:
                    inner_radius_squared = r_outer_mm**2 - (total_steel_volume / (np.pi * total_length_mm))
                    if inner_radius_squared > 0:
                        return r_outer_mm - np.sqrt(inner_radius_squared)

            # Fallback to simple average
            return float(wt_clean.mean())

    def create_wt_dataframe(
        self,
        df_current: pd.DataFrame,
        reduced_df: Optional[pd.DataFrame] = None,
        dist_unit: str = 'mi'
    ) -> pd.DataFrame:
        """
        Create a wall thickness CSV DataFrame with distance and WT data.
        
        Args:
            df_current: Full elevation profile data
            reduced_df: Reduced/simplified elevation data (optional)
            dist_unit: Distance unit ('km', 'mi', 'm')
            
        Returns:
            DataFrame with distance and wall thickness data
        """
        try:
            if df_current.empty:
                return pd.DataFrame(columns=['Distance', 'WallThickness'])

            # Get distance and wall thickness from original data
            distances_m = self._get_distance_data(df_current)
            if distances_m is None:
                distances_m = pd.Series(range(len(df_current)), dtype=float)

            # Convert distances to user units
            distances = self._convert_distances(distances_m, dist_unit)

            # Get wall thickness data
            wall_thickness_mm = self._get_wall_thickness_data(df_current)

            # Process reduced data if available
            if reduced_df is not None and not reduced_df.empty and 'OrigRowID' in reduced_df.columns:
                distances, wall_thickness_mm = self._sample_reduced_data(
                    reduced_df, distances, wall_thickness_mm, df_current
                )

            # Subsample if too many points
            if len(distances) > 1000:
                distances, wall_thickness_mm = self._subsample_wt_data(distances, wall_thickness_mm)

            # Clean and interpolate data
            wall_thickness_mm = self._clean_wt_data(wall_thickness_mm)

            # Convert units and create final DataFrame
            return self._create_final_wt_dataframe(distances, wall_thickness_mm, dist_unit)

        except Exception as e:
            self.logger.error(f"Error creating WT dataframe: {e}")
            return pd.DataFrame(columns=['Distance', 'WallThickness'])

    def _convert_distances(self, distances_m: pd.Series, dist_unit: str) -> pd.Series:
        """Convert distances to user units."""
        if dist_unit == 'km':
            return distances_m / 1000.0
        elif dist_unit == 'mi':
            return distances_m * 0.000621371
        else:
            return distances_m.copy()

    def _get_wall_thickness_data(self, df_current: pd.DataFrame) -> pd.Series:
        """Get wall thickness data from dataframe."""
        if 'NominalWallThicknessMillimeters' in df_current.columns:
            return pd.to_numeric(df_current['NominalWallThicknessMillimeters'], errors='coerce')
        else:
            return pd.Series([12.7] * len(df_current))

    def _sample_reduced_data(
        self,
        reduced_df: pd.DataFrame,
        distances: pd.Series,
        wall_thickness_mm: pd.Series,
        df_current: pd.DataFrame
    ) -> Tuple[pd.Series, pd.Series]:
        """Sample data based on reduced dataframe."""
        sampled_distances = []
        sampled_wt = []

        for orig_id in reduced_df['OrigRowID']:
            try:
                orig_idx = int(orig_id)
                if 0 <= orig_idx < len(df_current):
                    dist_val = distances.iloc[orig_idx]
                    wt_val = wall_thickness_mm.iloc[orig_idx]

                    if pd.notna(dist_val) and pd.notna(wt_val):
                        sampled_distances.append(dist_val)
                        sampled_wt.append(wt_val)
                    elif pd.notna(dist_val):
                        # Interpolate missing WT
                        wt_interp = self._interpolate_wt(distances, wall_thickness_mm, orig_idx)
                        sampled_distances.append(dist_val)
                        sampled_wt.append(wt_interp)
            except Exception:
                continue

        if sampled_distances:
            return pd.Series(sampled_distances), pd.Series(sampled_wt)
        else:
            return distances, wall_thickness_mm

    def _interpolate_wt(
        self,
        distances: pd.Series,
        wall_thickness_mm: pd.Series,
        orig_idx: int
    ) -> float:
        """Interpolate wall thickness at a given index."""
        try:
            valid_wt_mask = wall_thickness_mm.notna()
            if valid_wt_mask.sum() > 1:
                return np.interp(
                    [distances.iloc[orig_idx]],
                    distances[valid_wt_mask].values,
                    wall_thickness_mm[valid_wt_mask].values
                )[0]
        except:
            pass
        return 12.7  # fallback

    def _subsample_wt_data(
        self,
        distances: pd.Series,
        wall_thickness_mm: pd.Series
    ) -> Tuple[pd.Series, pd.Series]:
        """Subsample wall thickness data to reduce size."""
        # Remove NaN values
        valid_mask = distances.notna() & wall_thickness_mm.notna()
        distances = distances[valid_mask]
        wall_thickness_mm = wall_thickness_mm[valid_mask]

        if len(distances) > 1000:
            # Sample based on WT variation
            wt_diff = np.abs(np.diff(wall_thickness_mm.values))
            wt_diff = np.append(wt_diff, 0)

            importance = wt_diff / (wt_diff.max() + 1e-6)
            importance = importance + 0.1

            n_samples = min(1000, len(distances))
            sample_prob = importance / importance.sum() * n_samples
            sample_prob = np.minimum(sample_prob, 1.0)

            # Add uniform sampling
            uniform_indices = np.linspace(0, len(distances)-1, n_samples//4, dtype=int)

            keep_mask = np.random.random(len(distances)) < sample_prob
            keep_mask[uniform_indices] = True
            keep_mask[0] = True  # Always keep first
            keep_mask[-1] = True  # Always keep last

            distances = distances[keep_mask].reset_index(drop=True)
            wall_thickness_mm = wall_thickness_mm[keep_mask].reset_index(drop=True)

        return distances, wall_thickness_mm

    def _clean_wt_data(self, wall_thickness_mm: pd.Series) -> pd.Series:
        """Clean wall thickness data by interpolating small gaps."""
        if wall_thickness_mm.notna().sum() == 0:
            return pd.Series([12.7] * len(wall_thickness_mm))

        # Interpolate small gaps only
        mask_na = wall_thickness_mm.isna()
        if mask_na.any():
            # Identify runs of NaN values
            runs = self._find_nan_runs(mask_na)
            
            # Interpolate short gaps (≤3 points)
            for start_idx, end_idx in runs:
                if end_idx - start_idx <= 3:
                    wall_thickness_mm = self._interpolate_gap(
                        wall_thickness_mm, start_idx, end_idx
                    )

            # Fill remaining NaN values
            wall_thickness_mm = wall_thickness_mm.ffill().bfill().fillna(12.7)

        return wall_thickness_mm

    def _find_nan_runs(self, mask_na: pd.Series) -> List[Tuple[int, int]]:
        """Find runs of consecutive NaN values."""
        runs = []
        start = None
        
        for i, is_na in enumerate(mask_na):
            if is_na and start is None:
                start = i
            elif not is_na and start is not None:
                runs.append((start, i))
                start = None
                
        if start is not None:
            runs.append((start, len(mask_na)))
            
        return runs

    def _interpolate_gap(
        self,
        wall_thickness_mm: pd.Series,
        start_idx: int,
        end_idx: int
    ) -> pd.Series:
        """Interpolate a gap in wall thickness data."""
        for idx in range(start_idx, end_idx):
            if start_idx > 0 and end_idx < len(wall_thickness_mm):
                before_val = wall_thickness_mm.iloc[start_idx - 1]
                after_val = wall_thickness_mm.iloc[end_idx]
                ratio = (idx - start_idx + 1) / (end_idx - start_idx + 1)
                wall_thickness_mm.iloc[idx] = before_val + ratio * (after_val - before_val)
        
        return wall_thickness_mm

    def _create_final_wt_dataframe(
        self,
        distances: pd.Series,
        wall_thickness_mm: pd.Series,
        dist_unit: str
    ) -> pd.DataFrame:
        """Create the final wall thickness dataframe."""
        # Convert units
        if dist_unit == 'km':
            wt_final = wall_thickness_mm  # Keep in mm
            wt_header = 'WallThickness_mm'
        else:
            wt_final = wall_thickness_mm / 25.4  # Convert to inches
            wt_header = 'WallThickness_in'

        # Create DataFrame
        result_df = pd.DataFrame({
            'Distance': distances.round(6),
            wt_header: wt_final.round(4)
        })

        # Final cleanup
        return result_df.dropna().reset_index(drop=True)

    def compute_top_n_deviations(
        self,
        df: pd.DataFrame,
        flags: np.ndarray,
        n: int = 5
    ) -> List[Tuple[float, int]]:
        """
        Compute the top N largest deviations from the RDP simplified line.
        
        Args:
            df: Original DataFrame with elevation data
            flags: RDP flags indicating kept points
            n: Number of top deviations to return
            
        Returns:
            List of (deviation, index) tuples sorted by deviation magnitude
        """
        try:
            x = df['Milepost'].to_numpy(dtype=float)
            y = df['Elevation'].to_numpy(dtype=float)
            kept_idx = np.where(flags != 0)[0]
            
            deviations = []
            
            for start, end in zip(kept_idx[:-1], kept_idx[1:]):
                x1, y1 = x[start], y[start]
                x2, y2 = x[end], y[end]
                idxs = np.arange(start, end + 1)
                
                px = x[idxs]
                py = y[idxs]
                dx = (x2 - x1)
                
                if dx == 0:
                    y_line = np.full_like(py, y1, dtype=float)
                else:
                    t = (px - x1) / dx
                    y_line = y1 + t * (y2 - y1)
                    
                dists = np.abs(py - y_line)
                
                for rel_idx, dist in enumerate(dists):
                    deviations.append((float(dist), int(idxs[rel_idx])))
                    
            # Sort by deviation magnitude
            deviations.sort(reverse=True, key=lambda tup: tup[0])
            
            # Remove duplicates and return top N
            seen = set()
            top_n = []
            
            for dev, idx in deviations:
                if idx not in seen:
                    top_n.append((dev, idx))
                    seen.add(idx)
                if len(top_n) == n:
                    break
                    
            return top_n
            
        except Exception as e:
            self.logger.error(f"Error computing top deviations: {e}")
            return []
