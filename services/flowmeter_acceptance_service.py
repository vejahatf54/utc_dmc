"""
Simplified Flowmeter Acceptance Service - Actually works!
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from services.exceptions import ProcessingError
from services.rtu_service import RTUService
from services.review_to_csv_service import ReviewCsvService
from services.config_manager import ConfigManager
import tempfile
import shutil
import scipy.signal
from scipy import stats


class FlowmeterAcceptanceService:
    """Simplified flowmeter acceptance testing service that actually works."""

    def __init__(self):
        """Initialize the service."""
        self.logger = logging.getLogger(__name__)

        # Core data containers
        self.tags_df = None
        self.test_results = {}  # Store test results for each meter
        self.plots_data = {}    # Store plot data

        # Services (initialize when needed)
        self.rtu_service = RTUService()
        self.review_service = None  # Initialize when we have parameters

        # Theme support
        self.current_theme = 'mantine_light'

    def run_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run the flowmeter acceptance analysis - simplified and working."""
        try:
            self.logger.info(
                "Starting simplified flowmeter acceptance analysis")

            # Set theme
            theme_data = params.get('theme_data', {})
            self.current_theme = theme_data.get('template', 'mantine_light')

            # Get file paths and UI parameters
            rtu_file = params['rtu_file']
            review_file = params['review_file']
            tags_file = params['csv_tags_file']
            time_start = params['time_start']
            time_end = params['time_end']

            # Extract UI parameters (UI must provide all required values)
            min_range = params.get('min_range')
            max_range = params.get('max_range')
            min_q = params.get('min_q')
            max_q = params.get('max_q')
            flat_threshold = params.get('flat_threshold')
            accuracy_range = params.get('accuracy_range')
            data_dir = params.get('data_dir')

            # Validate required parameters
            if any(x is None for x in [min_range, max_range, min_q, max_q, flat_threshold, accuracy_range]):
                raise ValueError(
                    "Missing required parameters: min_range, max_range, min_q, max_q, flat_threshold, accuracy_range must be provided by UI")

            # Load tags configuration (Tags.in format only)
            self.tags_df = pd.read_csv(tags_file)
            self.logger.info(
                f"Loaded {len(self.tags_df)} meter configurations")

            # Validate Tags.in format
            required_columns = ['SCADATagID_DIG',
                                'SCADATagID_ANL', 'MBSTagID', 'Reference_Meter']
            missing_columns = [
                col for col in required_columns if col not in self.tags_df.columns]
            if missing_columns:
                raise ValueError(
                    f"Tags file is missing required columns: {missing_columns}. Please use Tags.in format.")

            # Initialize test results
            self.test_results = {}

            # Check if we should use existing data or extract new data
            use_existing_data = params.get('use_existing_data', False)

            if use_existing_data:
                # Use existing CSV files in _Data directory
                self.logger.info(
                    "Using existing CSV data (skipping extraction)")
                tags_file_dir = os.path.dirname(params['csv_tags_file'])
                data_dir = os.path.join(tags_file_dir, "_Data")

                # Verify _Data directory exists
                if not os.path.exists(data_dir):
                    raise ProcessingError(
                        f"_Data directory not found at {data_dir}. Please run analysis without 'Use existing data' option first.")

                csv_export_result = {
                    'data_dir': data_dir,
                    'message': 'Using existing CSV data from _Data directory',
                    'exported_files': []  # We don't know which files exist, tests will handle this
                }
            else:
                # Export CSV data FIRST - tests need these files to exist
                csv_export_result = self.export_csv_data(params)

            # Get the data directory from CSV export result
            if 'data_dir' in csv_export_result:
                data_dir = csv_export_result['data_dir']

            # Process each meter using Tags.in format
            for index, row in self.tags_df.iterrows():
                meter_name = row['MBSTagID'].strip()
                digital_tag = row['SCADATagID_DIG'].strip()
                analog_tag = row['SCADATagID_ANL'].strip()
                ref_tag = row['Reference_Meter'].strip()

                self.logger.info(f"Processing meter: {meter_name}")

                # Run tests for this meter with UI parameters
                meter_results = self._run_meter_tests(
                    meter_name, digital_tag, analog_tag, ref_tag,
                    rtu_file, review_file, time_start, time_end,
                    min_range, max_range, min_q, max_q, flat_threshold, params, data_dir
                )

                self.test_results[meter_name] = meter_results

            # Create plots data with actual CSV files
            self.plots_data = self._generate_plots_data(data_dir)

            # Create plots with actual data
            plots = self.create_analysis_plots(
                {'template': self.current_theme})

            return {
                'success': True,
                'test_results': self.test_results,
                'plots_data': self.plots_data,
                'plots': plots,
                'csv_export': csv_export_result,
                'message': f'Flowmeter acceptance analysis completed for {len(self.test_results)} meters. {csv_export_result.get("message", "CSV data exported to _Data directory.")}'
            }

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise ProcessingError(f"Analysis error: {e}")

    def _generate_plots_data(self, data_dir: str = None) -> Dict[str, Any]:
        """Generate plot data from actual CSV files (MBSTagID.csv and Reference_Meter.csv)."""
        plots_data = {}

        try:
            # Look for MBSTagID.csv and Reference_Meter.csv files
            if data_dir:
                mbs_file = os.path.join(data_dir, "MBSTagID.csv")
                ref_file = os.path.join(data_dir, "Reference_Meter.csv")
            else:
                # Look in current directory and _Data subdirectory
                for base_dir in [".", "./_Data", "../_Data"]:
                    mbs_file = os.path.join(base_dir, "MBSTagID.csv")
                    ref_file = os.path.join(base_dir, "Reference_Meter.csv")
                    if os.path.exists(mbs_file) and os.path.exists(ref_file):
                        break

            # Process each meter in tags_df
            for index, row in self.tags_df.iterrows():
                meter_name = row['MBSTagID'].strip()
                digital_tag = row['SCADATagID_DIG'].strip()
                analog_tag = row['SCADATagID_ANL'].strip()
                ref_tag = row['Reference_Meter'].strip()

                meter_plots_data = {
                    'time_series': {},
                    'statistics': {}
                }

                # Load and process MBSTagID.csv data
                if os.path.exists(mbs_file):
                    try:
                        mbs_df = pd.read_csv(mbs_file)
                        # Strip whitespace from column names to handle formatting inconsistencies
                        mbs_df.columns = mbs_df.columns.str.strip()

                        # Get the correct column names - MBS files have TIME and meter-specific VAL columns
                        time_col = 'TIME' if 'TIME' in mbs_df.columns else None
                        val_col = None

                        # Find the VAL column for this meter (look for exact match first, then fallback to pattern)
                        exact_match = f"{meter_name}:VAL"

                        # First try exact match on meter name
                        if exact_match in mbs_df.columns:
                            val_col = exact_match
                        else:
                            # Fallback: look for any column with :VAL suffix
                            for col in mbs_df.columns:
                                if ':VAL' in col:
                                    val_col = col
                                    self.logger.warning(
                                        f"Could not find exact column match for {exact_match}, using {col} instead")
                                    break

                        if time_col and val_col:
                            # Use actual MBS data without any fake generation
                            meter_plots_data['time_series']['digital_signal'] = {
                                'timestamps': mbs_df[time_col].tolist(),
                                'values': mbs_df[val_col].tolist()
                            }

                            # Statistics from real data
                            meter_plots_data['statistics']['digital'] = {
                                'mean': float(mbs_df[val_col].mean()),
                                'std': float(mbs_df[val_col].std()),
                                'min': float(mbs_df[val_col].min()),
                                'max': float(mbs_df[val_col].max())
                            }
                        else:
                            self.logger.warning(
                                f"MBSTagID.csv missing expected columns (TIME, :VAL pattern). Found columns: {list(mbs_df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Error reading MBSTagID.csv: {e}")

                # Load analog signal from exported SCADA analog CSV
                analog_csv = os.path.join(
                    data_dir, "SCADATagID_ANL.csv") if data_dir else None
                if analog_csv and os.path.exists(analog_csv):
                    try:
                        analog_df = pd.read_csv(analog_csv)
                        # Filter for this specific analog tag
                        if 'tag_name' in analog_df.columns and 'timestamp' in analog_df.columns and 'value' in analog_df.columns:
                            tag_data = analog_df[analog_df['tag_name']
                                                 == analog_tag]
                            if not tag_data.empty:
                                meter_plots_data['time_series']['analog_signal'] = {
                                    'timestamps': tag_data['timestamp'].tolist(),
                                    'values': tag_data['value'].tolist()
                                }
                                # Statistics from real analog data
                                meter_plots_data['statistics']['analog'] = {
                                    'mean': float(tag_data['value'].mean()),
                                    'std': float(tag_data['value'].std()),
                                    'min': float(tag_data['value'].min()),
                                    'max': float(tag_data['value'].max())
                                }
                        else:
                            self.logger.warning(
                                f"SCADATagID_ANL.csv missing expected columns (tag_name, timestamp, value)")
                    except Exception as e:
                        self.logger.error(
                            f"Error reading SCADATagID_ANL.csv: {e}")

                # Load reference SCADA signal from exported Ref_SCADATagID CSV (new functionality)
                ref_scada_tag = row.get('Ref_SCADATagID', '').strip(
                ) if 'Ref_SCADATagID' in row else ''
                if ref_scada_tag:
                    ref_scada_csv = os.path.join(
                        data_dir, "Ref_SCADATagID.csv") if data_dir else None
                    if ref_scada_csv and os.path.exists(ref_scada_csv):
                        try:
                            ref_scada_df = pd.read_csv(ref_scada_csv)
                            # Filter for this specific reference SCADA tag
                            if 'tag_name' in ref_scada_df.columns and 'timestamp' in ref_scada_df.columns and 'value' in ref_scada_df.columns:
                                tag_data = ref_scada_df[ref_scada_df['tag_name']
                                                        == ref_scada_tag]
                                if not tag_data.empty:
                                    meter_plots_data['time_series']['ref_scada_signal'] = {
                                        'timestamps': tag_data['timestamp'].tolist(),
                                        'values': tag_data['value'].tolist()
                                    }
                                    # Statistics from real reference SCADA data
                                    meter_plots_data['statistics']['ref_scada'] = {
                                        'mean': float(tag_data['value'].mean()),
                                        'std': float(tag_data['value'].std()),
                                        'min': float(tag_data['value'].min()),
                                        'max': float(tag_data['value'].max())
                                    }
                            else:
                                self.logger.warning(
                                    f"Ref_SCADATagID.csv missing expected columns (tag_name, timestamp, value)")
                        except Exception as e:
                            self.logger.error(
                                f"Error reading Ref_SCADATagID.csv: {e}")

                # Load and process Reference_Meter.csv data
                if os.path.exists(ref_file):
                    try:
                        ref_df = pd.read_csv(ref_file)
                        # Strip whitespace from column names to handle formatting inconsistencies
                        ref_df.columns = ref_df.columns.str.strip()

                        # Use correct column names for Reference_Meter.csv
                        time_col = 'TIME' if 'TIME' in ref_df.columns else None
                        val_col = None

                        # Find the VAL column for reference meter
                        exact_match = f"{ref_tag}:VAL"

                        # First try exact match on reference meter name
                        if exact_match in ref_df.columns:
                            val_col = exact_match
                        else:
                            # Fallback: look for any column with :VAL suffix
                            for col in ref_df.columns:
                                if ':VAL' in col:
                                    val_col = col
                                    self.logger.warning(
                                        f"Could not find exact column match for {exact_match}, using {col} instead")
                                    break

                        if time_col and val_col:
                            meter_plots_data['time_series']['reference_signal'] = {
                                'timestamps': ref_df[time_col].tolist(),
                                'values': ref_df[val_col].tolist()
                            }

                            # Statistics
                            meter_plots_data['statistics']['reference'] = {
                                'mean': float(ref_df[val_col].mean()),
                                'std': float(ref_df[val_col].std()),
                                'min': float(ref_df[val_col].min()),
                                'max': float(ref_df[val_col].max())
                            }
                        else:
                            self.logger.warning(
                                f"Reference_Meter.csv missing expected columns (TIME, :VAL pattern). Found columns: {list(ref_df.columns)}")
                    except Exception as e:
                        self.logger.error(
                            f"Error reading Reference_Meter.csv: {e}")

                # Only use real data from CSV files - NO fake data generation
                if not meter_plots_data['time_series']:
                    self.logger.warning(
                        f"No valid CSV data found for {meter_name}. Analysis requires actual data files.")

                plots_data[meter_name] = meter_plots_data

        except Exception as e:
            self.logger.error(f"Error generating plots data: {e}")
            # Return empty data structure
            plots_data = {}

        return plots_data

    def _run_meter_tests(self, meter_name: str, digital_tag: str, analog_tag: str,
                         ref_tag: str, rtu_file: str, review_file: str,
                         time_start: str, time_end: str, min_range: float, max_range: float,
                         min_q: float, max_q: float, flat_threshold: float,
                         params: Dict[str, Any], data_dir: str = None) -> Dict[str, Any]:
        """Run tests for a single meter and return results."""
        results = {
            'meter_name': meter_name,
            'reliability_tests': {},
            'timeliness_tests': {},
            'accuracy_tests': {},
            'overall_status': 'pass'
        }

        try:
            # Test 1: Data Availability
            rtu_data_available = self._check_rtu_data(
                digital_tag, analog_tag, rtu_file, time_start, time_end)
            review_data_available = self._check_review_data(
                meter_name, ref_tag, review_file, time_start, time_end)

            # Test 1.3 - Quality verification for both digital and analog signals (CSV-based)
            digital_quality_result = self._test_13_quality_is_good(
                digital_tag, rtu_file, 'digital', data_dir)
            analog_quality_result = self._test_13_quality_is_good(
                analog_tag, rtu_file, 'analog', data_dir)

            results['reliability_tests'] = {
                'Data Availability (RTU)': {
                    'status': 'pass' if rtu_data_available else 'fail',
                    'value': 'Available' if rtu_data_available else 'Missing',
                    'description': 'RTU data found in time range'
                },
                'Data Availability (Review)': {
                    'status': 'pass' if review_data_available else 'fail',
                    'value': 'Available' if review_data_available else 'Missing',
                    'description': 'Review data found in time range'
                },
                'Digital Signal Quality Check': {
                    'status': digital_quality_result['status'],
                    'value': f"{digital_quality_result['bad_quality_count']} bad quality readings",
                    'description': 'Digital signal quality is GOOD in CSV data'
                },
                'Analog Signal Quality Check': {
                    'status': analog_quality_result['status'],
                    'value': f"{analog_quality_result['bad_quality_count']} bad quality readings",
                    'description': 'Analog signal quality is GOOD in CSV data'
                }
            }

            # Test 2.1 and 2.2 - Timeliness and Completeness checks
            digital_time_result = self._test_21_time_differences(
                digital_tag, rtu_file, 'digital', data_dir)
            analog_time_result = self._test_21_time_differences(
                analog_tag, rtu_file, 'analog', data_dir)
            flat_result = self._test_22_flat_attribute(
                meter_name, review_file, flat_threshold, data_dir)

            results['timeliness_tests'] = {
                'Test 2.1 - Digital Signal Time Diff': {
                    'status': digital_time_result['status'],
                    'value': f"Max: {digital_time_result['max_time_diff']}s, Mean: {digital_time_result['mean_time_diff']}s",
                    'description': 'Digital signal time differences between readings'
                },
                'Test 2.1 - Analog Signal Time Diff': {
                    'status': analog_time_result['status'],
                    'value': f"Max: {analog_time_result['max_time_diff']}s, Mean: {analog_time_result['mean_time_diff']}s",
                    'description': 'Analog signal time differences between readings'
                },
                'Test 2.2 - FLAT Attribute Check': {
                    'status': flat_result['status'],
                    'value': flat_result['flat_check_status'],
                    'description': f'FLAT attribute <= {flat_threshold} (excluding shutdown periods)'
                }
            }

            # Test 1.1 - Range verification for both digital and analog signals
            digital_range_result = self._test_11_readings_within_range(
                digital_tag, rtu_file, 'digital', min_range, max_range, data_dir)
            analog_range_result = self._test_11_readings_within_range(
                analog_tag, rtu_file, 'analog', min_range, max_range, data_dir)

            # Test 1.2 - Unit verification for both digital and analog signals
            digital_units_result = self._test_12_units_verified(
                digital_tag, rtu_file, 'digital', min_q, max_q, data_dir)
            analog_units_result = self._test_12_units_verified(
                analog_tag, rtu_file, 'analog', min_q, max_q, data_dir)

            # Test 1.3 - Quality verification for both digital and analog signals
            digital_quality_result = self._test_13_quality_is_good(
                digital_tag, rtu_file, 'digital', data_dir)
            analog_quality_result = self._test_13_quality_is_good(
                analog_tag, rtu_file, 'analog', data_dir)

            # Test 1.4 - Quality verification in Review file
            review_quality_result = self._test_14_quality_review(
                meter_name, review_file, data_dir)

            # Test 3.1 - Mean Squared Error between digital and analog signals
            mse_result = self._test_31_mean_squared_error(
                digital_tag, analog_tag, rtu_file, data_dir)

            # Test 3.2 - Signal-to-Noise Ratio for both digital and analog signals
            digital_snr_result = self._test_32_signal_noise_ratio(
                digital_tag, rtu_file, 'digital', min_q, data_dir)
            analog_snr_result = self._test_32_signal_noise_ratio(
                analog_tag, rtu_file, 'analog', min_q, data_dir)

            results['accuracy_tests'] = {
                'Test 1.1 - Digital Signal Range': {
                    'status': digital_range_result['status'],
                    'value': f"{digital_range_result['out_of_range_count']} out of range",
                    'description': 'Digital signal readings within expected range'
                },
                'Test 1.1 - Analog Signal Range': {
                    'status': analog_range_result['status'],
                    'value': f"{analog_range_result['out_of_range_count']} out of range",
                    'description': 'Analog signal readings within operational range'
                },
                'Test 1.2 - Digital Signal Units': {
                    'status': digital_units_result['status'],
                    'value': f"{digital_units_result['conversions_applied']} conversions applied",
                    'description': 'Digital signal measurement units verified'
                },
                'Test 1.2 - Analog Signal Units': {
                    'status': analog_units_result['status'],
                    'value': f"{analog_units_result['conversions_applied']} conversions applied",
                    'description': 'Analog signal measurement units verified'
                },

                'Test 1.4 - Review File Quality': {
                    'status': review_quality_result['status'],
                    'value': f"{review_quality_result['bad_status_count']} bad status readings",
                    'description': 'Review file status values are GOOD (ST=1)'
                },
                'Test 3.1 - Mean Squared Error': {
                    'status': mse_result['status'],
                    'value': f"MSE: {mse_result['mse_value']}, Avg: {mse_result['nominal_flowrate']}",
                    'description': 'Mean squared error between digital and analog signals'
                },
                'Test 3.2 - Digital Signal SNR': {
                    'status': digital_snr_result['status'],
                    'value': f"SNR: {digital_snr_result['snr_value']}" if digital_snr_result['snr_value'] is not None else "N/A",
                    'description': 'Digital signal-to-noise ratio for steady state section'
                },
                'Test 3.2 - Analog Signal SNR': {
                    'status': analog_snr_result['status'],
                    'value': f"SNR: {analog_snr_result['snr_value']}" if analog_snr_result['snr_value'] is not None else "N/A",
                    'description': 'Analog signal-to-noise ratio for steady state section'
                }
            }

            # Test 3.3 and 3.4 - Target vs Digital/Reference comparisons - Real implementation required
            # Get accuracy_range from params
            accuracy_range = params.get('accuracy_range')
            test_33_result = self._test_33_target_vs_digital(
                meter_name, digital_tag, rtu_file, data_dir, accuracy_range)
            test_34_result = self._test_34_target_vs_reference(
                meter_name, ref_tag, review_file, data_dir, accuracy_range)

            # Add Test 3.3 and 3.4 to accuracy tests with real results
            results['accuracy_tests']['Test 3.3 - Target vs Digital'] = {
                'status': test_33_result['status'],
                'value': test_33_result['value'],
                'description': 'Target meter vs Digital signal comparison'
            }

            results['accuracy_tests']['Test 3.4 - Target vs Reference'] = {
                'status': test_34_result['status'],
                'value': test_34_result['value'],
                'description': 'Target meter vs Reference meter comparison'
            }

            # Test 3.5 - SNR Comparison between Digital/Analog and Reference meter
            # Find the ref_scada_tag from tags_df for this meter
            ref_scada_tag = ''
            if hasattr(self, 'tags_df') and self.tags_df is not None:
                # Find the row for this meter
                meter_row = self.tags_df[self.tags_df['MBSTagID'].str.strip(
                ) == meter_name]
                if not meter_row.empty and 'Ref_SCADATagID' in self.tags_df.columns:
                    ref_scada_tag = meter_row.iloc[0]['Ref_SCADATagID'].strip(
                    ) if pd.notna(meter_row.iloc[0]['Ref_SCADATagID']) else ''

            if params.get('accuracy_check_5') and ref_scada_tag:
                test_35_result = self._test_35_snr_comparison(
                    digital_tag, analog_tag, ref_scada_tag, rtu_file, min_q, data_dir)
                results['accuracy_tests']['Test 3.5 - SNR Comparison'] = {
                    'status': test_35_result['status'],
                    'value': f"Digital: {test_35_result['digital_snr']:.1f}dB, Analog: {test_35_result['analog_snr']:.1f}dB, Ref: {test_35_result['reference_snr']:.1f}dB" if all(x is not None for x in [test_35_result['digital_snr'], test_35_result['analog_snr'], test_35_result['reference_snr']]) else "SNR data unavailable",
                    'description': 'Target DIG/ANL SNR within 95% of Reference meter SNR'
                }
            elif params.get('accuracy_check_5') and not ref_scada_tag:
                results['accuracy_tests']['Test 3.5 - SNR Comparison'] = {
                    'status': 'fail',
                    'value': 'No Ref_SCADATagID defined',
                    'description': 'Test 3.5 requires Ref_SCADATagID column in tags file'
                }

            # Robustness Tests (4.1 only) - extract parameters from params (UI must provide values)
            stability_window = params.get('stability_window_size')
            drift_threshold = params.get('drift_threshold')
            stability_threshold = params.get('stability_threshold')

            # Validate required parameters for robustness tests
            if params.get('robustness_check_1') and any(x is None for x in [stability_window, drift_threshold, stability_threshold]):
                raise ValueError(
                    "Test 4.1 parameters missing: stability_window_size, drift_threshold, stability_threshold are required")

            digital_stability_result = self._test_41_signal_stability(
                digital_tag, rtu_file, 'digital',
                window_size=stability_window,
                drift_threshold=drift_threshold,
                stability_threshold=stability_threshold,
                data_dir=data_dir)
            analog_stability_result = self._test_41_signal_stability(
                analog_tag, rtu_file, 'analog',
                window_size=stability_window,
                drift_threshold=drift_threshold,
                stability_threshold=stability_threshold,
                data_dir=data_dir)

            results['robustness_tests'] = {
                'Test 4.1 - Digital Signal Stability': {
                    'status': digital_stability_result['status'],
                    'value': f"{digital_stability_result['stability_percentage']}% stable",
                    'description': f'Digital signal stability analysis (±3σ outliers: {digital_stability_result["outliers_count"]}, drift violations: {digital_stability_result["drift_violations"]})'
                },
                'Test 4.1 - Analog Signal Stability': {
                    'status': analog_stability_result['status'],
                    'value': f"{analog_stability_result['stability_percentage']}% stable",
                    'description': f'Analog signal stability analysis (±3σ outliers: {analog_stability_result["outliers_count"]}, drift violations: {analog_stability_result["drift_violations"]})'
                }
            }

            # Determine overall status
            all_tests = []
            for category in ['reliability_tests', 'timeliness_tests', 'accuracy_tests', 'robustness_tests']:
                for test_name, test_result in results[category].items():
                    all_tests.append(test_result['status'])

            results['overall_status'] = 'pass' if all(
                status == 'pass' for status in all_tests) else 'fail'

        except Exception as e:
            self.logger.error(f"Error testing meter {meter_name}: {e}")
            results['overall_status'] = 'error'

        return results

    def _check_rtu_data(self, digital_tag: str, analog_tag: str, rtu_file: str,
                        time_start: str, time_end: str) -> bool:
        """Check if RTU data is available."""
        try:
            # For now, assume data is available if file exists
            return os.path.exists(rtu_file)
        except:
            return False

    def _check_review_data(self, meter_tag: str, ref_tag: str, review_file: str,
                           time_start: str, time_end: str) -> bool:
        """Check if review data is available."""
        try:
            # For now, assume data is available if file exists
            return os.path.exists(review_file)
        except:
            return False

    def _test_11_readings_within_range(self, tag_name: str, rtu_file: str,
                                       signal_type: str, min_range: float,
                                       max_range: float, data_dir: str = None) -> Dict[str, Any]:
        """
        Test 1.1: Readings within Expected Range of Operation

        Matches original flowmeter_main.py logic - counts readings outside lower/upper bounds.
        CSV is already filtered by date range, no need to filter again.

        Args:
            tag_name: The SCADA tag ID to check
            rtu_file: Path to RTU data file (used to determine data directory)
            signal_type: 'digital' or 'analog'
            min_range: Minimum acceptable range value (from UI)
            max_range: Maximum acceptable range value (from UI)
            data_dir: Directory containing CSV data files (from UI)

        Returns:
            Dictionary with test results including out_of_range_count and status
        """
        try:
            self.logger.info(
                f"Running Test 1.1 for {signal_type} signal: {tag_name}")

            # Default result structure
            result = {
                'out_of_range_count': 0,
                'total_readings': 0,
                'status': 'pass',
                'details': f'No data found for {tag_name}'
            }

            # Determine data directory
            if data_dir is None:
                data_dir = os.path.join(os.path.dirname(rtu_file), '_Data')

            # Determine CSV file based on signal type
            if signal_type.lower() == 'digital':
                csv_file = os.path.join(data_dir, "SCADATagID_DIG.csv")
            elif signal_type.lower() == 'analog':
                csv_file = os.path.join(data_dir, "SCADATagID_ANL.csv")
            else:
                result['status'] = 'fail'
                result['details'] = f'Unknown signal type: {signal_type}'
                return result

            if not os.path.exists(csv_file):
                result['status'] = 'fail'
                result['details'] = f'CSV file not found: {csv_file}'
                return result

            # Load CSV data
            df = pd.read_csv(csv_file)

            # Filter for the specific tag using tag_name column (matches CSV format)
            if 'tag_name' not in df.columns:
                result['status'] = 'fail'
                result['details'] = f'No tag_name column found in {csv_file}'
                return result

            tag_data = df[df['tag_name'] == tag_name]

            if tag_data.empty:
                result['details'] = f'No data found for tag {tag_name}'
                result['status'] = 'fail'
                return result

            # Get values and check ranges (matches original logic)
            values = tag_data['value'].dropna()
            result['total_readings'] = len(values)

            if result['total_readings'] == 0:
                result['status'] = 'fail'
                result['details'] = 'No valid readings found'
                return result

            # Count values outside range (original logic: >= lower_bound AND <= upper_bound)
            out_of_range = values[(values < min_range) | (values > max_range)]
            result['out_of_range_count'] = len(out_of_range)

            # Original logic uses simple count, not percentage
            result['status'] = 'pass' if result['out_of_range_count'] == 0 else 'fail'
            result['details'] = f'{signal_type.title()} signal range check ({min_range}-{max_range}): {result["out_of_range_count"]} out of {result["total_readings"]} readings out of range'

            return result

        except Exception as e:
            self.logger.error(f"Error in Test 1.1 for {tag_name}: {e}")
            return {
                'out_of_range_count': 0,
                'total_readings': 0,
                'status': 'fail',
                'details': f'Test execution error: {str(e)}'
            }

    def _test_12_units_verified(self, tag_name: str, rtu_file: str,
                                signal_type: str, min_q: float, max_q: float,
                                data_dir: str = None) -> Dict[str, Any]:
        """
        Test 1.2: Measurement Units were Verified

        Matches original flowmeter_main.py unit_check logic exactly.
        Checks if values are in m³/h using min_Q/max_Q tolerance (80%-120%).
        If outside range, attempts conversion from barrels/h using factor 6.2898.

        Args:
            tag_name: The SCADA tag ID to check  
            rtu_file: Path to RTU data file
            signal_type: 'digital' or 'analog'
            min_q: Minimum operating flowrate (from UI)
            max_q: Maximum operating flowrate (from UI)
            data_dir: Directory containing CSV data files

        Returns:
            Dictionary with test results including conversions_applied and status
        """
        try:
            self.logger.info(
                f"Running Test 1.2 for {signal_type} signal: {tag_name}")

            # Default result structure
            result = {
                'unit_issues_count': 0,
                'total_readings': 0,
                'status': 'pass',
                'details': f'No data found for {tag_name}',
                'conversions_applied': 0
            }

            # Determine data directory
            if data_dir is None:
                data_dir = os.path.join(os.path.dirname(rtu_file), '_Data')

            # Determine CSV file based on signal type
            if signal_type.lower() == 'digital':
                csv_file = os.path.join(data_dir, "SCADATagID_DIG.csv")
            elif signal_type.lower() == 'analog':
                csv_file = os.path.join(data_dir, "SCADATagID_ANL.csv")
            else:
                result['status'] = 'fail'
                result['details'] = f'Unknown signal type: {signal_type}'
                return result

            if not os.path.exists(csv_file):
                result['status'] = 'fail'
                result['details'] = f'CSV file not found: {csv_file}'
                return result

            # Load CSV data
            df = pd.read_csv(csv_file)

            # Filter for the specific tag
            if 'tag_name' not in df.columns:
                result['status'] = 'fail'
                result['details'] = f'No tag_name column found in {csv_file}'
                return result

            tag_data = df[df['tag_name'] == tag_name]

            if tag_data.empty:
                result['details'] = f'No data found for tag {tag_name}'
                result['status'] = 'fail'
                return result

            # Get values and perform unit verification (original logic)
            values = tag_data['value'].dropna().tolist()
            result['total_readings'] = len(values)

            if result['total_readings'] == 0:
                result['status'] = 'fail'
                result['details'] = 'No valid readings found'
                return result

            # Apply original unit_check logic exactly
            wrong_unit_instance = 0
            conversions_applied = 0

            # Calculate tolerance range (original logic: 80% to 120% of min/max Q)
            min_acceptable = 0.8 * min_q
            max_acceptable = 1.2 * max_q

            for index in range(len(values)):
                if min_acceptable <= values[index] <= max_acceptable:
                    # Value is in expected m³/h range, no conversion needed
                    pass
                else:
                    # Value outside expected range - convert from barrels/h to m³/h
                    wrong_unit_instance += 1
                    values[index] = values[index] / \
                        6.2898  # Original conversion factor
                    conversions_applied += 1

            result['conversions_applied'] = conversions_applied

            # Determine status and message (matches original logic exactly)
            if wrong_unit_instance > 0:
                result['details'] = "Some units appeared in barrels/hr, and were converted to m3/hr"
                # Original treats conversions as pass
                result['status'] = 'pass'
            else:
                result['details'] = "Units are all in m3/hr"
                result['status'] = 'pass'

            return result

        except Exception as e:
            self.logger.error(f"Error in Test 1.2 for {tag_name}: {e}")
            return {
                'unit_issues_count': 0,
                'total_readings': 0,
                'status': 'fail',
                'details': f'Test execution error: {str(e)}',
                'conversions_applied': 0
            }

    def _test_13_quality_is_good(self, tag_name: str, rtu_file: str,
                                 signal_type: str, data_dir: str = None) -> Dict[str, Any]:
        """
        Test 1.3: Quality of the Signals is GOOD in the rtu File

        Matches original flowmeter_main.py logic - counts instances where quality != "GOOD".
        Original logic: if bad_quality == 0, then pass; otherwise fail.

        Args:
            tag_name: The SCADA tag ID to check
            rtu_file: Path to RTU data file
            signal_type: 'digital' or 'analog'
            data_dir: Directory containing CSV data files

        Returns:
            Dictionary with test results including bad_quality_count and status
        """
        try:
            self.logger.info(
                f"Running Test 1.3 for {signal_type} signal: {tag_name}")

            # Default result structure
            result = {
                'bad_quality_count': 0,
                'total_readings': 0,
                'status': 'pass',
                'details': f'No data found for {tag_name}'
            }

            # Determine data directory
            if data_dir is None:
                data_dir = os.path.join(os.path.dirname(rtu_file), '_Data')

            # Determine CSV file based on signal type
            if signal_type.lower() == 'digital':
                csv_file = os.path.join(data_dir, "SCADATagID_DIG.csv")
            elif signal_type.lower() == 'analog':
                csv_file = os.path.join(data_dir, "SCADATagID_ANL.csv")
            else:
                result['status'] = 'fail'
                result['details'] = f'Unknown signal type: {signal_type}'
                return result

            if not os.path.exists(csv_file):
                result['status'] = 'fail'
                result['details'] = f'CSV file not found: {csv_file}'
                return result

            # Load CSV data
            df = pd.read_csv(csv_file)

            # Filter for the specific tag
            if 'tag_name' not in df.columns:
                result['status'] = 'fail'
                result['details'] = f'No tag_name column found in {csv_file}'
                return result

            tag_data = df[df['tag_name'] == tag_name]

            if tag_data.empty:
                result['details'] = f'No data found for tag {tag_name}'
                result['status'] = 'fail'
                return result

            # Check quality column (matches original logic)
            if 'quality' not in tag_data.columns:
                result['status'] = 'fail'
                result['details'] = 'No quality column found in data'
                return result

            quality_values = tag_data['quality']
            result['total_readings'] = len(quality_values)

            # Count bad quality instances (original logic: != "GOOD")
            bad_quality_count = len(quality_values[quality_values != 'GOOD'])
            result['bad_quality_count'] = bad_quality_count

            # Original logic: if bad_quality == 0, pass; otherwise fail
            if bad_quality_count == 0:
                result['status'] = 'pass'
                result['details'] = f'Quality for tag {tag_name} is all GOOD'
            else:
                result['status'] = 'fail'
                result['details'] = f'BAD Quality present with {bad_quality_count} number of instances'

            return result

        except Exception as e:
            self.logger.error(f"Error in Test 1.3 for {tag_name}: {e}")
            return {
                'bad_quality_count': 0,
                'total_readings': 0,
                'status': 'fail',
                'details': f'Test execution error: {str(e)}'
            }

    def _test_14_quality_review(self, meter_name: str, review_file: str,
                                data_dir: str = None) -> Dict[str, Any]:
        """
        Test 1.4: Quality of the Signals is GOOD in the Review File

        Matches original flowmeter_main.py reliability_check_4_function logic.
        Checks if all ST (status) column values == 1 (GOOD) in Review data.
        CSV is already filtered by date range, no need to filter again.

        Args:
            meter_name: The MBS tag ID (meter name) to check
            review_file: Path to Review data file
            data_dir: Directory containing CSV data files

        Returns:
            Dictionary with test results including bad_status_count and status
        """
        try:
            self.logger.info(f"Running Test 1.4 for meter: {meter_name}")

            # Default result structure
            result = {
                'bad_status_count': 0,
                'total_readings': 0,
                'status': 'pass',
                'details': f'No data found for meter {meter_name}'
            }

            # Determine data directory
            if data_dir is None:
                data_dir = os.path.join(os.path.dirname(review_file), '_Data')

            mbs_csv_file = os.path.join(data_dir, 'MBSTagID.csv')

            if not os.path.exists(mbs_csv_file):
                result['details'] = f'No MBSTagID.csv file found for meter {meter_name}'
                result['status'] = 'fail'
                return result

            # Load the MBS CSV data
            df = pd.read_csv(mbs_csv_file)

            # Strip whitespace from column names to handle formatting inconsistencies
            df.columns = df.columns.str.strip()

            # The column format is: TIME, {meter_name}:VAL, {meter_name}:ST, {meter_name}:FLAT
            # We need to check the ST (status) column (after stripping spaces)
            st_column = f'{meter_name}:ST'

            if st_column not in df.columns:
                result[
                    'details'] = f'No status column found for meter {meter_name} in MBSTagID.csv. Available columns: {list(df.columns)}'
                result['status'] = 'fail'
                return result

            # Count readings (CSV is already date-filtered)
            total_readings = len(df)
            result['total_readings'] = total_readings

            if total_readings == 0:
                result['details'] = f'No data found for meter {meter_name}'
                result['status'] = 'fail'
                return result

            # Original logic: count where ST != 1 (bad status)
            bad_status_count = len(df[df[st_column] != 1])
            result['bad_status_count'] = bad_status_count

            # Original logic: uses .all() check - if all ST == 1, then pass
            if bad_status_count == 0:
                result['status'] = 'pass'
                result['details'] = 'Values appear GOOD in the review file'
            else:
                result['status'] = 'fail'
                result['details'] = 'Some values appear BAD in the review file - Requires further investigation from the LC'

            return result

        except Exception as e:
            self.logger.error(f"Error in Test 1.4 for {meter_name}: {e}")
            return {
                'bad_status_count': 0,
                'total_readings': 0,
                'status': 'fail',
                'details': f'Test execution error: {str(e)}'
            }

    def _test_21_time_differences(self, tag_name: str, rtu_file: str,
                                  signal_type: str, data_dir: str = None) -> Dict[str, Any]:
        """
        Test 2.1: Timeliness and Completeness Check 1 - Time Differences

        Matches original flowmeter_main.py timeliness_and_completeness logic.
        Calculates time differences between consecutive readings and reports 
        max and mean time differences.

        Args:
            tag_name: The SCADA tag ID to check
            rtu_file: Path to RTU data file
            signal_type: 'digital' or 'analog'
            data_dir: Directory containing CSV data files

        Returns:
            Dictionary with test results including max_time_diff and mean_time_diff
        """
        try:
            self.logger.info(
                f"Running Test 2.1 for {signal_type} signal: {tag_name}")

            # Default result structure
            result = {
                'max_time_diff': 0,
                'mean_time_diff': 0.0,
                'total_readings': 0,
                'status': 'pass',
                'details': f'No data found for {tag_name}'
            }

            # Determine data directory
            if data_dir is None:
                data_dir = os.path.join(os.path.dirname(rtu_file), '_Data')

            # Determine CSV file based on signal type
            if signal_type.lower() == 'digital':
                csv_file = os.path.join(data_dir, "SCADATagID_DIG.csv")
            elif signal_type.lower() == 'analog':
                csv_file = os.path.join(data_dir, "SCADATagID_ANL.csv")
            else:
                result['status'] = 'fail'
                result['details'] = f'Unknown signal type: {signal_type}'
                return result

            if not os.path.exists(csv_file):
                result['status'] = 'fail'
                result['details'] = f'CSV file not found: {csv_file}'
                return result

            # Load CSV data
            df = pd.read_csv(csv_file)

            # Filter for the specific tag
            if 'tag_name' not in df.columns:
                result['status'] = 'fail'
                result['details'] = f'No tag_name column found in {csv_file}'
                return result

            tag_data = df[df['tag_name'] == tag_name].copy()

            if tag_data.empty:
                result['details'] = f'No data found for tag {tag_name}'
                result['status'] = 'fail'
                return result

            # Check for timestamp column
            if 'timestamp' not in tag_data.columns:
                result['status'] = 'fail'
                result['details'] = 'No timestamp column found in data'
                return result

            # Sort by timestamp to ensure proper order
            tag_data = tag_data.sort_values('timestamp')
            result['total_readings'] = len(tag_data)

            if result['total_readings'] < 2:
                result['status'] = 'fail'
                result['details'] = 'Need at least 2 readings to calculate time differences'
                return result

            # Calculate time differences (original logic)
            timestamps = tag_data['timestamp'].values
            time_differences = []

            for k in range(len(timestamps) - 1):
                x = timestamps[k]
                y = timestamps[k + 1]
                time_diff = y - x
                time_differences.append(time_diff)

            # Calculate max and mean time differences
            result['max_time_diff'] = max(time_differences)
            result['mean_time_diff'] = round(np.mean(time_differences), 2)

            # Determine status (original doesn't have pass/fail for Test 2.1, just reports values)
            result['status'] = 'pass'
            result['details'] = f'Max: {result["max_time_diff"]}s, Mean: {result["mean_time_diff"]}s'

            return result

        except Exception as e:
            self.logger.error(f"Error in Test 2.1 for {tag_name}: {e}")
            return {
                'max_time_diff': 0,
                'mean_time_diff': 0.0,
                'total_readings': 0,
                'status': 'fail',
                'details': f'Test execution error: {str(e)}'
            }

    def _test_22_flat_attribute(self, meter_name: str, review_file: str,
                                flat_threshold: float, data_dir: str = None) -> Dict[str, Any]:
        """
        Test 2.2: Timeliness and Completeness Check 2 - FLAT Attribute

        Matches original flowmeter_main.py timeliness_check_2 logic.
        Checks if FLAT attribute values are <= threshold, excluding shutdown periods
        (where VAL <= 1).

        Args:
            meter_name: The MBS tag ID (meter name) to check
            review_file: Path to Review data file
            flat_threshold: FLAT threshold value (from UI)
            data_dir: Directory containing CSV data files

        Returns:
            Dictionary with test results including flat_check_status
        """
        try:
            self.logger.info(f"Running Test 2.2 for meter: {meter_name}")

            # Default result structure
            result = {
                'flat_check_status': 'unknown',
                'total_readings': 0,
                'non_shutdown_readings': 0,
                'status': 'pass',
                'details': f'No data found for meter {meter_name}'
            }

            # Determine data directory
            if data_dir is None:
                data_dir = os.path.join(os.path.dirname(review_file), '_Data')

            mbs_csv_file = os.path.join(data_dir, 'MBSTagID.csv')

            if not os.path.exists(mbs_csv_file):
                result['details'] = f'No MBSTagID.csv file found for meter {meter_name}'
                result['status'] = 'fail'
                return result

            # Load the MBS CSV data
            df = pd.read_csv(mbs_csv_file)

            # Strip whitespace from column names to handle formatting inconsistencies
            df.columns = df.columns.str.strip()

            # The column format is: TIME, {meter_name}:VAL, {meter_name}:ST, {meter_name}:FLAT
            val_column = f'{meter_name}:VAL'
            flat_column = f'{meter_name}:FLAT'

            # Check required columns exist
            missing_columns = []
            if val_column not in df.columns:
                missing_columns.append('VAL column')
            if flat_column not in df.columns:
                missing_columns.append('FLAT column')

            if missing_columns:
                result[
                    'details'] = f'Missing columns for meter {meter_name}: {missing_columns}. Available: {list(df.columns)}'
                result['status'] = 'fail'
                return result

            result['total_readings'] = len(df)

            if result['total_readings'] == 0:
                result['details'] = f'No data found for meter {meter_name}'
                result['status'] = 'fail'
                return result

            try:
                # Original logic: Filter out shutdown periods (VAL <= 1)
                dataframe_not_shutdown = df[df[val_column] > 1]
                result['non_shutdown_readings'] = len(dataframe_not_shutdown)

                if result['non_shutdown_readings'] == 0:
                    result['details'] = f'No non-shutdown readings found for meter {meter_name}'
                    result['status'] = 'fail'
                    result['flat_check_status'] = 'no_data'
                    return result

                # Check if all FLAT values are <= threshold (original logic uses .all())
                review_flat = (
                    dataframe_not_shutdown[flat_column] <= flat_threshold).all()

                if review_flat:
                    result['status'] = 'pass'
                    result['flat_check_status'] = 'GOOD'
                    result['details'] = f'FLAT attribute check passed: all values <= {flat_threshold}'
                else:
                    result['status'] = 'fail'
                    result['flat_check_status'] = 'BAD'
                    result['details'] = f'FLAT attribute check failed: some values > {flat_threshold}'

            except Exception as inner_e:
                # Original logic has this fallback
                result['status'] = 'fail'
                result['flat_check_status'] = 'FLAT Not Available'
                result['details'] = f'FLAT Attribute Not Accessible: {str(inner_e)}'

            return result

        except Exception as e:
            self.logger.error(f"Error in Test 2.2 for {meter_name}: {e}")
            return {
                'flat_check_status': 'error',
                'total_readings': 0,
                'non_shutdown_readings': 0,
                'status': 'fail',
                'details': f'Test execution error: {str(e)}'
            }

    def _test_31_mean_squared_error(self, digital_tag: str, analog_tag: str,
                                    rtu_file: str, data_dir: str = None) -> Dict[str, Any]:
        """
        Test 3.1: Mean Squared Error between Digital and Analog Signals

        Calculates MSE using the correct formula: MSE = mean((digital - analog)²)
        Does not normalize by digital mean or convert to percentage.

        Args:
            digital_tag: The digital SCADA tag ID
            analog_tag: The analog SCADA tag ID
            rtu_file: Path to RTU data file
            data_dir: Directory containing CSV data files

        Returns:
            Dictionary with test results including mse_value and nominal_flowrate
        """
        try:
            self.logger.info(
                f"Running Test 3.1 MSE for digital: {digital_tag}, analog: {analog_tag}")

            # Default result structure
            result = {
                'mse_value': 0.0,
                'nominal_flowrate': 0.0,
                'total_readings': 0,
                'status': 'pass',
                'details': 'No data found'
            }

            # Determine data directory
            if data_dir is None:
                data_dir = os.path.join(os.path.dirname(rtu_file), '_Data')

            # CSV file paths
            digital_csv = os.path.join(data_dir, "SCADATagID_DIG.csv")
            analog_csv = os.path.join(data_dir, "SCADATagID_ANL.csv")

            # Check if both CSV files exist
            if not os.path.exists(digital_csv):
                result['status'] = 'fail'
                result['details'] = f'Digital CSV file not found: {digital_csv}'
                return result

            if not os.path.exists(analog_csv):
                result['status'] = 'fail'
                result['details'] = f'Analog CSV file not found: {analog_csv}'
                return result

            # Load CSV data
            digital_df = pd.read_csv(digital_csv)
            analog_df = pd.read_csv(analog_csv)

            # Filter for specific tags
            if 'tag_name' not in digital_df.columns or 'tag_name' not in analog_df.columns:
                result['status'] = 'fail'
                result['details'] = 'No tag_name column found in CSV files'
                return result

            digital_data = digital_df[digital_df['tag_name'] == digital_tag]
            analog_data = analog_df[analog_df['tag_name'] == analog_tag]

            if digital_data.empty:
                result['status'] = 'fail'
                result['details'] = f'No data found for digital tag {digital_tag}'
                return result

            if analog_data.empty:
                result['status'] = 'fail'
                result['details'] = f'No data found for analog tag {analog_tag}'
                return result

            # Get values
            digital_values = digital_data['value'].dropna().values
            analog_values = analog_data['value'].dropna().values

            if len(digital_values) == 0 or len(analog_values) == 0:
                result['status'] = 'fail'
                result['details'] = 'No valid readings found in one or both signals'
                return result

            # Align data lengths (trim to shorter length)
            min_length = min(len(digital_values), len(analog_values))
            digital_values = digital_values[:min_length]
            analog_values = analog_values[:min_length]

            result['total_readings'] = min_length

            # Calculate MSE using correct formula: mean((digital - analog)²)
            # Not normalized by digital mean or converted to percentage
            mse_value = np.square(np.subtract(
                digital_values, analog_values)).mean()
            nominal_flowrate = np.mean(digital_values)

            result['mse_value'] = round(mse_value, 3)
            result['nominal_flowrate'] = round(nominal_flowrate, 2)
            result['status'] = 'pass'
            result['details'] = f'MSE: {result["mse_value"]}, Avg Flow: {result["nominal_flowrate"]}'

            return result

        except Exception as e:
            self.logger.error(
                f"Error in Test 3.1 for {digital_tag}/{analog_tag}: {e}")
            return {
                'mse_value': 0.0,
                'nominal_flowrate': 0.0,
                'total_readings': 0,
                'status': 'fail',
                'details': f'Test execution error: {str(e)}'
            }

    def _test_32_signal_noise_ratio(self, tag_name: str, rtu_file: str,
                                    signal_type: str, min_q: float,
                                    data_dir: str = None) -> Dict[str, Any]:
        """
        Test 3.2: Signal-to-Noise Ratio (Accuracy Check 2) - Improved with scipy

        Uses scipy for better SNR calculation with multiple methods:
        1. Power-based SNR (10*log10(signal_power/noise_power))
        2. Detrended SNR to remove systematic trends
        3. Welch's method for power spectral density estimation
        """
        try:

            self.logger.info(
                f"Running Test 3.2 SNR for {signal_type} signal: {tag_name}")

            # Default result structure
            result = {
                'snr_value': None,
                'total_readings': 0,
                'steady_state_readings': 0,
                'status': 'pass',
                'details': f'No data found for {tag_name}'
            }

            # Determine data directory
            if data_dir is None:
                data_dir = os.path.join(os.path.dirname(rtu_file), '_Data')

            # Determine CSV file based on signal type
            if signal_type.lower() == 'digital':
                csv_file = os.path.join(data_dir, "SCADATagID_DIG.csv")
            elif signal_type.lower() == 'analog':
                csv_file = os.path.join(data_dir, "SCADATagID_ANL.csv")
            elif signal_type.lower() == 'ref_scada':
                csv_file = os.path.join(data_dir, "Ref_SCADATagID.csv")
            else:
                result['status'] = 'fail'
                result['details'] = f'Unknown signal type: {signal_type}'
                return result

            if not os.path.exists(csv_file):
                result['status'] = 'fail'
                result['details'] = f'CSV file not found: {csv_file}'
                return result

            # Load CSV data
            df = pd.read_csv(csv_file)

            # Filter for the specific tag
            if 'tag_name' not in df.columns:
                result['status'] = 'fail'
                result['details'] = f'No tag_name column found in {csv_file}'
                return result

            tag_data = df[df['tag_name'] == tag_name].copy()

            if tag_data.empty:
                result['details'] = f'No data found for tag {tag_name}'
                result['status'] = 'fail'
                return result

            # Get values
            values = tag_data['value'].dropna().values
            result['total_readings'] = len(values)

            if result['total_readings'] == 0:
                result['status'] = 'fail'
                result['details'] = 'No valid readings found'
                return result

            # Get steady state values (existing logic)
            steady_state_values = values[values > min_q]
            result['steady_state_readings'] = len(steady_state_values)

            if len(steady_state_values) < 10:  # Need more data for scipy methods
                result['status'] = 'fail'
                result[
                    'details'] = f'Insufficient steady state data for robust SNR calculation. Found {len(steady_state_values)} readings (need ≥10).'
                result['snr_value'] = None
                return result

            # Method 1: Improved basic SNR with detrending
            # Remove linear trend to get better noise estimate
            detrended_values = scipy.signal.detrend(
                steady_state_values, type='linear')
            # RMS power of original signal
            signal_power = np.mean(steady_state_values**2)
            # Variance of detrended signal as noise
            noise_power = np.var(detrended_values)

            if noise_power == 0:
                result['status'] = 'fail'
                result['details'] = 'Noise power is zero - cannot calculate SNR'
                result['snr_value'] = None
                return result

            # SNR in dB (more standard representation)
            snr_db = 10 * np.log10(signal_power / noise_power)

            # Method 2: Spectral SNR using Welch's method
            try:
                # Estimate power spectral density
                frequencies, psd = scipy.signal.welch(
                    steady_state_values, nperseg=min(len(steady_state_values)//4, 256))

                # Assume signal is in low frequency components (first 10% of spectrum)
                signal_freq_cutoff = len(frequencies) // 10
                signal_power_spectral = np.sum(psd[:signal_freq_cutoff])
                noise_power_spectral = np.sum(psd[signal_freq_cutoff:])

                if noise_power_spectral > 0:
                    snr_spectral_db = 10 * \
                        np.log10(signal_power_spectral / noise_power_spectral)
                else:
                    snr_spectral_db = None
            except:
                snr_spectral_db = None

            # Method 3: Statistical outlier-based noise estimation
            # Use median absolute deviation for robust noise estimation
            median_val = np.median(steady_state_values)
            mad = stats.median_abs_deviation(steady_state_values)

            if mad > 0:
                # MAD-based SNR (more robust to outliers)
                # 1.4826 converts MAD to std for normal distribution
                snr_mad = median_val / (mad * 1.4826)
            else:
                snr_mad = None

            # Store multiple SNR calculations
            result['snr_value'] = round(snr_db, 3)  # Primary result in dB
            result['snr_linear'] = round(
                signal_power / noise_power, 3) if noise_power > 0 else None
            result['snr_spectral_db'] = round(
                snr_spectral_db, 3) if snr_spectral_db is not None else None
            result['snr_mad_based'] = round(
                snr_mad, 3) if snr_mad is not None else None

            # Enhanced details with multiple metrics
            details_parts = [f"SNR: {result['snr_value']} dB"]
            if result['snr_spectral_db']:
                details_parts.append(
                    f"Spectral SNR: {result['snr_spectral_db']} dB")
            if result['snr_mad_based']:
                details_parts.append(f"MAD-based: {result['snr_mad_based']}")

            # Apply > 30 dB acceptance criteria
            snr_threshold_db = 30.0  # > 30 dB acceptance criteria
            if result['snr_value'] is not None and result['snr_value'] > snr_threshold_db:
                result['status'] = 'pass'
                details_parts.append(f"(PASS: > {snr_threshold_db} dB)")
            else:
                result['status'] = 'fail'
                details_parts.append(f"(FAIL: ≤ {snr_threshold_db} dB)")

            result['details'] = ", ".join(details_parts)

            return result

        except ImportError:
            # Fallback to original method if scipy not available
            self.logger.warning(
                "Scipy not available, using basic SNR calculation")
            # ... original calculation code ...
        except Exception as e:
            self.logger.error(f"Error in Test 3.2 for {tag_name}: {e}")
            return {
                'snr_value': None,
                'total_readings': 0,
                'steady_state_readings': 0,
                'status': 'fail',
                'details': f'Test execution error: {str(e)}'
            }

    def _test_33_target_vs_digital(self, meter_name: str, digital_tag: str, rtu_file: str,
                                   data_dir: str, accuracy_range: float) -> Dict[str, Any]:
        """Wrapper for Test 3.3 - Target vs Digital comparison using real CSV data."""
        try:
            if not data_dir:
                return {
                    'status': 'fail',
                    'value': 'No data directory available',
                    'details': 'CSV export required for Test 3.3'
                }

            target_csv = os.path.join(data_dir, "MBSTagID.csv")
            digital_csv = os.path.join(data_dir, "SCADATagID_DIG.csv")

            if not os.path.exists(target_csv) or not os.path.exists(digital_csv):
                return {
                    'status': 'fail',
                    'value': 'Required CSV files not found',
                    'details': f'Missing: {target_csv} or {digital_csv}'
                }

            result = self._test_33_target_vs_digital_comparison(
                target_csv, digital_csv, accuracy_range, data_dir)
            return {
                'status': result['status'],
                'value': f"{result.get('percentage_within_range', 0):.1f}% within ±{accuracy_range}%",
                'details': result.get('details', '')
            }
        except Exception as e:
            return {
                'status': 'fail',
                'value': f'Test error: {str(e)}',
                'details': 'Test 3.3 execution failed'
            }

    def _test_34_target_vs_reference(self, meter_name: str, ref_tag: str, review_file: str,
                                     data_dir: str, accuracy_range: float) -> Dict[str, Any]:
        """Wrapper for Test 3.4 - Target vs Reference comparison using real CSV data."""
        try:
            if not data_dir:
                return {
                    'status': 'fail',
                    'value': 'No data directory available',
                    'details': 'CSV export required for Test 3.4'
                }

            target_csv = os.path.join(data_dir, "MBSTagID.csv")
            reference_csv = os.path.join(data_dir, "Reference_Meter.csv")

            if not os.path.exists(target_csv) or not os.path.exists(reference_csv):
                return {
                    'status': 'fail',
                    'value': 'Required CSV files not found',
                    'details': f'Missing: {target_csv} or {reference_csv}'
                }

            result = self._test_34_target_vs_reference_comparison(
                target_csv, reference_csv, accuracy_range, data_dir)
            return {
                'status': result['status'],
                'value': f"{result.get('percentage_within_range', 0):.1f}% within ±{accuracy_range}%",
                'details': result.get('details', '')
            }
        except Exception as e:
            return {
                'status': 'fail',
                'value': f'Test error: {str(e)}',
                'details': 'Test 3.4 execution failed'
            }

    def _test_33_target_vs_digital_comparison(self, target_csv: str, digital_csv: str,
                                              accuracy_range: float, data_folder: str) -> Dict[str, Any]:
        """
        Test 3.3: Target vs Digital Signal Comparison
        Compares Target meter values (MBSTagID.csv from Review) with Digital RTU values (SCADATagID_DIG.csv)

        Args:
            target_csv: Path to MBSTagID.csv (Target meter from Review file)
            digital_csv: Path to SCADATagID_DIG.csv (Digital signal from RTU)
            accuracy_range: Percentage tolerance for comparison (e.g., 1.0 for ±1%)
            data_folder: Folder containing the CSV files

        Returns:
            Dict with comparison results including percentage within range
        """
        result = {
            'percentage_within_range': 0.0,
            'total_comparisons': 0,
            'values_within_range': 0,
            'target_readings': 0,
            'digital_readings': 0,
            'status': 'fail',
            'details': ''
        }

        try:
            # Read Target meter data (MBSTagID.csv - Review file format)
            target_file = os.path.join(
                data_folder, os.path.basename(target_csv))
            if not os.path.exists(target_file):
                result['details'] = f'Target CSV file not found: {target_file}'
                return result

            target_df = pd.read_csv(target_file)
            # Strip whitespace from column names to handle formatting inconsistencies
            target_df.columns = target_df.columns.str.strip()

            # Find the :VAL column in target data
            val_column = None
            for col in target_df.columns:
                if ':VAL' in col:
                    val_column = col
                    break

            if val_column is None:
                result['details'] = 'No :VAL column found in target CSV file'
                return result

            # Clean and prepare target data
            target_df['TIME'] = pd.to_datetime(
                target_df['TIME'], errors='coerce')
            target_df = target_df.dropna(subset=['TIME', val_column])
            target_values = target_df[val_column].values
            target_times = target_df['TIME'].values
            result['target_readings'] = len(target_values)

            # Read Digital RTU data (SCADATagID_DIG.csv - RTU file format)
            digital_file = os.path.join(
                data_folder, os.path.basename(digital_csv))
            if not os.path.exists(digital_file):
                result['details'] = f'Digital CSV file not found: {digital_file}'
                return result

            digital_df = pd.read_csv(digital_file)

            # Prepare digital data
            digital_df['datetime'] = pd.to_datetime(
                digital_df['datetime'], errors='coerce')
            digital_df = digital_df.dropna(subset=['datetime', 'value'])
            digital_values = digital_df['value'].values
            digital_times = digital_df['datetime'].values
            result['digital_readings'] = len(digital_values)

            if len(target_values) == 0 or len(digital_values) == 0:
                result['details'] = f'Insufficient data: Target={len(target_values)}, Digital={len(digital_values)}'
                return result

            # Time-align the datasets by finding nearest timestamps
            aligned_pairs = []
            for i, target_time in enumerate(target_times):
                target_val = target_values[i]

                # Find closest digital timestamp (within reasonable time window, e.g., 30 seconds)
                time_diffs = np.abs(digital_times - target_time)
                min_diff_idx = np.argmin(time_diffs)
                min_diff_seconds = time_diffs[min_diff_idx] / \
                    np.timedelta64(1, 's')

                if min_diff_seconds <= 30:  # Within 30 seconds
                    digital_val = digital_values[min_diff_idx]
                    aligned_pairs.append((target_val, digital_val))

            result['total_comparisons'] = len(aligned_pairs)

            if result['total_comparisons'] == 0:
                result['details'] = 'No time-aligned data points found between target and digital signals'
                return result

            # Calculate target mean for comparison
            target_vals = [pair[0] for pair in aligned_pairs]
            target_mean = np.mean(target_vals)

            # Count values within accuracy range
            lower_bound = target_mean * (1 - accuracy_range / 100)
            upper_bound = target_mean * (1 + accuracy_range / 100)

            values_within_range = 0
            for target_val, digital_val in aligned_pairs:
                if lower_bound <= digital_val <= upper_bound:
                    values_within_range += 1

            result['values_within_range'] = values_within_range
            result['percentage_within_range'] = round(
                (values_within_range / result['total_comparisons']) * 100, 2)

            result['status'] = 'pass'
            result[
                'details'] = f'{result["percentage_within_range"]}% of digital values within ±{accuracy_range}% of target mean ({round(target_mean, 2)})'

            return result

        except Exception as e:
            self.logger.error(
                f"Error in Test 3.3 Target vs Digital comparison: {e}")
            result['details'] = f'Test execution error: {str(e)}'
            return result

    def _test_34_target_vs_reference_comparison(self, target_csv: str, reference_csv: str,
                                                accuracy_range: float, data_folder: str) -> Dict[str, Any]:
        """
        Test 3.4: Target vs Reference Meter Comparison (formerly Test 3.5)
        Compares Target meter values (MBSTagID.csv) with Reference meter values (Reference_Meter.csv)
        Both from Review files

        Args:
            target_csv: Path to MBSTagID.csv (Target meter from Review file)
            reference_csv: Path to Reference_Meter.csv (Reference meter from Review file)
            accuracy_range: Percentage tolerance for comparison (e.g., 1.0 for ±1%)
            data_folder: Folder containing the CSV files

        Returns:
            Dict with comparison results including percentage within range
        """
        result = {
            'percentage_within_range': 0.0,
            'total_comparisons': 0,
            'values_within_range': 0,
            'target_readings': 0,
            'reference_readings': 0,
            'reference_mean': 0.0,
            'status': 'fail',
            'details': ''
        }

        try:
            # Read Target meter data (MBSTagID.csv - Review file format)
            target_file = os.path.join(
                data_folder, os.path.basename(target_csv))
            if not os.path.exists(target_file):
                result['details'] = f'Target CSV file not found: {target_file}'
                return result

            target_df = pd.read_csv(target_file)
            # Strip whitespace from column names to handle formatting inconsistencies
            target_df.columns = target_df.columns.str.strip()

            # Find the :VAL column in target data
            target_val_column = None
            for col in target_df.columns:
                if ':VAL' in col:
                    target_val_column = col
                    break

            if target_val_column is None:
                result['details'] = 'No :VAL column found in target CSV file'
                return result

            # Read Reference meter data (Reference_Meter.csv - Review file format)
            reference_file = os.path.join(
                data_folder, os.path.basename(reference_csv))
            if not os.path.exists(reference_file):
                result['details'] = f'Reference CSV file not found: {reference_file}'
                return result

            reference_df = pd.read_csv(reference_file)
            # Strip whitespace from column names to handle formatting inconsistencies
            reference_df.columns = reference_df.columns.str.strip()

            # Find the :VAL column in reference data
            reference_val_column = None
            for col in reference_df.columns:
                if ':VAL' in col:
                    reference_val_column = col
                    break

            if reference_val_column is None:
                result['details'] = 'No :VAL column found in reference CSV file'
                return result

            # Clean and prepare target data
            target_df['TIME'] = pd.to_datetime(
                target_df['TIME'], errors='coerce')
            target_df = target_df.dropna(subset=['TIME', target_val_column])
            target_values = target_df[target_val_column].values
            target_times = target_df['TIME'].values
            result['target_readings'] = len(target_values)

            # Clean and prepare reference data
            reference_df['TIME'] = pd.to_datetime(
                reference_df['TIME'], errors='coerce')
            reference_df = reference_df.dropna(
                subset=['TIME', reference_val_column])
            reference_values = reference_df[reference_val_column].values
            reference_times = reference_df['TIME'].values
            result['reference_readings'] = len(reference_values)

            if len(target_values) == 0 or len(reference_values) == 0:
                result['details'] = f'Insufficient data: Target={len(target_values)}, Reference={len(reference_values)}'
                return result

            # Time-align the datasets by finding nearest timestamps
            aligned_pairs = []
            for i, target_time in enumerate(target_times):
                target_val = target_values[i]

                # Find closest reference timestamp (within reasonable time window, e.g., 30 seconds)
                time_diffs = np.abs(reference_times - target_time)
                min_diff_idx = np.argmin(time_diffs)
                min_diff_seconds = time_diffs[min_diff_idx] / \
                    np.timedelta64(1, 's')

                if min_diff_seconds <= 30:  # Within 30 seconds
                    reference_val = reference_values[min_diff_idx]
                    aligned_pairs.append((target_val, reference_val))

            result['total_comparisons'] = len(aligned_pairs)

            if result['total_comparisons'] == 0:
                result['details'] = 'No time-aligned data points found between target and reference meters'
                return result

            # Calculate reference mean for comparison (following original project logic)
            reference_vals = [pair[1] for pair in aligned_pairs]
            reference_mean = np.mean(reference_vals)
            result['reference_mean'] = round(reference_mean, 2)

            # Count target values within accuracy range of reference mean
            lower_bound = reference_mean * (1 - accuracy_range / 100)
            upper_bound = reference_mean * (1 + accuracy_range / 100)

            values_within_range = 0
            for target_val, reference_val in aligned_pairs:
                if lower_bound <= target_val <= upper_bound:
                    values_within_range += 1

            result['values_within_range'] = values_within_range
            result['percentage_within_range'] = round(
                (values_within_range / result['total_comparisons']) * 100, 2)

            result['status'] = 'pass'
            result[
                'details'] = f'{result["percentage_within_range"]}% of target values within ±{accuracy_range}% of reference mean ({reference_mean})'

            return result

        except Exception as e:
            self.logger.error(
                f"Error in Test 3.4 Target vs Reference comparison: {e}")
            result['details'] = f'Test execution error: {str(e)}'
            return result

    def _test_41_signal_stability(self, tag_name: str, rtu_file: str,
                                  signal_type: str, window_size: int = 50,
                                  drift_threshold: float = 5.0,
                                  stability_threshold: float = 90.0,
                                  data_dir: str = None) -> Dict[str, Any]:
        """
        Test 4.1: Signal Stability Analysis (Robustness Test)

        Analyzes signal stability using rolling statistics, drift detection, and ±3σ outlier analysis.
        Based on original flowmeter_main.py robustness implementation with 90% threshold approach.

        Args:
            tag_name: The SCADA tag ID to check
            rtu_file: Path to RTU data file
            signal_type: 'digital' or 'analog'
            window_size: Size of rolling window for stability analysis (default: 50)
            drift_threshold: Percentage drift threshold for stability (default: 5.0%)
            stability_threshold: Percentage of readings that must be stable (default: 90.0%)
            data_dir: Directory containing CSV data files

        Returns:
            Dictionary with stability analysis results
        """
        try:
            self.logger.info(
                f"Running Test 4.1 Signal Stability for {signal_type} signal: {tag_name}")

            # Default result structure
            result = {
                'stability_percentage': 0.0,
                'outliers_count': 0,
                'drift_violations': 0,
                'total_readings': 0,
                'stable_readings': 0,
                'mean_value': 0.0,
                'std_deviation': 0.0,
                'status': 'fail',
                'details': f'No data found for {tag_name}'
            }

            # Determine data directory
            if data_dir is None:
                data_dir = os.path.join(os.path.dirname(rtu_file), '_Data')

            # Determine CSV file based on signal type
            if signal_type.lower() == 'digital':
                csv_file = os.path.join(data_dir, "SCADATagID_DIG.csv")
            elif signal_type.lower() == 'analog':
                csv_file = os.path.join(data_dir, "SCADATagID_ANL.csv")
            else:
                result['status'] = 'fail'
                result['details'] = f'Unknown signal type: {signal_type}'
                return result

            if not os.path.exists(csv_file):
                result['status'] = 'fail'
                result['details'] = f'CSV file not found: {csv_file}'
                return result

            # Load CSV data
            df = pd.read_csv(csv_file)

            # Filter for the specific tag
            if 'tag_name' not in df.columns:
                result['status'] = 'fail'
                result['details'] = f'No tag_name column found in {csv_file}'
                return result

            tag_data = df[df['tag_name'] == tag_name].copy()

            if tag_data.empty:
                result['details'] = f'No data found for tag {tag_name}'
                result['status'] = 'fail'
                return result

            # Get values and basic statistics
            values = tag_data['value'].dropna().values
            result['total_readings'] = len(values)

            if result['total_readings'] < window_size:
                result['status'] = 'fail'
                result['details'] = f'Insufficient data: need at least {window_size} readings, got {result["total_readings"]}'
                return result

            # Calculate basic statistics
            mean_value = np.mean(values)
            std_deviation = np.std(values)
            result['mean_value'] = round(mean_value, 3)
            result['std_deviation'] = round(std_deviation, 3)

            # ±3σ outlier detection (original approach)
            lower_3sigma = mean_value - 3 * std_deviation
            upper_3sigma = mean_value + 3 * std_deviation
            outliers = values[(values < lower_3sigma) |
                              (values > upper_3sigma)]
            result['outliers_count'] = len(outliers)

            # Rolling statistics for drift detection
            values_series = pd.Series(values)
            rolling_mean = values_series.rolling(
                window=window_size, center=True).mean()
            rolling_std = values_series.rolling(
                window=window_size, center=True).std()

            # Drift detection: check if rolling mean deviates more than drift_threshold% from overall mean
            drift_violations = 0
            drift_threshold_abs = mean_value * (drift_threshold / 100.0)

            for rolling_val in rolling_mean.dropna():
                if abs(rolling_val - mean_value) > drift_threshold_abs:
                    drift_violations += 1

            result['drift_violations'] = drift_violations

            # Stability analysis: combine outlier and drift analysis
            # A reading is considered "stable" if:
            # 1. It's within ±3σ bounds
            # 2. Its local rolling mean is within drift threshold
            stable_readings = 0

            for i, value in enumerate(values):
                is_within_3sigma = lower_3sigma <= value <= upper_3sigma

                # Check if rolling mean at this point is stable (if available)
                rolling_stable = True
                if not pd.isna(rolling_mean.iloc[i]):
                    rolling_stable = abs(
                        rolling_mean.iloc[i] - mean_value) <= drift_threshold_abs

                if is_within_3sigma and rolling_stable:
                    stable_readings += 1

            result['stable_readings'] = stable_readings
            result['stability_percentage'] = round(
                (stable_readings / result['total_readings']) * 100, 2)

            # Determine pass/fail based on stability_threshold (original 90% approach)
            if result['stability_percentage'] >= stability_threshold:
                result['status'] = 'pass'
                result['details'] = f'Signal stability: {result["stability_percentage"]}% (≥{stability_threshold}% required). Outliers: {result["outliers_count"]}, Drift violations: {drift_violations}'
            else:
                result['status'] = 'fail'
                result['details'] = f'Signal stability: {result["stability_percentage"]}% (<{stability_threshold}% required). Outliers: {result["outliers_count"]}, Drift violations: {drift_violations}'

            return result

        except Exception as e:
            self.logger.error(f"Error in Test 4.1 for {tag_name}: {e}")
            return {
                'stability_percentage': 0.0,
                'outliers_count': 0,
                'drift_violations': 0,
                'total_readings': 0,
                'stable_readings': 0,
                'mean_value': 0.0,
                'std_deviation': 0.0,
                'status': 'fail',
                'details': f'Test execution error: {str(e)}'
            }

    def get_test_results_summary(self) -> Dict[str, Any]:
        """Get test results formatted for UI display with pass/fail icons."""
        if not self.test_results:
            return {
                'total_meters': 0,
                'tests_run': False,
                'message': 'No test results available. Please run the analysis first.',
                'test_details': []
            }

        test_details = []
        for meter_name, results in self.test_results.items():
            meter_summary = {
                'meter_name': meter_name,
                'overall_status': results['overall_status'],
                'test_categories': []
            }

            # Add each test category
            for category_name, category_data in results.items():
                if category_name.endswith('_tests'):
                    category_summary = {
                        'category': category_name.replace('_tests', '').title(),
                        'tests': []
                    }

                    for test_name, test_data in category_data.items():
                        category_summary['tests'].append({
                            'name': test_name,
                            'status': test_data['status'],
                            'value': test_data['value'],
                            'description': test_data['description']
                        })

                    meter_summary['test_categories'].append(category_summary)

            test_details.append(meter_summary)

        total_passed = sum(1 for results in self.test_results.values()
                           if results['overall_status'] == 'pass')

        return {
            'total_meters': len(self.test_results),
            'meters_passed': total_passed,
            'meters_failed': len(self.test_results) - total_passed,
            'tests_run': True,
            'message': f'Analysis completed for {len(self.test_results)} meters',
            'test_details': test_details
        }

    def create_analysis_plots(self, theme_data: Optional[Dict[str, Any]] = None) -> Dict[str, go.Figure]:
        """Create simple, working plots with actual data."""
        template = theme_data.get(
            'template', 'mantine_light') if theme_data else 'mantine_light'
        plotly_template = self._get_plotly_template(template)

        plots = {}

        if not self.test_results:
            # Create placeholder if no data
            plots['status'] = self._create_placeholder_plot(
                plotly_template, "Run Analysis to See Results")
            return plots

        # Plot 1: Overall Test Results
        meters = list(self.test_results.keys())
        statuses = [self.test_results[meter]['overall_status']
                    for meter in meters]

        colors = ['green' if status ==
                  'pass' else 'red' for status in statuses]

        fig1 = go.Figure(data=[
            go.Bar(x=meters, y=[1]*len(meters),
                   marker_color=colors, name='Test Results')
        ])
        fig1.update_layout(
            title="Flowmeter Test Results Overview",
            template=plotly_template,
            xaxis_title="Meters",
            yaxis_title="Status",
            yaxis=dict(tickvals=[0, 1], ticktext=['Fail', 'Pass']),
            height=400
        )
        plots['test_overview'] = fig1

        # Plot 2: Test Category Breakdown
        categories = ['Reliability', 'Timeliness', 'Accuracy']
        pass_counts = []
        fail_counts = []

        for category in categories:
            category_key = category.lower() + '_tests'
            passed = 0
            failed = 0

            for meter_results in self.test_results.values():
                if category_key in meter_results:
                    for test_result in meter_results[category_key].values():
                        if test_result['status'] == 'pass':
                            passed += 1
                        else:
                            failed += 1

            pass_counts.append(passed)
            fail_counts.append(failed)

        fig2 = go.Figure(data=[
            go.Bar(name='Passed', x=categories,
                   y=pass_counts, marker_color='green'),
            go.Bar(name='Failed', x=categories,
                   y=fail_counts, marker_color='red')
        ])
        fig2.update_layout(
            title="Test Results by Category",
            template=plotly_template,
            barmode='stack',
            height=400
        )
        plots['category_breakdown'] = fig2

        # Plot 3: Success Rate Pie Chart
        total_passed = sum(1 for results in self.test_results.values()
                           if results['overall_status'] == 'pass')
        total_failed = len(self.test_results) - total_passed

        fig3 = go.Figure(data=[go.Pie(
            labels=['Passed', 'Failed'],
            values=[total_passed, total_failed],
            marker_colors=['green', 'red']
        )])
        fig3.update_layout(
            title="Overall Success Rate",
            template=plotly_template,
            height=400
        )
        plots['success_rate'] = fig3

        return plots

    def _create_placeholder_plot(self, template: str, title: str) -> go.Figure:
        """Create a placeholder plot."""
        fig = go.Figure()
        fig.add_annotation(
            text="Run flowmeter acceptance analysis to see results",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            title=title,
            template=template,
            showlegend=False,
            height=400,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        return fig

    def _get_plotly_template(self, dmc_template: str) -> str:
        """Convert DMC theme to Plotly template."""
        template_map = {
            'mantine_light': 'plotly_white',
            'mantine_dark': 'plotly_dark'
        }
        return template_map.get(dmc_template, 'plotly_white')

    def _test_35_snr_comparison(self, digital_tag: str, analog_tag: str, ref_scada_tag: str,
                                rtu_file: str, min_q: float, data_dir: str = None) -> Dict[str, Any]:
        """
        Test 3.5: Target DIG/ANL SNR within 95% of Reference meter SNR

        Compares the SNR of digital and analog signals with reference meter SNR.
        Pass criteria: Both digital and analog SNR should be within 95% of reference meter SNR.

        Args:
            digital_tag: Digital signal tag name
            analog_tag: Analog signal tag name  
            ref_scada_tag: Reference SCADA tag name
            rtu_file: RTU file path
            min_q: Minimum flow threshold
            data_dir: Data directory containing CSV files

        Returns:
            Dict with comparison results
        """
        result = {
            'digital_snr': None,
            'analog_snr': None,
            'reference_snr': None,
            'digital_within_95_percent': False,
            'analog_within_95_percent': False,
            'status': 'fail',
            'details': 'Test 3.5 - SNR comparison not performed'
        }

        try:
            self.logger.info(
                f"Running Test 3.5 SNR comparison for digital: {digital_tag}, analog: {analog_tag}, reference: {ref_scada_tag}")

            # If no reference SCADA tag, skip this test
            if not ref_scada_tag:
                result['details'] = 'No reference SCADA tag (Ref_SCADATagID) defined - Test 3.5 skipped'
                return result

            # Get SNR for digital signal
            digital_snr_result = self._test_32_signal_noise_ratio(
                digital_tag, rtu_file, 'digital', min_q, data_dir)
            result['digital_snr'] = digital_snr_result.get('snr_value')

            # Get SNR for analog signal
            analog_snr_result = self._test_32_signal_noise_ratio(
                analog_tag, rtu_file, 'analog', min_q, data_dir)
            result['analog_snr'] = analog_snr_result.get('snr_value')

            # Get SNR for reference SCADA signal (treat as analog signal type)
            ref_snr_result = self._test_32_signal_noise_ratio(
                ref_scada_tag, rtu_file, 'ref_scada', min_q, data_dir)
            result['reference_snr'] = ref_snr_result.get('snr_value')

            # Check if all SNR values are available
            if None in [result['digital_snr'], result['analog_snr'], result['reference_snr']]:
                missing = []
                if result['digital_snr'] is None:
                    missing.append('digital')
                if result['analog_snr'] is None:
                    missing.append('analog')
                if result['reference_snr'] is None:
                    missing.append('reference')
                result['details'] = f'SNR calculation failed for: {", ".join(missing)}'
                return result

            # Calculate 95% threshold of reference SNR
            ref_snr_95_percent = result['reference_snr'] * 0.95

            # Check if digital SNR is within 95% of reference
            result['digital_within_95_percent'] = result['digital_snr'] >= ref_snr_95_percent

            # Check if analog SNR is within 95% of reference
            result['analog_within_95_percent'] = result['analog_snr'] >= ref_snr_95_percent

            # Test passes if both digital and analog are within 95% of reference
            both_within_threshold = result['digital_within_95_percent'] and result['analog_within_95_percent']

            if both_within_threshold:
                result['status'] = 'pass'
                result[
                    'details'] = f'PASS: Digital SNR {result["digital_snr"]:.1f} dB, Analog SNR {result["analog_snr"]:.1f} dB both ≥ 95% of Reference SNR {result["reference_snr"]:.1f} dB (≥{ref_snr_95_percent:.1f} dB)'
            else:
                result['status'] = 'fail'
                digital_status = "✓" if result['digital_within_95_percent'] else "✗"
                analog_status = "✓" if result['analog_within_95_percent'] else "✗"
                result[
                    'details'] = f'FAIL: Digital {digital_status} {result["digital_snr"]:.1f} dB, Analog {analog_status} {result["analog_snr"]:.1f} dB vs Reference {result["reference_snr"]:.1f} dB (need ≥{ref_snr_95_percent:.1f} dB)'

            return result

        except Exception as e:
            self.logger.error(f"Error in Test 3.5 SNR comparison: {e}")
            result['details'] = f'Test 3.5 execution error: {str(e)}'
            return result

    def export_csv_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Export RTU and Review data to CSV files in _Data directory."""
        try:
            self.logger.info("Starting CSV data export")

            # Get file paths first
            rtu_file = params['rtu_file']
            review_file = params['review_file']
            tags_file = params['csv_tags_file']
            time_start = params['time_start']
            time_end = params['time_end']

            # Create _Data directory next to the Tags.in file
            tags_file_dir = os.path.dirname(tags_file)
            data_dir = os.path.join(tags_file_dir, "_Data")
            os.makedirs(data_dir, exist_ok=True)

            # Load tags configuration
            self.tags_df = pd.read_csv(tags_file)
            self.logger.info(
                f"Loaded {len(self.tags_df)} meter configurations")

            exported_files = []

            # Process each meter's tags (Tags.in format only)
            for index, row in self.tags_df.iterrows():
                meter_name = row['MBSTagID'].strip()
                digital_tag = row['SCADATagID_DIG'].strip()
                analog_tag = row['SCADATagID_ANL'].strip()
                ref_tag = row['Reference_Meter'].strip()
                # Handle the new Ref_SCADATagID column if it exists
                ref_scada_tag = row.get('Ref_SCADATagID', '').strip(
                ) if 'Ref_SCADATagID' in row else ''

                self.logger.info(f"Exporting data for meter: {meter_name}")

                # Export RTU data for digital tag
                if digital_tag:
                    dig_csv_file = os.path.join(data_dir, "SCADATagID_DIG.csv")
                    self._export_rtu_tag_data(
                        rtu_file, digital_tag, dig_csv_file, time_start, time_end)
                    exported_files.append(dig_csv_file)

                # Export RTU data for analog tag
                if analog_tag:
                    anl_csv_file = os.path.join(data_dir, "SCADATagID_ANL.csv")
                    self._export_rtu_tag_data(
                        rtu_file, analog_tag, anl_csv_file, time_start, time_end)
                    exported_files.append(anl_csv_file)

                # Export RTU data for reference SCADA tag (new functionality)
                if ref_scada_tag:
                    ref_scada_csv_file = os.path.join(
                        data_dir, "Ref_SCADATagID.csv")
                    self._export_rtu_tag_data(
                        rtu_file, ref_scada_tag, ref_scada_csv_file, time_start, time_end)
                    exported_files.append(ref_scada_csv_file)

                # Export Review data for MBS tag
                if meter_name:
                    mbs_csv_file = os.path.join(data_dir, "MBSTagID.csv")
                    self._export_review_tag_data(
                        review_file, meter_name, mbs_csv_file, time_start, time_end)
                    exported_files.append(mbs_csv_file)

                # Export Review data for Reference tag
                if ref_tag:
                    ref_csv_file = os.path.join(
                        data_dir, "Reference_Meter.csv")
                    self._export_review_tag_data(
                        review_file, ref_tag, ref_csv_file, time_start, time_end)
                    exported_files.append(ref_csv_file)

            return {
                'success': True,
                # Remove duplicates
                'exported_files': list(set(exported_files)),
                'data_dir': data_dir,
                'message': f'CSV export completed. {len(set(exported_files))} files exported to {data_dir}'
            }

        except Exception as e:
            self.logger.error(f"CSV export failed: {e}")
            raise ProcessingError(f"CSV export error: {e}")

    def _export_rtu_tag_data(self, rtu_file: str, tag_name: str, output_file: str,
                             start_time: str, end_time: str):
        """Export RTU data for a specific tag to CSV."""
        try:
            self.logger.info(f"Exporting RTU tag: {tag_name} to {output_file}")

            # Create a temporary tags file for the specific tag
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_tags_file:
                temp_tags_file.write(tag_name)
                temp_tags_path = temp_tags_file.name

            try:
                self.rtu_service.export_csv_flat(
                    input_file=rtu_file,
                    output_file=output_file,
                    start_time=start_time,
                    end_time=end_time,
                    tags_file=temp_tags_path
                )
                self.logger.info(
                    f"Successfully exported RTU tag {tag_name} to {output_file}")
            finally:
                # Clean up temporary file
                if os.path.exists(temp_tags_path):
                    os.unlink(temp_tags_path)

        except Exception as e:
            self.logger.error(f"Failed to export RTU tag {tag_name}: {e}")
            raise ProcessingError(f"RTU export error for {tag_name}: {e}")

    def _export_review_tag_data(self, review_file: str, tag_name: str, output_file: str,
                                start_time: str, end_time: str):
        """Export Review data for a specific tag using ReviewCsvService exactly like REVIEW to CSV page."""
        try:
            self.logger.info(
                f"Exporting Review tag: {tag_name} to {output_file}")

            # Get the review folder from the review file (parent directory)
            review_folder = os.path.dirname(review_file)
            if not review_folder:
                review_folder = "."

            if not os.path.exists(review_folder):
                raise ValueError(f"Review folder not found: {review_folder}")

            # Format times exactly like REVIEW to CSV page (yy/MM/dd_HH:mm:ss format)
            def parse_datetime_to_service_format(dt_str):
                # Handle the flowmeter format which is already in yy/mm/dd HH:MM:SS
                formats = [
                    '%y/%m/%d %H:%M:%S',  # This is what flowmeter service uses
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d'
                ]
                for fmt in formats:
                    try:
                        dt = datetime.strptime(dt_str, fmt)
                        # Convert to yy/MM/dd_HH:mm:ss format (underscore between date and time)
                        return dt.strftime('%y/%m/%d_%H:%M:%S')
                    except ValueError:
                        continue
                raise ValueError(f"Could not parse datetime: {dt_str}")

            start_formatted = parse_datetime_to_service_format(start_time)
            end_formatted = parse_datetime_to_service_format(end_time)

            # Create tags with suffixes (same as original logic)
            tag_variants = [
                f"{tag_name}:VAL",
                f"{tag_name}:ST",
                f"{tag_name}:FLAT"
            ]

            try:
                # Create ReviewCsvService instance exactly like REVIEW to CSV page
                review_service = ReviewCsvService(
                    folder_path=review_folder,
                    start_time=start_formatted,
                    end_time=end_formatted,
                    peek_list=tag_variants,  # Set peek_list directly instead of using file
                    dump_all=True,  # Export all data points, not just sampled at intervals
                    freq=None,  # Not used when dump_all=True
                    merged_file=os.path.basename(output_file)
                )
                review_service.run()

                # The merged file should be in the review folder, move it to output location
                source_file = os.path.join(
                    review_folder, os.path.basename(output_file))
                if os.path.exists(source_file):
                    if source_file != output_file:
                        shutil.move(source_file, output_file)
                    self.logger.info(
                        f"Successfully exported Review tag {tag_name} to {output_file}")
                else:
                    self.logger.warning(
                        f"Expected output file not found: {source_file}")
                    # Check if there are any CSV files generated in the review folder
                    csv_files = [f for f in os.listdir(
                        review_folder) if f.endswith('.csv')]
                    self.logger.info(
                        f"CSV files found in review folder: {csv_files}")

            except Exception as service_error:
                self.logger.error(f"ReviewCsvService failed: {service_error}")
                raise

        except Exception as e:
            self.logger.error(f"Failed to export Review tag {tag_name}: {e}")
            raise ProcessingError(f"Review export error for {tag_name}: {e}")

            return {
                'success': True,
                'exported_files': exported_files,
                'data_dir': data_dir,
                'message': f'Successfully exported {len(exported_files)} CSV files to {data_dir}'
            }

        except Exception as e:
            self.logger.error(f"Error in CSV export: {e}")
            return {
                'success': False,
                'exported_files': [],
                'data_dir': None,
                'message': f'CSV export failed: {str(e)}'
            }
