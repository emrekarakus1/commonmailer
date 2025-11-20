from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .utils import load_email_templates


class SignupForm(forms.Form):
    """Simplified signup form with only email and password."""
    email = forms.EmailField(
        required=True,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'placeholder': 'your.email@example.com',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        required=True,
        label="Password",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'autocomplete': 'new-password'
        }),
        min_length=1  # Minimum 1 character, no other restrictions
    )

    def clean_email(self):
        """Validate email and check if it already exists."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        """Create user with email as username."""
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        
        # Use email as username (or create a unique username from email)
        username = email.split('@')[0]  # Use part before @ as username
        # Ensure username is unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        return user


class MailAutomationForm(forms.Form):
    excel_file = forms.FileField(required=False, help_text="Upload an .xlsx file")
    template = forms.ChoiceField(choices=[], required=True)
    attachment = forms.FileField(required=False, help_text="Upload any file to attach to all emails (PDF, DOC, ZIP, etc.)")
    dry_run = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            from .services.templates import TemplateService
            template_service = TemplateService(user_id=user.id)
            templates = template_service.get_templates()
        else:
            templates = load_email_templates()
        self.fields["template"].choices = [(k, k) for k in templates.keys()]


class TemplateEditForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    subject = forms.CharField(max_length=200, required=False)
    body = forms.CharField(widget=forms.Textarea, required=True)





