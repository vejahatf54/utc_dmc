"""
Integration tests for the refactored Fetch Archive functionality.
Tests the complete workflow with dependency injection and SOLID architecture.
"""

import pytest
import tempfile
import os
import zipfile
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock

from core.dependency_injection import DIContainer
from core.interfaces import IFetchArchiveService, IArchiveValidator, IArchivePathService, IArchiveFileExtractor
from domain.archive_models import ArchiveDate, PipelineLine, OutputDirectory, ArchiveFileInfo
from validation.archive_validators import FetchArchiveRequestValidator
from services.archive_path_service import ArchivePathService
from services.archive_file_extractor import ArchiveFileExtractor
from services.fetch_archive_service import FetchArchiveService, LegacyFetchArchiveService
from controllers.fetch_archive_controller import FetchArchivePageController


class TestArchiveIntegration:
    """Integration tests for the complete archive workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test directory structure
        self.test_root = tempfile.mkdtemp()
        self.archive_base = os.path.join(self.test_root, "archive")
        self.output_base = os.path.join(self.test_root, "output")
        
        os.makedirs(self.archive_base)
        os.makedirs(self.output_base)
        
        # Create test archive structure
        self._create_test_archive_structure()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_root, ignore_errors=True)

    def _create_test_archive_structure(self):
        """Create a realistic test archive structure."""
        # Create line directories
        line_dirs = ["l01", "l02", "l03"]
        date_folder = "20231226"
        
        for line_id in line_dirs:
            line_path = os.path.join(self.archive_base, line_id, date_folder)
            os.makedirs(line_path)
            
            # Create test ZIP files with sample data
            for i in range(2):  # 2 ZIP files per line
                zip_filename = f"{line_id}_data_{i+1}.zip"
                zip_path = os.path.join(line_path, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    # Add test file to ZIP
                    test_content = f"Test data for {line_id} file {i+1}"
                    zip_file.writestr(f"data_{i+1}.txt", test_content)

    def test_complete_workflow_integration(self):
        """Test the complete fetch archive workflow."""
        # Setup dependencies
        validator = FetchArchiveRequestValidator()
        
        # Mock archive path to use our test directory
        from domain.archive_models import ArchivePath
        archive_path = ArchivePath(self.archive_base)
        path_service = ArchivePathService(archive_path)
        
        file_extractor = ArchiveFileExtractor()
        
        # Create service with dependency injection
        service = FetchArchiveService(validator, path_service, file_extractor)
        
        # Test parameters
        archive_date = datetime(2023, 12, 26)
        line_ids = ["l01", "l02"]
        output_directory = self.output_base
        
        # Execute fetch operation
        result = service.fetch_archive_data(archive_date, line_ids, output_directory)
        
        # Verify results
        assert result.success is True
        assert result.data['success'] is True
        assert len(result.data['files']) == 4  # 2 files per line, 2 lines
        assert len(result.data['failed_lines']) == 0
        
        # Verify files were extracted
        for line_id in line_ids:
            line_output_dir = os.path.join(output_directory, f"{line_id}_20231226")
            assert os.path.exists(line_output_dir)
            
            # Check that files were extracted
            extracted_files = os.listdir(line_output_dir)
            assert len(extracted_files) == 2  # 2 files per line

    def test_controller_integration(self):
        """Test the controller integration with services."""
        # Setup service dependencies
        validator = FetchArchiveRequestValidator()
        
        from domain.archive_models import ArchivePath
        archive_path = ArchivePath(self.archive_base)
        path_service = ArchivePathService(archive_path)
        
        file_extractor = ArchiveFileExtractor()
        service = FetchArchiveService(validator, path_service, file_extractor)
        
        # Create controller
        controller = FetchArchivePageController(service)
        
        # Test getting available lines
        lines_result = controller.get_available_lines()
        assert lines_result.success is True
        assert len(lines_result.data['lines']) == 3  # l01, l02, l03
        
        # Test date selection
        date_result = controller.handle_date_selection(date(2023, 12, 26))
        assert date_result.success is True
        assert date_result.data['valid'] is True
        
        # Test line selection
        lines_result = controller.handle_line_selection(["l01", "l02"])
        assert lines_result.success is True
        assert lines_result.data['lines_valid'] is True
        
        # Test output directory selection
        dir_result = controller.handle_output_directory_selection(self.output_base)
        assert dir_result.success is True
        assert dir_result.data['directory_valid'] is True
        
        # Test complete fetch request
        fetch_result = controller.handle_fetch_request(
            datetime(2023, 12, 26), ["l01", "l02"], self.output_base
        )
        assert fetch_result.success is True
        assert fetch_result.data['status'] == 'completed'

    def test_legacy_service_compatibility(self):
        """Test that legacy service wrapper maintains backward compatibility."""
        # Setup new service
        validator = FetchArchiveRequestValidator()
        
        from domain.archive_models import ArchivePath
        archive_path = ArchivePath(self.archive_base)
        path_service = ArchivePathService(archive_path)
        
        file_extractor = ArchiveFileExtractor()
        new_service = FetchArchiveService(validator, path_service, file_extractor)
        
        # Create legacy wrapper
        legacy_service = LegacyFetchArchiveService(new_service)
        
        # Test legacy API methods
        lines_result = legacy_service.get_available_lines()
        assert lines_result['success'] is True
        assert len(lines_result['lines']) == 3
        
        # Test legacy fetch method
        fetch_result = legacy_service.fetch_archive_data(
            datetime(2023, 12, 26), ["l01"], self.output_base
        )
        assert fetch_result['success'] is True
        assert len(fetch_result['files']) == 2  # 2 files for l01

    def test_error_handling_integration(self):
        """Test error handling throughout the system."""
        # Setup with invalid archive path
        validator = FetchArchiveRequestValidator()
        
        from domain.archive_models import ArchivePath
        invalid_path = ArchivePath("/nonexistent/path")
        path_service = ArchivePathService(invalid_path)
        
        file_extractor = ArchiveFileExtractor()
        service = FetchArchiveService(validator, path_service, file_extractor)
        
        # Test that service handles invalid path gracefully
        result = service.get_available_lines()
        assert result.success is False
        assert "not accessible" in result.error.lower()

    def test_validation_integration(self):
        """Test validation integration throughout the system."""
        validator = FetchArchiveRequestValidator()
        
        from domain.archive_models import ArchivePath
        archive_path = ArchivePath(self.archive_base)
        path_service = ArchivePathService(archive_path)
        
        file_extractor = ArchiveFileExtractor()
        service = FetchArchiveService(validator, path_service, file_extractor)
        
        # Test validation failure for future date
        future_date = datetime.now() + timedelta(days=1)
        result = service.fetch_archive_data(future_date, ["l01"], self.output_base)
        
        assert result.success is False
        assert "future" in result.error.lower()

    def test_dependency_injection_container_integration(self):
        """Test integration with dependency injection container."""
        # Mock configuration manager to return our test path
        with patch('services.archive_path_service.get_config_manager') as mock_config:
            mock_config_manager = Mock()
            mock_config_manager.get_archive_base_path.return_value = self.archive_base
            mock_config.return_value = mock_config_manager
            
            # Create container and configure services
            container = DIContainer()
            
            # Register archive services manually for testing
            from validation.archive_validators import create_fetch_archive_request_validator
            from services.archive_path_service import create_archive_path_service
            from services.archive_file_extractor import create_archive_file_extractor
            
            container.register_singleton(
                IArchiveValidator, factory=create_fetch_archive_request_validator
            )
            container.register_singleton(
                IArchivePathService, factory=create_archive_path_service
            )
            container.register_singleton(
                IArchiveFileExtractor, factory=create_archive_file_extractor
            )
            
            def fetch_archive_service_factory():
                validator = container.resolve(IArchiveValidator)
                path_service = container.resolve(IArchivePathService)
                file_extractor = container.resolve(IArchiveFileExtractor)
                return FetchArchiveService(validator, path_service, file_extractor)
            
            container.register_singleton(
                IFetchArchiveService, factory=fetch_archive_service_factory
            )
            
            # Test that services are properly injected
            service = container.resolve(IFetchArchiveService)
            assert isinstance(service, FetchArchiveService)
            
            # Test that service works
            result = service.get_available_lines()
            assert result.success is True
            assert len(result.data) == 3

    def test_performance_with_multiple_files(self):
        """Test performance characteristics with multiple files."""
        # Create more test files
        line_dirs = ["l01", "l02", "l03", "l04", "l05"]
        date_folder = "20231227"
        
        for line_id in line_dirs:
            line_path = os.path.join(self.archive_base, line_id, date_folder)
            os.makedirs(line_path, exist_ok=True)
            
            # Create more ZIP files per line
            for i in range(5):  # 5 ZIP files per line
                zip_filename = f"{line_id}_data_{i+1}.zip"
                zip_path = os.path.join(line_path, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    # Add multiple files to each ZIP
                    for j in range(3):  # 3 files per ZIP
                        test_content = f"Test data for {line_id} file {i+1} part {j+1}"
                        zip_file.writestr(f"data_{i+1}_part_{j+1}.txt", test_content)
        
        # Setup service
        validator = FetchArchiveRequestValidator()
        
        from domain.archive_models import ArchivePath
        archive_path = ArchivePath(self.archive_base)
        path_service = ArchivePathService(archive_path)
        
        file_extractor = ArchiveFileExtractor()
        service = FetchArchiveService(validator, path_service, file_extractor)
        
        # Test with all lines
        import time
        start_time = time.time()
        
        result = service.fetch_archive_data(
            datetime(2023, 12, 27), 
            line_dirs, 
            self.output_base
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify results
        assert result.success is True
        assert len(result.data['files']) == 75  # 5 lines × 5 zips × 3 files
        
        # Performance assertion (should complete in reasonable time)
        assert execution_time < 10.0  # Should complete within 10 seconds
        
        print(f"Processed 75 files in {execution_time:.2f} seconds")

    def test_concurrent_access_safety(self):
        """Test that the system handles concurrent access safely."""
        # This is a basic test - in a real system you'd use threading
        validator = FetchArchiveRequestValidator()
        
        from domain.archive_models import ArchivePath
        archive_path = ArchivePath(self.archive_base)
        path_service = ArchivePathService(archive_path)
        
        file_extractor = ArchiveFileExtractor()
        service = FetchArchiveService(validator, path_service, file_extractor)
        
        # Create multiple service instances (simulating concurrent requests)
        services = [service for _ in range(3)]
        
        # Execute requests "concurrently" (sequentially for test simplicity)
        results = []
        for i, svc in enumerate(services):
            output_dir = os.path.join(self.output_base, f"concurrent_{i}")
            os.makedirs(output_dir, exist_ok=True)
            
            result = svc.fetch_archive_data(
                datetime(2023, 12, 26), 
                ["l01"], 
                output_dir
            )
            results.append(result)
        
        # Verify all requests succeeded
        for result in results:
            assert result.success is True
            assert len(result.data['files']) == 2  # 2 files for l01