"""
Module to fetch MBS elevation data from external folders for comparison with database profiles.

Fixes:
- Normalize model Milepost/Elevation to meters so it aligns with DB data (meters).
- Provide consistent columns DistanceMeters & ElevationMeters for downstream UI.
- Include lightweight unit metadata inferred from folder/file names (mi/km/ft/m).
"""
import os
import re
import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from services.exceptions import ServiceError, DataProcessingError

logger = logging.getLogger(__name__)


class ElevationDataService:
    """Service for handling MBS elevation data processing and validation."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ElevationDataService")


def extract_elevation_profile(folder_path: str) -> Optional[pd.DataFrame]:
    """
    Extracts continuous elevation profile DataFrame from inprep.txt
    or from l*.inprep by running demac.
    Ensures no duplicate mileposts at pipe boundaries.

    Args:
        folder_path: Path to folder containing MBS files
        
    Returns:
        DataFrame with elevation profile data or None if failed
        
    Raises:
        ServiceError: If critical processing errors occur
        DataProcessingError: If data format/validation issues occur
    """
    service_logger = logging.getLogger(f"{__name__}.extract_elevation_profile")
    
    try:
        service_logger.info(f"Starting elevation profile extraction from: {folder_path}")
        
        if not os.path.exists(folder_path):
            raise ServiceError(f"Folder does not exist: {folder_path}")
            
        if not os.path.isdir(folder_path):
            raise ServiceError(f"Path is not a directory: {folder_path}")
        
        # Step 1: Try to find l*.inprep
        inprep_file = None
        try:
            folder_contents = os.listdir(folder_path)
            service_logger.debug(f"Folder contains {len(folder_contents)} files")
            
            for f in folder_contents:
                if re.match(r"l.*\.inprep$", f, re.IGNORECASE):
                    inprep_file = f
                    break
                    
            if inprep_file:
                service_logger.info(f"Found inprep file: {inprep_file}")
                
        except OSError as e:
            raise ServiceError(f"Cannot access folder contents: {e}") from e

        # Step 2: Define output text file
        inprep_txt = os.path.join(folder_path, "inprep.txt")

        # Step 3: Generate inprep.txt if needed
        if inprep_file:
            service_logger.info(f"Running demac to generate inprep.txt from {inprep_file}")
            try:
                result = os.system(f'cd "{folder_path}" && demac {inprep_file} inprep.txt')
                if result != 0:
                    service_logger.warning(f"demac command returned non-zero exit code: {result}")
            except Exception as e:
                service_logger.error(f"Error running demac: {e}")
                raise ServiceError(f"Failed to run demac: {e}") from e
                
        elif not os.path.exists(inprep_txt):
            raise DataProcessingError("Neither l*.inprep nor inprep.txt found in folder")

        # Step 4: Parse inprep.txt
        try:
            service_logger.info("Parsing inprep.txt file")
            with open(inprep_txt, "r", encoding='utf-8', errors='ignore') as f:
                lines = [line for line in f.readlines() if line.strip()
                         and not line.strip().startswith("/*")]
            service_logger.debug(f"Read {len(lines)} non-empty, non-comment lines")
            
        except (IOError, OSError) as e:
            raise ServiceError(f"Cannot read inprep.txt file: {e}") from e

        profile_data = []
        chainage_offset = 0.0
        pipe_number = 1  # track which pipe data came from
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()

            if "PIPE.DIST ELEV" in line or "HORIZ.DIST  ELEV" in line:
                use_horiz_dist = "HORIZ.DIST" in line
                service_logger.debug(f"Processing pipe {pipe_number} with {'horizontal' if use_horiz_dist else 'pipe'} distance")
                i += 1
                pipe_data = []

                # Read until blank or new pipe header
                while (i < len(lines) and lines[i].strip() and 
                       not lines[i].strip().startswith("+") and 
                       not ("PIPE.DIST ELEV" in lines[i] or "HORIZ.DIST  ELEV" in lines[i])):
                    parts = lines[i].split()
                    if len(parts) >= 2:
                        try:
                            dist = float(parts[0])
                            elev = float(parts[1])
                            pipe_data.append((dist, elev))
                        except (ValueError, IndexError) as e:
                            service_logger.warning(f"Skipping invalid data line: {lines[i].strip()}")
                    i += 1

                # Process pipe data if found
                if pipe_data:
                    service_logger.debug(f"Found {len(pipe_data)} elevation points for pipe {pipe_number}")
                    
                    if use_horiz_dist:
                        # Convert horizontal distances to chainage
                        converted = []
                        cum_len = 0.0
                        converted.append((0.0, pipe_data[0][1]))  # start point
                        
                        for j in range(1, len(pipe_data)):
                            dx = pipe_data[j][0] - pipe_data[j-1][0]
                            dy = pipe_data[j][1] - pipe_data[j-1][1]
                            seg_len = np.sqrt(dx**2 + dy**2)
                            cum_len += seg_len
                            converted.append((cum_len, pipe_data[j][1]))
                        pipe_data = converted
                    else:
                        # Normalize PIPE.DIST to start at zero
                        start_d = pipe_data[0][0]
                        pipe_data = [(d - start_d, e) for (d, e) in pipe_data]

                    # Apply offset so pipes are continuous
                    for j, (d, e) in enumerate(pipe_data):
                        milepost = chainage_offset + d
                        # Avoid duplicate milepost at pipe boundary
                        if profile_data and np.isclose(milepost, profile_data[-1][0]):
                            continue
                        profile_data.append((milepost, e, pipe_number))

                    chainage_offset = profile_data[-1][0] if profile_data else 0.0
                    
                pipe_number += 1
            else:
                i += 1

        if not profile_data:
            service_logger.warning("No elevation profile data found in file")
            # Return empty DataFrame with expected columns to maintain consistency
            return pd.DataFrame(columns=["Milepost", "Elevation", "Pipe"])

        df = pd.DataFrame(profile_data, columns=["Milepost", "Elevation", "Pipe"])
        service_logger.info(f"Successfully extracted {len(df)} elevation points from {pipe_number-1} pipes")
        
        return df
        
    except (ServiceError, DataProcessingError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        service_logger.error(f"Unexpected error in elevation profile extraction: {e}")
        raise ServiceError(f"Elevation profile extraction failed: {e}") from e


def _infer_units_from_inprep(folder_path: str) -> Dict[str, str]:
    """
    Determine units by inspecting inprep.txt (created after running demac).
    If it contains '=METRIC', use distance 'km' and elevation 'm'.
    If it contains '=ENGLISH', use distance 'mi' and elevation 'ft'.
    Otherwise, default to 'mi' and 'ft'.
    
    Args:
        folder_path: Path to folder containing inprep.txt
        
    Returns:
        Dict with 'distance' and 'elevation' unit keys
        
    Raises:
        ServiceError: If file reading fails unexpectedly
    """
    service_logger = logging.getLogger(f"{__name__}._infer_units_from_inprep")
    
    try:
        inprep_path = os.path.join(folder_path, "inprep.txt")
        
        if not os.path.isfile(inprep_path):
            service_logger.debug("inprep.txt not found, using default units")
            return {"distance": "mi", "elevation": "ft"}
            
        service_logger.debug(f"Reading units from {inprep_path}")
        
        with open(inprep_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
            
        # Look for explicit unit flags written by MBS/DEMAnC workflows
        if "=metric" in content:
            service_logger.info("Detected metric units from inprep.txt")
            return {"distance": "km", "elevation": "m"}
            
        if "=english" in content:
            service_logger.info("Detected English units from inprep.txt")
            return {"distance": "mi", "elevation": "ft"}
            
        service_logger.debug("No explicit units found, using default imperial units")
        return {"distance": "mi", "elevation": "ft"}
        
    except (OSError, IOError) as e:
        service_logger.warning(f"Error reading inprep.txt for units: {e}, using defaults")
        return {"distance": "mi", "elevation": "ft"}
    except Exception as e:
        service_logger.error(f"Unexpected error inferring units: {e}")
        raise ServiceError(f"Failed to infer units from inprep.txt: {e}") from e


def fetch_elevation_profile(folder_path: str) -> Optional[pd.DataFrame]:
    """
    Wrapper function to fetch elevation profile data from a given folder path.
    Uses the existing extract_elevation_profile function.

    Args:
        folder_path: Path to the folder containing MBS inprep files

    Returns:
        DataFrame with normalized meter columns:
            - DistanceMeters
            - ElevationMeters
        Also retains original columns Milepost & Elevation for reference.
        Returns None if processing fails.
        
    Raises:
        ServiceError: For critical processing errors
        DataProcessingError: For data validation/format issues
    """
    service_logger = logging.getLogger(f"{__name__}.fetch_elevation_profile")
    
    try:
        service_logger.info(f"Fetching elevation profile from: {folder_path}")
        
        if not folder_path:
            raise ServiceError("Folder path is empty or None")
            
        if not os.path.exists(folder_path):
            service_logger.warning(f"Folder does not exist: {folder_path}")
            return None

        if not os.path.isdir(folder_path):
            service_logger.warning(f"Path is not a directory: {folder_path}")
            return None

        # Use the existing extract_elevation_profile function
        df = extract_elevation_profile(folder_path)

        if df is None or df.empty:
            service_logger.warning("No elevation data extracted from folder")
            return None

        service_logger.debug(f"Extracted {len(df)} raw elevation points")

        # Clean and validate data
        try:
            df = df.dropna(subset=["Milepost", "Elevation"]).copy()
            df = df.sort_values("Milepost").reset_index(drop=True)
            service_logger.debug(f"After cleaning: {len(df)} valid points")
            
        except Exception as e:
            raise DataProcessingError(f"Error cleaning elevation data: {e}") from e

        if df.empty:
            service_logger.warning("No valid elevation data after cleaning")
            return None

        # Infer source units from inprep.txt flags; fall back to defaults
        try:
            units = _infer_units_from_inprep(folder_path)
            dist_u = units.get("distance", "mi")
            elev_u = units.get("elevation", "ft")
            service_logger.info(f"Using units: distance={dist_u}, elevation={elev_u}")
            
        except Exception as e:
            service_logger.warning(f"Error inferring units, using defaults: {e}")
            dist_u, elev_u = "mi", "ft"

        # Convert to meters with proper error handling
        try:
            if dist_u == "mi":
                dist_m = df["Milepost"].astype(float) * 1609.344
            elif dist_u == "km":
                dist_m = df["Milepost"].astype(float) * 1000.0
            else:  # already meters
                dist_m = df["Milepost"].astype(float)

            if elev_u == "ft":
                elev_m = df["Elevation"].astype(float) * 0.3048
            else:  # meters
                elev_m = df["Elevation"].astype(float)
                
            # Validate converted values
            if not np.all(np.isfinite(dist_m)) or not np.all(np.isfinite(elev_m)):
                raise DataProcessingError("Invalid values found after unit conversion")
                
        except Exception as e:
            raise DataProcessingError(f"Error converting units to meters: {e}") from e

        # Create result dataframe
        try:
            df_result = df.copy()
            df_result["DistanceMeters"] = dist_m
            df_result["ElevationMeters"] = elev_m

            # Keep essential columns only (plus originals for reference)
            df_result = df_result[["Milepost", "Elevation", "DistanceMeters", "ElevationMeters"]]
            
        except Exception as e:
            raise DataProcessingError(f"Error creating result dataframe: {e}") from e

        service_logger.info(f"Successfully processed elevation profile: {len(df_result)} points, "
                           f"distance range: {df_result['DistanceMeters'].min():.1f}-{df_result['DistanceMeters'].max():.1f}m, "
                           f"elevation range: {df_result['ElevationMeters'].min():.1f}-{df_result['ElevationMeters'].max():.1f}m")

        return df_result

    except (ServiceError, DataProcessingError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        service_logger.error(f"Unexpected error fetching elevation profile from {folder_path}: {e}")
        return None


def validate_elevation_data(df: pd.DataFrame) -> bool:
    """
    Validate the elevation data format.

    Args:
        df: DataFrame to validate

    Returns:
        True if valid, False otherwise
    """
    service_logger = logging.getLogger(f"{__name__}.validate_elevation_data")
    
    try:
        if df is None:
            service_logger.debug("DataFrame is None")
            return False
            
        if df.empty:
            service_logger.debug("DataFrame is empty")
            return False

        # Accept either normalized meter columns or the original columns
        if set(["DistanceMeters", "ElevationMeters"]).issubset(df.columns):
            cols = ["DistanceMeters", "ElevationMeters"]
            service_logger.debug("Found normalized meter columns")
        elif set(["Milepost", "Elevation"]).issubset(df.columns):
            cols = ["Milepost", "Elevation"]
            service_logger.debug("Found original columns")
        else:
            service_logger.warning(f"Required columns not found. Available: {list(df.columns)}")
            return False

        # Check for null values
        null_count = df[cols].isnull().sum().sum()
        if null_count > 0:
            service_logger.warning(f"Found {null_count} null values in elevation data")
            return False
            
        # Check for infinite values
        inf_count = np.isinf(df[cols]).sum().sum()
        if inf_count > 0:
            service_logger.warning(f"Found {inf_count} infinite values in elevation data")
            return False

        service_logger.debug(f"Validation passed for {len(df)} elevation points")
        return True
        
    except Exception as e:
        service_logger.error(f"Error validating elevation data: {e}")
        return False
