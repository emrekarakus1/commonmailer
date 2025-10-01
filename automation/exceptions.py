"""
Custom exceptions for the automation module.
"""


class AutomationError(Exception):
    """Base exception for automation module."""
    pass


class MailSendError(AutomationError):
    """Raised when mail sending fails."""
    pass


class TemplateNotFoundError(AutomationError):
    """Raised when a template is not found."""
    pass


class FileProcessingError(AutomationError):
    """Raised when file processing fails."""
    pass


class ReportGenerationError(AutomationError):
    """Raised when report generation fails."""
    pass
