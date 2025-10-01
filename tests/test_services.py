"""
Smoke tests for automation services to preserve behavior.
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from automation.services.templates import template_service
from automation.services.reporting import reporting_service
from automation.services.file_processor import file_processor
from automation.exceptions import TemplateNotFoundError, ReportGenerationError


class TestTemplateService(TestCase):
    """Test template service functionality."""
    
    def setUp(self):
        """Set up test data."""
        template_service.clear_cache()
    
    def test_template_crud_operations(self):
        """Test template create, read, update, delete operations."""
        # Create template
        template_service.save_template("test_template", "Test Subject", "Test Body")
        
        # Read template
        template = template_service.get_template("test_template")
        self.assertEqual(template["subject"], "Test Subject")
        self.assertEqual(template["body"], "Test Body")
        
        # Update template
        template_service.save_template("test_template", "Updated Subject", "Updated Body")
        updated_template = template_service.get_template("test_template")
        self.assertEqual(updated_template["subject"], "Updated Subject")
        self.assertEqual(updated_template["body"], "Updated Body")
        
        # Delete template
        template_service.delete_template("test_template")
        with self.assertRaises(TemplateNotFoundError):
            template_service.get_template("test_template")
    
    def test_template_not_found(self):
        """Test template not found error."""
        with self.assertRaises(TemplateNotFoundError):
            template_service.get_template("nonexistent")
    
    def test_render_template(self):
        """Test template rendering with context."""
        template_service.save_template("test_template", "Hello {name}", "Dear {name}, welcome!")
        
        subject, body = template_service.render_template("test_template", {"name": "John"})
        self.assertEqual(subject, "Hello John")
        self.assertEqual(body, "Dear John, welcome!")
    
    def test_export_import_templates(self):
        """Test template export and import."""
        # Create test template
        template_service.save_template("test_template", "Test Subject", "Test Body")
        
        # Export templates
        json_content = template_service.export_templates_to_json()
        self.assertIn("test_template", json_content)
        self.assertIn("Test Subject", json_content)
        
        # Clear and import
        template_service.clear_cache()
        template_service.upload_templates_from_json(json_content)
        
        # Verify import
        template = template_service.get_template("test_template")
        self.assertEqual(template["subject"], "Test Subject")
        self.assertEqual(template["body"], "Test Body")


class TestReportingService(TestCase):
    """Test reporting service functionality."""
    
    def test_generate_mail_report_bytes(self):
        """Test generating mail report as bytes."""
        results = [
            {
                "email": "test@example.com",
                "company_name": "Test Company",
                "matched_files": "test.pdf",
                "sent_with_attachments": True,
                "status": "OK",
                "error_detail": ""
            }
        ]
        
        content = reporting_service.generate_report_bytes(results)
        self.assertIsInstance(content, bytes)
        self.assertGreater(len(content), 1000)  # Basic size check
    
    def test_generate_mail_report_empty(self):
        """Test generating report with empty results."""
        with self.assertRaises(ReportGenerationError):
            reporting_service.generate_report_bytes([])
    
    def test_save_report_to_file(self):
        """Test saving report to file."""
        results = [
            {
                "email": "test@example.com",
                "status": "OK",
                "error_detail": ""
            }
        ]
        
        file_path = reporting_service.save_report_to_file(results, "test_report.xlsx")
        self.assertTrue(file_path.endswith("test_report.xlsx"))


class TestFileProcessorService(TestCase):
    """Test file processor service functionality."""
    
    def test_encode_single_file(self):
        """Test encoding a single file."""
        file_content = b"test file content"
        uploaded_file = SimpleUploadedFile("test.txt", file_content, content_type="text/plain")
        
        attachment = file_processor.encode_single_file(uploaded_file)
        
        self.assertEqual(attachment["name"], "test.txt")
        self.assertEqual(attachment["contentType"], "text/plain")
        self.assertIn("contentBytes", attachment)
        self.assertEqual(attachment["@odata.type"], "#microsoft.graph.fileAttachment")
    
    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files."""
        # Test with non-existent directory
        result = file_processor.cleanup_temp_files("/nonexistent/path")
        self.assertTrue(result)  # Should return True even if directory doesn't exist


class TestMailService(TestCase):
    """Test mail service functionality."""
    
    @patch('automation.services.mailer.acquire_token_silent_or_fail')
    @patch('automation.services.mailer.send_mail_with_attachments')
    def test_send_single_mail_with_attachments(self, mock_send, mock_token):
        """Test sending single mail with attachments."""
        from automation.services.mailer import send_single_mail
        
        mock_token.return_value = "test_token"
        mock_send.return_value = True
        
        attachments = [{"name": "test.pdf", "contentBytes": "base64content"}]
        result = send_single_mail(
            "test@example.com",
            "Test Subject",
            "Test Body",
            attachments
        )
        
        self.assertTrue(result)
        mock_send.assert_called_once()
    
    @patch('automation.services.mailer.acquire_token_silent_or_fail')
    def test_send_single_mail_auth_error(self, mock_token):
        """Test sending mail with authentication error."""
        from automation.services.mailer import send_single_mail, NeedsLoginError
        
        mock_token.side_effect = NeedsLoginError("Auth required")
        
        with self.assertRaises(NeedsLoginError):
            send_single_mail("test@example.com", "Test Subject", "Test Body")


class TestIntegration(TestCase):
    """Integration tests to ensure services work together."""
    
    def test_mail_automation_workflow(self):
        """Test complete mail automation workflow."""
        # Create template
        template_service.save_template(
            "test_template",
            "Hello {name}",
            "Dear {name}, your invoice is ready."
        )
        
        # Create test data
        test_data = [
            {"name": "John", "email": "john@example.com"},
            {"name": "Jane", "email": "jane@example.com"}
        ]
        
        # Render templates
        rendered_emails = []
        for data in test_data:
            subject, body = template_service.render_template("test_template", data)
            rendered_emails.append({
                "email": data["email"],
                "subject": subject,
                "body": body
            })
        
        # Generate report
        results = [
            {
                "email": email["email"],
                "status": "OK",
                "error_detail": ""
            }
            for email in rendered_emails
        ]
        
        report_content = reporting_service.generate_report_bytes(results)
        self.assertIsInstance(report_content, bytes)
        self.assertGreater(len(report_content), 1000)
        
        # Cleanup
        template_service.delete_template("test_template")
