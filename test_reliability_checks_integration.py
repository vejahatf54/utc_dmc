"""
Integration Tests for Flowmeter Acceptance Tests 1.1-1.4, 2.1-2.2, 3.1-3.4

14 integration tests using real L05 data:
- Test 1.1: Digital Signal Range 
- Test 1.1: Analog Signal Range
- Test 1.2: Digital Signal Units 
- Test 1.3: Digital Signal Quality
- Test 1.3: Analog Signal Quality
- Test 1.4: Review File Quality
- Test 2.1: Digital Signal Time Differences
- Test 2.1: Analog Signal Time Differences  
- Test 2.2: FLAT Attribute Check
- Test 3.1: Mean Squared Error
- Test 3.2: Digital Signal SNR
- Test 3.2: Analog Signal SNR
- Test 3.3: Target vs Digital Signal Comparison
- Test 3.4: Target vs Reference Meter Comparison

Test Configuration:
- Data Range: 1500-4000
- Date Range: 2025/06/27 04:30:00 to 2025/06/27 05:30:00
- Data Source: C:\\Temp\\python_projects\\Flow Meter Acceptance L05\\_Data

Run with: 
- C:/Temp/python_projects/DMC/.venv/Scripts/python.exe -m pytest test_reliability_checks_integration.py -v
- Or simply: pytest test_reliability_checks_integration.py -v (if virtual environment is activated)
"""

from services.flowmeter_acceptance_service import FlowmeterAcceptanceService
import pytest
import os
import sys
import pandas as pd
from datetime import datetime
import logging

# Add the project root to the path so we can import our services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Test configuration
DATA_DIR = r"C:\Temp\python_projects\Flow Meter Acceptance L05\_Data"
DIGITAL_CSV = os.path.join(DATA_DIR, "SCADATagID_DIG.csv")
ANALOG_CSV = os.path.join(DATA_DIR, "SCADATagID_ANL.csv")
MBS_CSV = os.path.join(DATA_DIR, "MBSTagID.csv")

# Test parameters
TIME_START = "2025/06/27 04:30:00"
TIME_END = "2025/06/27 05:30:00"
MIN_RANGE = 1500.0
MAX_RANGE = 4000.0
MIN_Q = 100.0
MAX_Q = 15000.0
FLAT_THRESHOLD = 5.0

# Tag names from Tags.in
DIGITAL_TAG = "rate.SN-5-FIT-1-SQ-DFR"
ANALOG_TAG = "rate.SN-5-FIT-1-SQ-AFR"
MBS_TAG = "SN_QSO_SU_5M1"


@pytest.fixture(scope="session")
def setup_test_environment():
    """Set up test environment with real L05 data."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Verify real data files exist
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"L05 data directory not found: {DATA_DIR}")
    if not os.path.exists(DIGITAL_CSV):
        raise FileNotFoundError(f"Digital CSV not found: {DIGITAL_CSV}")
    if not os.path.exists(ANALOG_CSV):
        raise FileNotFoundError(f"Analog CSV not found: {ANALOG_CSV}")
    if not os.path.exists(MBS_CSV):
        raise FileNotFoundError(f"MBS CSV not found: {MBS_CSV}")

    # Create dummy RTU file for service calls (required but not used)
    dummy_rtu_file = os.path.join(DATA_DIR, "dummy.dt")
    with open(dummy_rtu_file, 'w') as f:
        f.write("dummy rtu file")

    logger.info("Integration test setup complete - using real L05 data")

    yield {
        'data_dir': DATA_DIR,
        'dummy_rtu_file': dummy_rtu_file,
        'logger': logger
    }

    # Cleanup
    if os.path.exists(dummy_rtu_file):
        os.remove(dummy_rtu_file)


@pytest.fixture(scope="session")
def service():
    """Initialize the FlowmeterAcceptanceService."""
    return FlowmeterAcceptanceService()


def test_11_digital_range(setup_test_environment, service):
    """Test 1.1: Digital Signal Range - using actual L05 data"""
    env = setup_test_environment
    result = service._test_11_readings_within_range(
        DIGITAL_TAG, env['dummy_rtu_file'], 'digital',
        MIN_RANGE, MAX_RANGE, env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['status'] == 'pass', "Digital range test should pass"
    env['logger'].info(
        f"Test 1.1 Digital: {result['total_readings']} readings, "
        f"{result['out_of_range_count']} out of range, status: {result['status']}")

    # Verify specific result structure
    assert 'out_of_range_count' in result
    assert 'total_readings' in result


def test_11_analog_range(setup_test_environment, service):
    """Test 1.1: Analog Signal Range - using actual L05 data"""
    env = setup_test_environment
    result = service._test_11_readings_within_range(
        ANALOG_TAG, env['dummy_rtu_file'], 'analog',
        MIN_RANGE, MAX_RANGE, env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['status'] == 'pass', "Analog range test should pass"
    env['logger'].info(
        f"Test 1.1 Analog: {result['total_readings']} readings, "
        f"{result['out_of_range_count']} out of range, status: {result['status']}")

    # Verify specific result structure
    assert 'out_of_range_count' in result
    assert 'total_readings' in result


def test_12_digital_units(setup_test_environment, service):
    """Test 1.2: Digital Signal Units - using actual L05 data"""
    env = setup_test_environment
    result = service._test_12_units_verified(
        DIGITAL_TAG, env['dummy_rtu_file'], 'digital',
        MIN_Q, MAX_Q, env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['status'] == 'pass', "Digital units test should pass"
    env['logger'].info(
        f"Test 1.2 Digital: {result['total_readings']} readings, "
        f"{result['conversions_applied']} conversions, status: {result['status']}")

    # Verify specific result structure
    assert 'conversions_applied' in result
    assert 'total_readings' in result


def test_13_digital_quality(setup_test_environment, service):
    """Test 1.3: Digital Signal Quality - using actual L05 data"""
    env = setup_test_environment
    result = service._test_13_quality_is_good(
        DIGITAL_TAG, env['dummy_rtu_file'], 'digital', env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['status'] == 'pass', "Digital quality test should pass"
    env['logger'].info(
        f"Test 1.3 Digital: {result['total_readings']} readings, "
        f"{result['bad_quality_count']} bad quality, status: {result['status']}")

    # Verify specific result structure
    assert 'bad_quality_count' in result
    assert 'total_readings' in result


def test_13_analog_quality(setup_test_environment, service):
    """Test 1.3: Analog Signal Quality - using actual L05 data"""
    env = setup_test_environment
    result = service._test_13_quality_is_good(
        ANALOG_TAG, env['dummy_rtu_file'], 'analog', env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['status'] == 'pass', "Analog quality test should pass"
    env['logger'].info(
        f"Test 1.3 Analog: {result['total_readings']} readings, "
        f"{result['bad_quality_count']} bad quality, status: {result['status']}")

    # Verify specific result structure
    assert 'bad_quality_count' in result
    assert 'total_readings' in result


def test_14_review_quality(setup_test_environment, service):
    """Test 1.4: Review File Quality - using actual L05 MBSTagID.csv data"""
    env = setup_test_environment
    result = service._test_14_quality_review(
        MBS_TAG, "dummy_review_file", env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['status'] == 'pass', "Review quality test should pass"
    env['logger'].info(
        f"Test 1.4 Review: {result['total_readings']} readings, "
        f"{result['bad_status_count']} bad status, status: {result['status']}")

    # Verify specific result structure
    assert 'bad_status_count' in result
    assert 'total_readings' in result


def test_21_digital_time_differences(setup_test_environment, service):
    """Test 2.1: Digital Signal Time Differences - using actual L05 data"""
    env = setup_test_environment
    result = service._test_21_time_differences(
        DIGITAL_TAG, env['dummy_rtu_file'], 'digital', env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['status'] == 'pass', "Digital time diff test should pass"
    assert result['max_time_diff'] >= 0, "Max time diff should be >= 0"
    assert result['mean_time_diff'] >= 0.0, "Mean time diff should be >= 0"
    env['logger'].info(
        f"Test 2.1 Digital: {result['total_readings']} readings, "
        f"Max: {result['max_time_diff']}s, Mean: {result['mean_time_diff']}s")

    # Verify specific result structure
    assert 'max_time_diff' in result
    assert 'mean_time_diff' in result


def test_21_analog_time_differences(setup_test_environment, service):
    """Test 2.1: Analog Signal Time Differences - using actual L05 data"""
    env = setup_test_environment
    result = service._test_21_time_differences(
        ANALOG_TAG, env['dummy_rtu_file'], 'analog', env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['status'] == 'pass', "Analog time diff test should pass"
    assert result['max_time_diff'] >= 0, "Max time diff should be >= 0"
    assert result['mean_time_diff'] >= 0.0, "Mean time diff should be >= 0"
    env['logger'].info(
        f"Test 2.1 Analog: {result['total_readings']} readings, "
        f"Max: {result['max_time_diff']}s, Mean: {result['mean_time_diff']}s")

    # Verify specific result structure
    assert 'max_time_diff' in result
    assert 'mean_time_diff' in result


def test_22_flat_attribute(setup_test_environment, service):
    """Test 2.2: FLAT Attribute Check - using actual L05 MBSTagID.csv data"""
    env = setup_test_environment
    result = service._test_22_flat_attribute(
        MBS_TAG, "dummy_review_file", FLAT_THRESHOLD, env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['flat_check_status'] in ['GOOD', 'BAD', 'FLAT Not Available', 'no_data'], \
        "Should have valid flat check status"
    env['logger'].info(
        f"Test 2.2 FLAT: {result['total_readings']} total readings, "
        f"{result['non_shutdown_readings']} non-shutdown, status: {result['flat_check_status']}")

    # Verify specific result structure
    assert 'flat_check_status' in result
    assert 'non_shutdown_readings' in result


def test_31_mean_squared_error(setup_test_environment, service):
    """Test 3.1: Mean Squared Error - using actual L05 data"""
    env = setup_test_environment
    result = service._test_31_mean_squared_error(
        DIGITAL_TAG, ANALOG_TAG, env['dummy_rtu_file'], env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['status'] == 'pass', "MSE test should pass"
    assert result['mse_value'] >= 0.0, "MSE value should be >= 0"
    assert result['nominal_flowrate'] > 0.0, "Nominal flowrate should be > 0"
    env['logger'].info(
        f"Test 3.1 MSE: {result['total_readings']} readings, "
        f"MSE: {result['mse_value']}, Avg Flow: {result['nominal_flowrate']}")

    # Verify specific result structure
    assert 'mse_value' in result
    assert 'nominal_flowrate' in result

    # Verify MSE is calculated properly (should be reasonable for real data)
    assert result['mse_value'] < 1000000, "MSE should be reasonable for real data"


def test_32_signal_noise_ratio_digital(setup_test_environment, service):
    """Test 3.2: Signal-to-Noise Ratio for Digital Signal - using actual L05 data"""
    env = setup_test_environment
    result = service._test_32_signal_noise_ratio(
        DIGITAL_TAG, env['dummy_rtu_file'], 'digital', MIN_Q, env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['steady_state_readings'] > 0, "Should have steady state readings above min_q"

    if result['snr_value'] is not None:
        assert result['status'] == 'pass', "SNR test should pass when SNR is calculated"
        assert result['snr_value'] > 0, "SNR value should be positive"
        env['logger'].info(
            f"Test 3.2 Digital SNR: {result['total_readings']} total readings, "
            f"{result['steady_state_readings']} steady state, SNR: {result['snr_value']}")

        # Verify specific result structure
        assert 'snr_value' in result
        assert 'steady_state_readings' in result

        # Verify SNR is reasonable for real data (should be positive and not too extreme)
        assert 0.1 < result['snr_value'] < 10000, "SNR should be reasonable for real data"
    else:
        # If no SNR calculated, should have proper failure reason
        assert result['status'] == 'fail', "Should fail when SNR cannot be calculated"
        env['logger'].info(f"Test 3.2 Digital SNR failed: {result['details']}")


def test_32_signal_noise_ratio_analog(setup_test_environment, service):
    """Test 3.2: Signal-to-Noise Ratio for Analog Signal - using actual L05 data"""
    env = setup_test_environment
    result = service._test_32_signal_noise_ratio(
        ANALOG_TAG, env['dummy_rtu_file'], 'analog', MIN_Q, env['data_dir'])

    assert result['total_readings'] > 0, "Should have readings"
    assert result['steady_state_readings'] > 0, "Should have steady state readings above min_q"

    if result['snr_value'] is not None:
        assert result['status'] == 'pass', "SNR test should pass when SNR is calculated"
        assert result['snr_value'] > 0, "SNR value should be positive"
        env['logger'].info(
            f"Test 3.2 Analog SNR: {result['total_readings']} total readings, "
            f"{result['steady_state_readings']} steady state, SNR: {result['snr_value']}")

        # Verify specific result structure
        assert 'snr_value' in result
        assert 'steady_state_readings' in result

        # Verify SNR is reasonable for real data (should be positive and not too extreme)
        assert 0.1 < result['snr_value'] < 10000, "SNR should be reasonable for real data"
    else:
        # If no SNR calculated, should have proper failure reason
        assert result['status'] == 'fail', "Should fail when SNR cannot be calculated"
        env['logger'].info(f"Test 3.2 Analog SNR failed: {result['details']}")


def test_33_target_vs_digital_comparison(setup_test_environment, service):
    """Test 3.3: Target vs Digital Signal Comparison - using actual L05 data"""
    env = setup_test_environment

    # Hardcoded test parameters (as requested - NOT in service)
    ACCURACY_RANGE = 1.0  # ±1% tolerance
    TARGET_CSV = "MBSTagID.csv"
    DIGITAL_CSV = "SCADATagID_DIG.csv"

    result = service._test_33_target_vs_digital_comparison(
        TARGET_CSV, DIGITAL_CSV, ACCURACY_RANGE, env['data_dir'])

    assert result['target_readings'] > 0, "Should have target readings"
    assert result['digital_readings'] > 0, "Should have digital readings"
    assert result['total_comparisons'] > 0, "Should have time-aligned comparisons"

    if result['status'] == 'pass':
        assert result['percentage_within_range'] >= 0, "Percentage should be non-negative"
        assert result['values_within_range'] >= 0, "Values within range should be non-negative"
        env['logger'].info(
            f"Test 3.3 Target vs Digital: {result['total_comparisons']} comparisons, "
            f"{result['percentage_within_range']}% within ±{ACCURACY_RANGE}% range")
    else:
        env['logger'].info(
            f"Test 3.3 Target vs Digital failed: {result['details']}")

    # Verify result structure
    assert 'percentage_within_range' in result
    assert 'total_comparisons' in result
    assert 'values_within_range' in result


def test_34_target_vs_reference_comparison(setup_test_environment, service):
    """Test 3.4: Target vs Reference Meter Comparison - using actual L05 data"""
    env = setup_test_environment

    # Hardcoded test parameters (as requested - NOT in service)
    ACCURACY_RANGE = 1.0  # ±1% tolerance
    TARGET_CSV = "MBSTagID.csv"
    REFERENCE_CSV = "Reference_Meter.csv"

    result = service._test_34_target_vs_reference_comparison(
        TARGET_CSV, REFERENCE_CSV, ACCURACY_RANGE, env['data_dir'])

    assert result['target_readings'] > 0, "Should have target readings"
    assert result['reference_readings'] > 0, "Should have reference readings"
    assert result['total_comparisons'] > 0, "Should have time-aligned comparisons"

    if result['status'] == 'pass':
        assert result['percentage_within_range'] >= 0, "Percentage should be non-negative"
        assert result['values_within_range'] >= 0, "Values within range should be non-negative"
        assert result['reference_mean'] > 0, "Reference mean should be positive"
        env['logger'].info(
            f"Test 3.4 Target vs Reference: {result['total_comparisons']} comparisons, "
            f"{result['percentage_within_range']}% within ±{ACCURACY_RANGE}% of reference mean ({result['reference_mean']})")
    else:
        env['logger'].info(
            f"Test 3.4 Target vs Reference failed: {result['details']}")

    # Verify result structure
    assert 'percentage_within_range' in result
    assert 'total_comparisons' in result
    assert 'values_within_range' in result
    assert 'reference_mean' in result
