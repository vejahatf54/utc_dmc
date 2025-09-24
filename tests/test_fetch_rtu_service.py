"""
Unit tests for RTU Fetch Data service implementation.
Tests the new service with clean architecture patterns.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import tempfile
import os
import zipfile

from services.fetch_rtu_data_service import FetchRtuDataServiceV2, RtuLineProvider, RtuDataProcessor
from domain.rtu_models import RtuDateRange, RtuLineSelection, RtuOutputDirectory, RtuServerFilter
from core.interfaces import Result


class TestRtuLineProvider(unittest.TestCase):
    """Test RTU line provider implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.provider = RtuLineProvider()

    def test_get_available_lines_success(self):
        """Test getting available lines successfully."""
        with patch('os.listdir') as mock_listdir, \
             patch('os.path.isdir') as mock_isdir, \
             patch('os.path.exists') as mock_exists:
            
            mock_exists.return_value = True
            mock_listdir.return_value = ['l01', 'l02', 'l03']
            mock_isdir.return_value = True
            
            result = self.provider.get_lines()
            
            self.assertTrue(result.success)
            self.assertEqual(len(result.data), 3)
            self.assertEqual(result.data[0]['value'], 'l01')
            self.assertEqual(result.data[1]['value'], 'l02')

    def test_get_available_lines_failure(self):
        """Test handling failure when getting lines."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            result = self.provider.get_lines()
            
            self.assertFalse(result.success)
            self.assertIn('not accessible', result.error)


class TestRtuDataProcessor(unittest.TestCase):
    """Test RTU data processor implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = RtuDataProcessor()

    def test_process_multiple_files_success(self):
        """Test processing multiple files successfully."""
        test_files = [
            {
                'source_path': '/test/file1.zip',
                'filename': 'file1.zip',
                'date_str': '20240101',
                'line_id': 'l01',
                'server': 'TEST01'
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock zip file with actual content
            test_zip_path = os.path.join(temp_dir, 'file1.zip')
            with zipfile.ZipFile(test_zip_path, 'w') as zf:
                zf.writestr('test.dt', b'sample dt file content')
            
            # Update the test file path to point to the real zip
            test_files[0]['source_path'] = test_zip_path
            
            result = self.processor.process_multiple_files(test_files, temp_dir, max_workers=1)
            
            self.assertTrue(result.success)
            self.assertIn('extracted_files', result.data)  # Updated expected key
            self.assertIn('l01', result.data['extracted_files'])

    def test_process_multiple_files_with_errors(self):
        """Test processing with some errors."""
        test_files = [
            {
                'source_path': '/test/invalid.zip',
                'filename': 'invalid.zip',
                'date_str': '20240101',
                'line_id': 'l01',
                'server': 'TEST01'
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('zipfile.ZipFile') as mock_zipfile:
                # Mock zip file to raise an exception
                mock_zipfile.side_effect = zipfile.BadZipFile("Invalid zip file")
                
                result = self.processor.process_multiple_files(test_files, temp_dir, max_workers=1)
                
                self.assertTrue(result.success)  # Should handle errors gracefully
                self.assertIn('extraction_errors', result.data)

    def test_process_multiple_files_failure(self):
        """Test processing failure."""
        test_files = []  # Empty file list
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.processor.process_multiple_files(test_files, temp_dir, max_workers=1)
            
            self.assertFalse(result.success)
            self.assertIn('No files to process', result.error)


class TestFetchRtuDataServiceV2(unittest.TestCase):
    """Test main fetch RTU data service."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_line_provider = Mock()
        self.mock_data_processor = Mock()
        self.service = FetchRtuDataServiceV2(self.mock_line_provider, self.mock_data_processor)

    def test_get_available_lines(self):
        """Test getting available lines."""
        self.mock_line_provider.get_lines.return_value = Result.ok([{'label': 'l01', 'value': 'l01'}, {'label': 'l02', 'value': 'l02'}])
        
        result = self.service.get_available_lines()
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)
        self.mock_line_provider.get_lines.assert_called_once()

    def test_fetch_rtu_data_success(self):
        """Test successful RTU data fetch."""
        date_range = RtuDateRange(date(2024, 1, 1), date(2024, 1, 3))
        line_selection = RtuLineSelection(['l01'])
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = RtuOutputDirectory(temp_dir)
            server_filter = RtuServerFilter(None)
            
            # Mock the internal methods
            with patch.object(self.service, 'validate_data_source_availability') as mock_validate, \
                 patch.object(self.service, '_get_source_files') as mock_get_files:
                
                mock_validate.return_value = Result.ok(True, "Data source accessible")
                mock_get_files.return_value = Result.ok({
                    'source_files': [{'test': 'file'}],
                    'missing_dates': []
                })
                
                # Mock successful processing with correct data structure
                mock_processing_data = {
                    'lines_processed': 1,
                    'total_files_extracted': 1,
                    'extracted_files': {'l01': ['file1.dt']},
                    'extraction_errors': []
                }
                self.mock_data_processor.process_multiple_files.return_value = Result.ok(mock_processing_data)

                result = self.service.fetch_rtu_data(
                    line_selection, date_range, output_dir, server_filter, max_parallel_workers=2
                )

                self.assertTrue(result.success)
                self.mock_data_processor.process_multiple_files.assert_called_once()

    def test_fetch_rtu_data_failure(self):
        """Test RTU data fetch failure."""
        date_range = RtuDateRange(date(2024, 1, 1), date(2024, 1, 3))
        line_selection = RtuLineSelection(['l01'])
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = RtuOutputDirectory(temp_dir)
            server_filter = RtuServerFilter(None)
            
            # Mock data source availability failure
            with patch.object(self.service, 'validate_data_source_availability') as mock_validate:
                mock_validate.return_value = Result.ok(False, "Data source not accessible")

                result = self.service.fetch_rtu_data(
                    line_selection, date_range, output_dir, server_filter, max_parallel_workers=2
                )

                self.assertFalse(result.success)
                self.assertIn('Data source not accessible', result.error)  # Match actual error message

    def test_get_system_info(self):
        """Test getting system information."""
        result = self.service.get_system_info()
        
        self.assertTrue(result.success)
        self.assertIn('zip_file_pattern', result.data)
        self.assertIn('dt_file_extension', result.data)
        self.assertIn('default_max_parallel_workers', result.data)


if __name__ == '__main__':
    unittest.main()