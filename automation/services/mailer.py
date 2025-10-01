"""
Mail service for handling email operations.
"""
import base64
import logging
from typing import Dict, List, Optional, Any
from django.core.files.uploadedfile import UploadedFile

from ..exceptions import MailSendError
from .graph_client import (
    acquire_token_silent_or_fail,
    send_mail as graph_send_mail,
    send_mail_with_attachments,
    NeedsLoginError
)

logger = logging.getLogger(__name__)


def build_message_payload(
    to_email: str,
    subject: str,
    body: str,
    attachments: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Build Microsoft Graph message payload.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (HTML)
        attachments: List of attachment objects
        
    Returns:
        Message payload dictionary
    """
    payload = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": body},
        "toRecipients": [{"emailAddress": {"address": to_email}}],
    }
    
    if attachments:
        payload["attachments"] = attachments
        
    return payload


def encode_attachment(file_obj: UploadedFile) -> Dict[str, str]:
    """
    Encode uploaded file as Graph attachment.
    
    Args:
        file_obj: Django uploaded file object
        
    Returns:
        Graph attachment dictionary
    """
    try:
        content = file_obj.read()
        b64 = base64.b64encode(content).decode("utf-8")
        
        return {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": file_obj.name,
            "contentType": file_obj.content_type or "application/octet-stream",
            "contentBytes": b64,
        }
    except Exception as e:
        logger.error(f"Error encoding attachment {file_obj.name}: {e}")
        raise MailSendError(f"Failed to encode attachment: {e}") from e


def send_single_mail(
    to_email: str,
    subject: str,
    body: str,
    attachments: Optional[List[Dict[str, str]]] = None,
    timeout: int = 15
) -> bool:
    """
    Send a single email.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (HTML)
        attachments: List of attachment objects
        timeout: Request timeout in seconds
        
    Returns:
        True if successful
        
    Raises:
        MailSendError: If sending fails
        NeedsLoginError: If authentication is required
    """
    try:
        access_token = acquire_token_silent_or_fail()
        message_payload = build_message_payload(to_email, subject, body, attachments)
        
        if attachments:
            return send_mail_with_attachments(access_token, message_payload, attachments, timeout)
        else:
            return graph_send_mail(access_token, message_payload, timeout)
            
    except NeedsLoginError:
        raise
    except Exception as e:
        logger.error(f"Error sending mail to {to_email}: {e}")
        raise MailSendError(f"Failed to send mail: {e}") from e


def send_bulk_mails(
    mail_data: List[Dict[str, Any]],
    timeout: int = 15
) -> List[Dict[str, Any]]:
    """
    Send multiple emails and return results.
    
    Args:
        mail_data: List of mail data dictionaries
        timeout: Request timeout in seconds
        
    Returns:
        List of result dictionaries with status and error information
    """
    results = []
    
    try:
        access_token = acquire_token_silent_or_fail()
    except NeedsLoginError:
        # Return error for all mails
        for data in mail_data:
            results.append({
                "email": data.get("email", "unknown"),
                "status": "ERROR",
                "error_detail": "Authentication required"
            })
        return results
    
    for data in mail_data:
        try:
            to_email = data["email"]
            subject = data["subject"]
            body = data["body"]
            attachments = data.get("attachments", [])
            
            message_payload = build_message_payload(to_email, subject, body, attachments)
            
            if attachments:
                send_mail_with_attachments(access_token, message_payload, attachments, timeout)
            else:
                graph_send_mail(access_token, message_payload, timeout)
                
            results.append({
                "email": to_email,
                "status": "OK",
                "error_detail": ""
            })
            
        except Exception as e:
            logger.error(f"Error sending mail to {data.get('email', 'unknown')}: {e}")
            results.append({
                "email": data.get("email", "unknown"),
                "status": "ERROR",
                "error_detail": str(e)
            })
    
    return results
