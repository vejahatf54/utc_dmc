"""
Integration Tests for Flowmeter Acceptance Reliability Checks 1.1-1.4

6 tests for reliability checks:
- Test 1.1: Digital Signal Range 
- Test 1.1: Analog Signal Range
- Test 1.2: Digital Signal Units 
- Test 1.3: Digital Signal Quality
- Test 1.3: Analog Signal Quality
- Test 1.4: Review File Quality

Test Configuration:
- Data Range: 1500-4000
- Date Range: 2025/06/27 04:30:00 to 2025/06/27 05:30:00
- Data Source: C:\\Temp\\python_projects\\Flow Meter Acceptance L05\\_Data
"""

from services.flowmeter_acceptance_service import FlowmeterAcceptanceService
import unittest
import os
import sys
import tempfile
import shutil
import pandas as pd
from datetime import datetime
import logging

# Add the project root to the path so we can import our services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestReliabilityChecksIntegration(unittest.TestCase):
    """6 integration tests for reliability checks using actual L05 data."""

    @classmethod
    def setUpClass(cls):
        """Set up test class with actual data paths and configuration."""
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)

        # Data source paths
        cls.data_dir = r"C:\Temp\python_projects\Flow Meter Acceptance L05\_Data"
        cls.digital_csv = os.path.join(cls.data_dir, "SCADATagID_DIG.csv")
        cls.analog_csv = os.path.join(cls.data_dir, "SCADATagID_ANL.csv")
        cls.mbs_csv = os.path.join(cls.data_dir, "MBSTagID.csv")

        # Test parameters
        cls.time_start = "2025/06/27 04:30:00"
        cls.time_end = "2025/06/27 05:30:00"

        # Tag names from Tags.in
        cls.digital_tag = "rate.SN-5-FIT-1-SQ-DFR"
        cls.analog_tag = "rate.SN-5-FIT-1-SQ-AFR"
        cls.mbs_tag = "SN_QSO_SU_5M1"

        # Create temporary working directory for tests
        cls.temp_dir = tempfile.mkdtemp(prefix="reliability_tests_")

        # Initialize the service
        cls.service = FlowmeterAcceptanceService()

        cls.logger.info("Test setup complete")

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files."""
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    def _create_test_csv(self, source_csv, tag_name, filename):
        """Helper to create test CSV files in the expected format."""
        # Create unique temp directory for this test to avoid interference
        test_temp_dir = tempfile.mkdtemp(
            prefix=f"test_{filename.replace('.csv', '')}_")

        # Load and filter data
        df = pd.read_csv(source_csv)
        df['datetime'] = pd.to_datetime(df['datetime'])

        # Filter by date range
        start_dt = datetime.strptime(self.time_start, "%Y/%m/%d %H:%M:%S")
        end_dt = datetime.strptime(self.time_end, "%Y/%m/%d %H:%M:%S")
        filtered_df = df[
            (df['datetime'] >= start_dt) &
            (df['datetime'] <= end_dt)
        ]

        # Create RTU format CSV with 'ident' column expected by service
        rtu_data = filtered_df.copy()
        rtu_data['ident'] = rtu_data['tag_name']

        # Create temp CSV file
        temp_csv = os.path.join(test_temp_dir, filename)
        rtu_data.to_csv(temp_csv, index=False)

        # Create _Data directory structure expected by service with ONLY this file
        data_dir = os.path.join(test_temp_dir, '_Data')
        os.makedirs(data_dir, exist_ok=True)
        shutil.copy(temp_csv, os.path.join(data_dir, filename))

        return temp_csv

    def test_11_digital_range(self):
        """Test 1.1: Digital Signal Range - using actual L05 data"""
        # Create temporary structure for test with _Data subdirectory
        test_dir = tempfile.mkdtemp(prefix="test_11_digital_")
        dummy_dt_file = os.path.join(test_dir, "dummy.dt")
        data_dir = os.path.join(test_dir, "_Data")
        os.makedirs(data_dir, exist_ok=True)

        # Copy the actual L05 data to the _Data directory
        shutil.copy(self.digital_csv, os.path.join(
            data_dir, "SCADATagID_DIG.csv"))

        # Create dummy .dt file
        with open(dummy_dt_file, 'w') as f:
            f.write("dummy file")

        try:
            result = self.service._test_11_readings_within_range(
                self.digital_tag, dummy_dt_file, 'digital', 1500.0, 4000.0, data_dir)

            self.assertGreater(result['total_readings'],
                               0, "Should have readings")
            self.logger.info(
                f"Test 1.1 Digital: {result['total_readings']} readings, status: {result['status']}")
        finally:
            shutil.rmtree(test_dir)

    def test_11_analog_range(self):
        """Test 1.1: Analog Signal Range - using actual L05 data"""
        # Create temporary structure for test with _Data subdirectory
        test_dir = tempfile.mkdtemp(prefix="test_11_analog_")
        dummy_dt_file = os.path.join(test_dir, "dummy.dt")
        data_dir = os.path.join(test_dir, "_Data")
        os.makedirs(data_dir, exist_ok=True)

        # Copy the actual L05 data to the _Data directory
        target_csv = os.path.join(data_dir, "SCADATagID_ANL.csv")
        shutil.copy(self.analog_csv, target_csv)
        self.logger.info(f"Copied {self.analog_csv} to {target_csv}")
        self.logger.info(
            f"File exists after copy: {os.path.exists(target_csv)}")

        # Create dummy .dt file
        with open(dummy_dt_file, 'w') as f:
            f.write("dummy file")
        self.logger.info(f"Created dummy file: {dummy_dt_file}")

        try:
            result = self.service._test_11_readings_within_range(
                self.analog_tag, dummy_dt_file, 'analog', 1500.0, 4000.0, data_dir)

            self.logger.info(f"Test result: {result}")
            self.assertGreater(result['total_readings'],
                               0, "Should have readings")
            self.logger.info(
                f"Test 1.1 Analog: {result['total_readings']} readings, status: {result['status']}")
        finally:
            shutil.rmtree(test_dir)

    def test_12_digital_units(self):
        """Test 1.2: Digital Signal Units - using actual L05 data"""
        # Create temporary structure for test with _Data subdirectory
        test_dir = tempfile.mkdtemp(prefix="test_12_digital_")
        dummy_dt_file = os.path.join(test_dir, "dummy.dt")
        data_dir = os.path.join(test_dir, "_Data")
        os.makedirs(data_dir, exist_ok=True)

        # Copy the actual L05 data to the _Data directory
        shutil.copy(self.digital_csv, os.path.join(
            data_dir, "SCADATagID_DIG.csv"))

        # Create dummy .dt file
        with open(dummy_dt_file, 'w') as f:
            f.write("dummy file")

        try:
            result = self.service._test_12_units_verified(
                self.digital_tag, dummy_dt_file, 'digital', 100.0, 15000.0, data_dir)

            self.assertGreater(result['total_readings'],
                               0, "Should have readings")
            self.logger.info(
                f"Test 1.2 Digital: {result['total_readings']} readings, status: {result['status']}")
        finally:
            shutil.rmtree(test_dir)

    def test_13_digital_quality(self):
        """Test 1.3: Digital Signal Quality - using actual L05 data"""
        # Create temporary structure for test with _Data subdirectory
        test_dir = tempfile.mkdtemp(prefix="test_13_digital_")
        dummy_dt_file = os.path.join(test_dir, "dummy.dt")
        data_dir = os.path.join(test_dir, "_Data")
        os.makedirs(data_dir, exist_ok=True)

        # Copy the actual L05 data to the _Data directory
        shutil.copy(self.digital_csv, os.path.join(
            data_dir, "SCADATagID_DIG.csv"))

        # Create dummy .dt file
        with open(dummy_dt_file, 'w') as f:
            f.write("dummy file")

        try:
            result = self.service._test_13_quality_is_good(
                self.digital_tag, dummy_dt_file, 'digital', data_dir)

            self.assertGreater(result['total_readings'],
                               0, "Should have readings")
            self.logger.info(
                f"Test 1.3 Digital: {result['total_readings']} readings, status: {result['status']}")
        finally:
            shutil.rmtree(test_dir)

    def test_13_analog_quality(self):
        """Test 1.3: Analog Signal Quality - using actual L05 data"""
        # Create temporary structure for test with _Data subdirectory
        test_dir = tempfile.mkdtemp(prefix="test_13_analog_")
        dummy_dt_file = os.path.join(test_dir, "dummy.dt")
        data_dir = os.path.join(test_dir, "_Data")
        os.makedirs(data_dir, exist_ok=True)

        # Copy the actual L05 data to the _Data directory
        shutil.copy(self.analog_csv, os.path.join(
            data_dir, "SCADATagID_ANL.csv"))

        # Create dummy .dt file
        with open(dummy_dt_file, 'w') as f:
            f.write("dummy file")

        try:
            result = self.service._test_13_quality_is_good(
                self.analog_tag, dummy_dt_file, 'analog', data_dir)

            self.assertGreater(result['total_readings'],
                               0, "Should have readings")
            self.logger.info(
                f"Test 1.3 Analog: {result['total_readings']} readings, status: {result['status']}")
        finally:
            shutil.rmtree(test_dir)

    def test_14_review_quality(self):
        """Test 1.4: Review File Quality - using actual L05 MBSTagID.csv data"""
        # Test 1.4 uses MBSTagID.csv directly, no need to create temp files
        # It looks for the file in the L05 data directory

        result = self.service._test_14_quality_review(
            self.mbs_tag, "dummy_review_file", self.data_dir)

        self.assertGreater(result['total_readings'], 0, "Should have readings")
        self.logger.info(
            f"Test 1.4 Review: {result['total_readings']} readings, status: {result['status']}")

    def test_21_digital_time_differences(self):
        """Test 2.1: Digital Signal Time Differences - using actual L05 data"""
        # Create temporary structure for test with _Data subdirectory
        test_dir = tempfile.mkdtemp(prefix="test_21_digital_")
        dummy_dt_file = os.path.join(test_dir, "dummy.dt")
        data_dir = os.path.join(test_dir, "_Data")
        os.makedirs(data_dir, exist_ok=True)

        # Copy the actual L05 data to the _Data directory
        shutil.copy(self.digital_csv, os.path.join(
            data_dir, "SCADATagID_DIG.csv"))

        # Create dummy .dt file
        with open(dummy_dt_file, 'w') as f:
            f.write("dummy file")

        try:
            result = self.service._test_21_time_differences(
                self.digital_tag, dummy_dt_file, 'digital', data_dir)

            self.assertGreater(result['total_readings'],
                               0, "Should have readings")
            self.assertGreaterEqual(
                result['max_time_diff'], 0, "Max time diff should be >= 0")
            self.assertGreaterEqual(
                result['mean_time_diff'], 0.0, "Mean time diff should be >= 0")
            self.logger.info(
                f"Test 2.1 Digital: {result['total_readings']} readings, Max: {result['max_time_diff']}s, Mean: {result['mean_time_diff']}s")
        finally:
            shutil.rmtree(test_dir)

    def test_21_analog_time_differences(self):
        """Test 2.1: Analog Signal Time Differences - using actual L05 data"""
        # Create temporary structure for test with _Data subdirectory
        test_dir = tempfile.mkdtemp(prefix="test_21_analog_")
        dummy_dt_file = os.path.join(test_dir, "dummy.dt")
        data_dir = os.path.join(test_dir, "_Data")
        os.makedirs(data_dir, exist_ok=True)

        # Copy the actual L05 data to the _Data directory
        shutil.copy(self.analog_csv, os.path.join(
            data_dir, "SCADATagID_ANL.csv"))

        # Create dummy .dt file
        with open(dummy_dt_file, 'w') as f:
            f.write("dummy file")

        try:
            result = self.service._test_21_time_differences(
                self.analog_tag, dummy_dt_file, 'analog', data_dir)

            self.assertGreater(result['total_readings'],
                               0, "Should have readings")
            self.assertGreaterEqual(
                result['max_time_diff'], 0, "Max time diff should be >= 0")
            self.assertGreaterEqual(
                result['mean_time_diff'], 0.0, "Mean time diff should be >= 0")
            self.logger.info(
                f"Test 2.1 Analog: {result['total_readings']} readings, Max: {result['max_time_diff']}s, Mean: {result['mean_time_diff']}s")
        finally:
            shutil.rmtree(test_dir)

    def test_22_flat_attribute(self):
        """Test 2.2: FLAT Attribute Check - using actual L05 MBSTagID.csv data"""
        # Test 2.2 uses MBSTagID.csv directly from the L05 data directory
        result = self.service._test_22_flat_attribute(
            self.mbs_tag, "dummy_review_file", 5.0, self.data_dir)

        self.assertGreater(result['total_readings'], 0, "Should have readings")
        self.assertIn(result['flat_check_status'], ['GOOD', 'BAD', 'FLAT Not Available', 'no_data'],
                      "Should have valid flat check status")
        self.logger.info(
            f"Test 2.2 FLAT: {result['total_readings']} total readings, {result['non_shutdown_readings']} non-shutdown, status: {result['flat_check_status']}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
