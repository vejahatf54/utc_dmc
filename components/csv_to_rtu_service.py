"""
CSV to RTU Converter Service

This service handles the conversion of CSV files to RTU format using the real sps_api TodremAPI.
Based on LDUTC implementation for real TodremAPI integration.
"""

import os
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime

# Real TodremAPI integration
try:
    from sps_api import TodremApi
    from sps_api.model import RtuDataModel
    SPS_API_AVAILABLE = True
except ImportError:
    SPS_API_AVAILABLE = False
    TodremApi = None
    RtuDataModel = None


class SpsTodremApiAdapter:
    """Adapter for the sps_api.TodremApi with proper resource management"""
    
    def __init__(self):
        if not SPS_API_AVAILABLE:
            raise ImportError("sps_api is not available; cannot use SpsTodremApiAdapter")
        self._api = TodremApi()
    
    def open_rtu_file(self, file_path: str, no_records: int) -> int:
        return self._api.open_rtu_file(file_path, no_records)
    
    def write_point(self, timestamp: datetime, tag_name: str, tag_value: float, quality: int) -> None:
        rtu_data = RtuDataModel(
            timestamp=timestamp,
            tag_name=tag_name,
            tag_value=tag_value,
            quality=quality,
        )
        self._api.write_to_rtu_file(rtu_data)
    
    def flush(self) -> None:
        self._api.flush_rtu_memory_buffer()
    
    def close(self) -> None:
        self._api.close_rtu_file()
    
    def dispose(self) -> None:
        """Best-effort flush+close and attempt additional shutdown hooks."""
        try:
            try:
                self.flush()
            except Exception:
                pass
            try:
                self.close()
            except Exception:
                pass
        finally:
            for name in ("dispose", "shutdown", "terminate", "disconnect", "finalize"):
                try:
                    fn = getattr(self._api, name, None)
                    if callable(fn):
                        fn()
                except Exception:
                    pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc, tb):
        try:
            self.dispose()
        finally:
            return False
    
    def __del__(self):
        try:
            self.dispose()
        except Exception:
            pass


class CsvToRtuService:
    def __init__(self):
        self.supported_extensions = ['.csv']
    
    def parse_timestamp(self, value: str) -> datetime:
        """Parse common timestamp formats with sensible fallback to now if invalid."""
        try:
            text = str(value)
            if "T" in text:
                # Handle Zulu suffix
                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"
                return datetime.fromisoformat(text)
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now()
    
    def parse_value_with_quality(self, text: Optional[str]) -> tuple[float, int]:
        """Parse text to float; returns (value, quality) where quality 1=good, 0=bad."""
        try:
            if text is None:
                return 0.0, 0
            s = str(text).strip()
            if s and s.lower() not in {"nan", "null", "none"}:
                return float(s), 1
            return 0.0, 0
        except Exception:
            return 0.0, 0
    
    def count_tags_and_records(self, df: pd.DataFrame) -> tuple[int, int, int]:
        """Return (number_of_tags, number_of_records, total_points)."""
        header = list(df.columns)
        number_of_tags = max(0, len(header) - 1)  # First column is timestamp
        number_of_records = len(df)
        total_points = number_of_tags * number_of_records
        return number_of_tags, number_of_records, total_points
    
    def validate_csv_file(self, file_path: str) -> Dict[str, Any]:
        """Validate a CSV file and return metadata"""
        try:
            if not os.path.exists(file_path):
                return {
                    'valid': False,
                    'error': 'File does not exist'
                }
            
            # Check file extension
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in self.supported_extensions:
                return {
                    'valid': False,
                    'error': f'Unsupported file extension: {ext}'
                }
            
            # Read CSV and validate structure
            df = pd.read_csv(file_path)
            
            if df.empty:
                return {
                    'valid': False,
                    'error': 'CSV file is empty'
                }
            
            # Check if first column could be timestamp
            first_col = df.columns[0]
            num_tags, num_records, total_points = self.count_tags_and_records(df)
            
            return {
                'valid': True,
                'columns': len(df.columns),
                'rows': len(df),
                'tags': num_tags,
                'total_points': total_points,
                'first_column': first_col,
                'size': os.path.getsize(file_path)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Error reading CSV file: {str(e)}'
            }
    
    def convert_single_csv_to_rtu(self, csv_file_path: str, output_dir: str) -> Dict[str, Any]:
        """Convert a single CSV file to RTU format using real TodremAPI"""
        
        if not SPS_API_AVAILABLE:
            return {
                "success": False, 
                "error": "sps_api is not available. Please install it to use RTU conversion."
            }
        
        opened = False
        api = None
        
        try:
            # Create RTU file path
            base_name = os.path.basename(csv_file_path).replace(".csv", ".dt")
            rtu_file_path = os.path.join(output_dir, base_name)
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Clean existing .dt file to avoid open failures
            if os.path.exists(rtu_file_path):
                try:
                    os.remove(rtu_file_path)
                except Exception:
                    pass  # Non-fatal
            
            # Read and validate CSV
            df = pd.read_csv(csv_file_path)
            if df.empty:
                return {"success": False, "error": "CSV file is empty"}
            
            header = list(df.columns)
            num_tags, num_records, total_points = self.count_tags_and_records(df)
            
            # Initialize API
            api = SpsTodremApiAdapter()
            
            # Open RTU file
            channel = api.open_rtu_file(rtu_file_path, total_points)
            if channel == 0:
                return {"success": False, "error": "Failed to open RTU file"}
            opened = True
            
            tags_written = 0
            
            # Process each row
            for _, row in df.iterrows():
                timestamp = self.parse_timestamp(row.iloc[0])
                
                # Process each tag column (skip timestamp column)
                for col_index in range(1, len(header)):
                    tag_name = header[col_index]
                    value_text = row.iloc[col_index]
                    value, quality = self.parse_value_with_quality(value_text)
                    api.write_point(timestamp, tag_name, value, quality)
                    tags_written += 1
            
            return {
                "success": True,
                "records_processed": num_records,
                "tags_written": tags_written,
                "rtu_file": os.path.basename(rtu_file_path),
                "rtu_file_path": rtu_file_path
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error converting CSV to RTU: {str(e)}"}
        finally:
            # Always attempt to flush and close if we opened a file
            if opened and api:
                try:
                    api.flush()
                except Exception:
                    pass
                try:
                    api.close()
                except Exception:
                    pass
            
            # Dispose of API resources
            if api:
                try:
                    api.dispose()
                except Exception:
                    pass
    
    def convert_to_rtu(self, csv_file_paths: List[str], output_directory: str) -> Dict[str, Any]:
        """Convert multiple CSV files to RTU format"""
        try:
            if not SPS_API_AVAILABLE:
                return {
                    'success': False,
                    'error': 'sps_api is not available. Please install it to use RTU conversion.'
                }
            
            results = []
            successful_conversions = 0
            
            for file_path in csv_file_paths:
                filename = os.path.basename(file_path)
                result = self.convert_single_csv_to_rtu(file_path, output_directory)
                
                if result['success']:
                    successful_conversions += 1
                    results.append({
                        'file': filename,
                        'status': 'success',
                        'output_file': result['rtu_file'],
                        'records_processed': result['records_processed'],
                        'tags_written': result['tags_written']
                    })
                else:
                    results.append({
                        'file': filename,
                        'status': 'failed',
                        'error': result['error']
                    })
            
            if successful_conversions == 0:
                return {
                    'success': False,
                    'error': 'No files were successfully converted',
                    'results': results
                }
            
            return {
                'success': True,
                'message': f'Successfully converted {successful_conversions} of {len(csv_file_paths)} files',
                'results': results,
                'output_directory': output_directory,
                'successful_conversions': successful_conversions,
                'total_files': len(csv_file_paths)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error converting files: {str(e)}'
            }
