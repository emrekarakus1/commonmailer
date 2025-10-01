"""
Template service for handling email templates.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import os

from ..exceptions import TemplateNotFoundError
from ..utils import load_email_templates, save_email_templates
from .template_render import render_subject_body

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing email templates."""
    
    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
        self._templates_cache: Optional[Dict[str, Dict[str, str]]] = None
    
    def get_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Get all email templates for the current user.
        
        Returns:
            Dictionary of templates with name as key and {subject, body} as value
        """
        if self._templates_cache is None:
            self._templates_cache = self._load_user_templates()
        return self._templates_cache
    
    def get_template(self, name: str) -> Dict[str, str]:
        """
        Get a specific template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template dictionary with subject and body
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        templates = self.get_templates()
        if name not in templates:
            raise TemplateNotFoundError(f"Template '{name}' not found")
        return templates[name]
    
    def save_template(self, name: str, subject: str, body: str) -> None:
        """
        Save or update a template for the current user.
        
        Args:
            name: Template name
            subject: Email subject template
            body: Email body template
        """
        templates = self.get_templates()
        templates[name] = {"subject": subject, "body": body}
        self._save_user_templates(templates)
        # Update cache
        self._templates_cache = templates
        logger.info(f"Template '{name}' saved for user {self.user_id}")
    
    def delete_template(self, name: str) -> None:
        """
        Delete a template.
        
        Args:
            name: Template name
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        templates = self.get_templates()
        if name not in templates:
            raise TemplateNotFoundError(f"Template '{name}' not found")
        
        del templates[name]
        self._save_user_templates(templates)
        self._templates_cache = templates
        logger.info(f"Template '{name}' deleted for user {self.user_id}")
    
    def _load_user_templates(self) -> Dict[str, Dict[str, str]]:
        """Load templates for the current user."""
        if not self.user_id:
            return {}
        
        user_templates_file = Path(f"email_templates_user_{self.user_id}.json")
        if not user_templates_file.exists():
            return {}
        
        try:
            with open(user_templates_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Normalize to {subject, body} format
            normalized: Dict[str, Dict[str, str]] = {}
            for name, value in data.items():
                if isinstance(value, dict):
                    subject = str(value.get("subject", ""))
                    body = str(value.get("body", ""))
                else:  # Legacy format
                    subject = ""
                    body = str(value)
                normalized[str(name)] = {"subject": subject, "body": body}
            
            return normalized
        except Exception as e:
            logger.error(f"Error loading user templates for user {self.user_id}: {e}")
            return {}
    
    def _save_user_templates(self, templates: Dict[str, Dict[str, str]]) -> None:
        """Save templates for the current user."""
        if not self.user_id:
            return
        
        user_templates_file = Path(f"email_templates_user_{self.user_id}.json")
        try:
            with open(user_templates_file, "w", encoding="utf-8") as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving user templates for user {self.user_id}: {e}")
            raise
    
    def render_template(self, name: str, context: Dict[str, Any]) -> tuple[str, str]:
        """
        Render a template with the given context.
        
        Args:
            name: Template name
            context: Context data for rendering
            
        Returns:
            Tuple of (rendered_subject, rendered_body)
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        template = self.get_template(name)
        return render_subject_body(template["subject"], template["body"], context)
    
    def upload_templates_from_json(self, json_content: str) -> None:
        """
        Upload templates from JSON content.
        
        Args:
            json_content: JSON string containing templates
        """
        try:
            new_templates = json.loads(json_content)
            templates = self.get_templates()
            templates.update(new_templates)
            self._save_user_templates(templates)
            self._templates_cache = templates
            logger.info(f"Uploaded {len(new_templates)} templates")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON content: {e}") from e
    
    def export_templates_to_json(self) -> str:
        """
        Export all templates as JSON string.
        
        Returns:
            JSON string containing all templates
        """
        templates = self.get_templates()
        return json.dumps(templates, indent=2, ensure_ascii=False)
    
    def clear_cache(self) -> None:
        """Clear the templates cache."""
        self._templates_cache = None


# Global instance - will be replaced with user-specific instances
template_service = TemplateService()
