from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .utils import load_email_templates


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label="First Name")
    last_name = forms.CharField(max_length=30, required=True, label="Last Name")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user


class MailAutomationForm(forms.Form):
    excel_file = forms.FileField(required=False, help_text="Upload an .xlsx file")
    template = forms.ChoiceField(choices=[], required=True)
    attachment = forms.FileField(required=False, help_text="Upload any file to attach to all emails (PDF, DOC, ZIP, etc.)")
    dry_run = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        templates = load_email_templates()
        self.fields["template"].choices = [(k, k) for k in templates.keys()]


class TemplateEditForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    subject = forms.CharField(max_length=200, required=False)
    body = forms.CharField(widget=forms.Textarea, required=True)


class TemplateUploadForm(forms.Form):
    json_file = forms.FileField(required=True, help_text="Upload a JSON file with templates")



