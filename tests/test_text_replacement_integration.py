"""
Integration tests for text replacement functionality.
Tests the complete workflow from UI to service layer.
"""

import unittest
import tempfile
import base64
import os
from pathlib import Path
from core.dependency_injection import configure_services
from controllers.text_replacement_controller import TextReplacementUIResponseFormatter


class TestTextReplacementIntegration(unittest.TestCase):
    """Integration tests for text replacement workflow."""

    def setUp(self):
        """Set up test fixtures."""
        # Configure DI container
        self.container = configure_services()

        # Create temporary directory with test files
        self.temp_dir = tempfile.mkdtemp()

        # Create test files with content to replace
        test_files = {
            'test1.txt': 'This is old_text in file 1. More old_text here.',
            'test2.py': 'def function():\n    return "old_text"',
            'test3.js': 'const value = "old_text"; // old_text comment',
            'ignored.cpp': 'This old_text should not be changed'  # Wrong extension
        }

        for filename, content in test_files.items():
            (Path(self.temp_dir) / filename).write_text(content, encoding='utf-8')

        # Create CSV content
        csv_content = "old_text,new_text\nother_old,other_new\n"
        self.encoded_csv = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')
        self.csv_contents = f"data:text/csv;base64,{self.encoded_csv}"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_workflow_success(self):
        """Test complete text replacement workflow."""
        # Get controller from DI container
        controller = self.container.resolve("text_replacement_controller")

        # Step 1: Handle CSV upload
        upload_result = controller.handle_csv_upload(
            self.csv_contents, "test.csv")

        self.assertTrue(upload_result.success,
                        f"CSV upload failed: {upload_result.error}")
        self.assertEqual(upload_result.data['substitution_count'], 2)

        # Step 2: Handle text replacement
        csv_data = {'content': self.encoded_csv}
        extensions = "txt,py,js"

        replacement_result = controller.handle_text_replacement(
            self.temp_dir, csv_data, extensions, True
        )

        self.assertTrue(replacement_result.success,
                        f"Text replacement failed: {replacement_result.error}")

        # Verify results
        data = replacement_result.data
        self.assertEqual(data['processed_files'], 3)  # Only txt, py, js files
        self.assertEqual(data['total_files'], 3)
        self.assertEqual(len(data['errors']), 0)

        # Step 3: Verify file contents were changed
        test1_content = (Path(self.temp_dir) / 'test1.txt').read_text()
        self.assertIn('new_text', test1_content)
        self.assertNotIn('old_text', test1_content)

        test2_content = (Path(self.temp_dir) / 'test2.py').read_text()
        self.assertIn('new_text', test2_content)
        self.assertNotIn('old_text', test2_content)

        test3_content = (Path(self.temp_dir) / 'test3.js').read_text()
        self.assertIn('new_text', test3_content)
        self.assertNotIn('old_text', test3_content)

        # Step 4: Verify ignored file was not changed
        ignored_content = (Path(self.temp_dir) / 'ignored.cpp').read_text()
        # Should still contain old text
        self.assertIn('old_text', ignored_content)

    def test_workflow_with_case_insensitive(self):
        """Test workflow with case-insensitive replacement."""
        # Create file with mixed case
        test_file = Path(self.temp_dir) / 'mixed_case.txt'
        test_file.write_text('OLD_TEXT and old_text and Old_Text')

        # Create CSV with case replacement
        csv_content = "old_text,REPLACED\n"
        encoded_csv = base64.b64encode(
            csv_content.encode('utf-8')).decode('utf-8')

        controller = self.container.resolve("text_replacement_controller")

        csv_data = {'content': encoded_csv}

        # Case-insensitive replacement
        result = controller.handle_text_replacement(
            self.temp_dir, csv_data, "txt", False  # match_case=False
        )

        self.assertTrue(result.success)

        # Verify all variations were replaced
        content = test_file.read_text()
        self.assertEqual(content, 'REPLACED and REPLACED and REPLACED')

    def test_workflow_with_errors(self):
        """Test workflow handling files with errors."""
        # Create a file with restricted permissions (if possible)
        restricted_file = Path(self.temp_dir) / 'restricted.txt'
        restricted_file.write_text('old_text')

        # Try to make it read-only (best effort - may not work on all systems)
        try:
            restricted_file.chmod(0o444)
        except:
            pass  # Skip if can't change permissions

        controller = self.container.resolve("text_replacement_controller")
        csv_data = {'content': self.encoded_csv}

        result = controller.handle_text_replacement(
            self.temp_dir, csv_data, "txt", True
        )

        # Should still succeed overall even if some files fail
        self.assertTrue(result.success)

    def test_ui_response_formatting(self):
        """Test UI response formatting integration."""
        controller = self.container.resolve("text_replacement_controller")
        formatter = TextReplacementUIResponseFormatter()

        # Test CSV upload formatting
        upload_result = controller.handle_csv_upload(
            self.csv_contents, "test.csv")
        csv_data, status = formatter.format_csv_upload_response(upload_result)

        self.assertEqual(status['type'], 'success')
        self.assertEqual(status['filename'], 'test.csv')
        self.assertEqual(status['substitution_count'], 2)

        # Test replacement formatting
        csv_data = {'content': self.encoded_csv}
        replacement_result = controller.handle_text_replacement(
            self.temp_dir, csv_data, "txt,py,js", True
        )

        notification = formatter.format_replacement_response(
            replacement_result)

        self.assertEqual(notification['type'], 'success')
        self.assertEqual(notification['title'], 'Completed Successfully')
        self.assertIn('processed_files', notification['details'])

    def test_dependency_injection_configuration(self):
        """Test that all services are properly configured in DI container."""
        # Verify all required services are registered
        text_replacer = self.container.resolve("text_replacer")
        self.assertIsNotNone(text_replacer)

        substitution_loader = self.container.resolve("substitution_loader")
        self.assertIsNotNone(substitution_loader)

        file_processor = self.container.resolve("file_processor")
        self.assertIsNotNone(file_processor)

        text_replacement_service = self.container.resolve(
            "text_replacement_service")
        self.assertIsNotNone(text_replacement_service)

        controller = self.container.resolve("text_replacement_controller")
        self.assertIsNotNone(controller)

        # Verify validators are registered
        csv_validator = self.container.resolve("csv_validator")
        self.assertIsNotNone(csv_validator)

        directory_validator = self.container.resolve("directory_validator")
        self.assertIsNotNone(directory_validator)

        extensions_validator = self.container.resolve("extensions_validator")
        self.assertIsNotNone(extensions_validator)

    def test_backwards_compatibility_with_legacy_service(self):
        """Test that legacy service wrapper still works."""
        from services.text_replacement_service_v2 import LegacyTextReplacementService

        # Create temporary CSV file
        csv_file = Path(self.temp_dir) / 'substitutions.csv'
        csv_file.write_text('old_text,new_text\n')

        # Create test file
        test_file = Path(self.temp_dir) / 'legacy_test.txt'
        test_file.write_text('This contains old_text')

        # Use legacy service
        legacy_service = LegacyTextReplacementService()
        legacy_service.set_csv_file(str(csv_file))
        legacy_service.set_folder_path(self.temp_dir)

        # Should not raise exception
        legacy_service.replace_in_files(['txt'], True)

        # Verify replacement worked
        content = test_file.read_text()
        self.assertIn('new_text', content)
        self.assertNotIn('old_text', content)


if __name__ == '__main__':
    unittest.main()
