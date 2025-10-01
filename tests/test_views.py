"""
Smoke tests for views to preserve behavior.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch, Mock
import json

from automation.services.templates import template_service


class TestViewSmokeTests(TestCase):
    """Smoke tests for views to ensure behavior is preserved."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test template
        template_service.save_template(
            "test_template",
            "Test Subject",
            "Test Body"
        )
    
    def tearDown(self):
        """Clean up test data."""
        template_service.clear_cache()
    
    def test_landing_page(self):
        """Test landing page loads correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to Portal')
    
    def test_login_page(self):
        """Test login page loads correctly."""
        self.client.logout()
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome Back')
    
    def test_signup_page(self):
        """Test signup page loads correctly."""
        self.client.logout()
        response = self.client.get('/signup/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')
    
    def test_dashboard_requires_login(self):
        """Test dashboard requires authentication."""
        self.client.logout()
        response = self.client.get('/dashboard/')
        self.assertRedirects(response, '/login/?next=/dashboard/')
    
    def test_dashboard_authenticated(self):
        """Test dashboard loads for authenticated user."""
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
    
    def test_mail_automation_requires_login(self):
        """Test mail automation requires authentication."""
        self.client.logout()
        response = self.client.get('/mail/')
        self.assertRedirects(response, '/login/?next=/mail/')
    
    def test_mail_automation_authenticated(self):
        """Test mail automation loads for authenticated user."""
        response = self.client.get('/mail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mail Automation')
    
    def test_template_manager_requires_login(self):
        """Test template manager requires authentication."""
        self.client.logout()
        response = self.client.get('/templates/')
        self.assertRedirects(response, '/login/?next=/templates/')
    
    def test_template_manager_authenticated(self):
        """Test template manager loads for authenticated user."""
        response = self.client.get('/templates/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Template Manager')
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'ok')
    
    @patch('automation.services.graph_client.device_code_start')
    def test_mail_signin_start(self, mock_device_code):
        """Test mail signin start endpoint."""
        mock_device_code.return_value = {
            'user_code': 'ABC123',
            'verification_uri': 'https://microsoft.com/devicelogin'
        }
        
        response = self.client.get('/mail/signin/start/')
        self.assertEqual(response.status_code, 200)
    
    def test_template_download(self):
        """Test template download endpoint."""
        response = self.client.get('/templates/download/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('test_template', response.content.decode())
    
    def test_template_upload(self):
        """Test template upload functionality."""
        # Create test template data
        test_templates = {
            "new_template": {
                "subject": "New Subject",
                "body": "New Body"
            }
        }
        
        # Create test file
        test_file = json.dumps(test_templates)
        
        with patch('automation.views.template_service.upload_templates_from_json') as mock_upload:
            mock_upload.return_value = None
            
            response = self.client.post('/templates/', {
                'upload_templates': '1',
                'template_file': test_file
            })
            
            # Should redirect after successful upload
            self.assertEqual(response.status_code, 302)
    
    def test_template_delete(self):
        """Test template deletion."""
        # Create a template to delete
        template_service.save_template("delete_me", "Subject", "Body")
        
        response = self.client.post('/templates/', {
            'delete_template': '1',
            'template_name': 'delete_me'
        })
        
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)
        
        # Template should be deleted
        with self.assertRaises(Exception):  # TemplateNotFoundError
            template_service.get_template("delete_me")
    
    def test_mail_automation_form_validation(self):
        """Test mail automation form validation."""
        # Test with invalid form data
        response = self.client.post('/mail/', {
            'template': 'nonexistent_template',
            'dry_run': '1'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
    
    def test_mail_automation_reset(self):
        """Test mail automation reset functionality."""
        # Set some session data
        session = self.client.session
        session['mail_excel_b64'] = 'test_data'
        session.save()
        
        # Test reset
        response = self.client.get('/mail/?reset=1')
        self.assertEqual(response.status_code, 200)
        
        # Session should be cleared
        session = self.client.session
        self.assertNotIn('mail_excel_b64', session)
    
    def test_report_download_no_data(self):
        """Test report download with no data."""
        response = self.client.get('/report/download/direct/')
        self.assertEqual(response.status_code, 404)
    
    def test_url_patterns(self):
        """Test that all URL patterns are accessible."""
        urls_to_test = [
            '/',
            '/login/',
            '/signup/',
            '/dashboard/',
            '/mail/',
            '/templates/',
            '/healthz/',
        ]
        
        for url in urls_to_test:
            response = self.client.get(url)
            # Should not return 404 (either 200, 302 redirect, or 403)
            self.assertNotEqual(response.status_code, 404, f"URL {url} returned 404")


class TestAuthenticationFlow(TestCase):
    """Test authentication flow."""
    
    def test_signup_flow(self):
        """Test user signup flow."""
        response = self.client.post('/signup/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        })
        
        # Should redirect after successful signup
        self.assertEqual(response.status_code, 302)
        
        # User should be created
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_login_flow(self):
        """Test user login flow."""
        # Create user
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Test login
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)
    
    def test_logout_flow(self):
        """Test user logout flow."""
        # Create and login user
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Test logout
        response = self.client.get('/logout/')
        
        # Should redirect after logout
        self.assertEqual(response.status_code, 302)
