"""
Integration Tests for Flowmeter Acceptance Tests 1.1-1.4, 2.1-2.2, and 3.1

10 integration tests using real L05 data:
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
