"""
Backup service for user templates and data.
"""
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class BackupService:
    """Service for backing up user templates and data."""
    
    def __init__(self):
        self.backup_path = Path(settings.DATA_STORAGE_PATH) / "backups"
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, user_id: int, backup_name: Optional[str] = None) -> str:
        """
        Create a backup of user templates.
        
        Args:
            user_id: User ID to backup
            backup_name: Optional custom backup name
            
        Returns:
            Path to the created backup file
        """
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"user_{user_id}_backup_{timestamp}.json"
        
        backup_file = self.backup_path / backup_name
        
        # Get user templates
        user_templates_file = Path(settings.USER_TEMPLATES_PATH) / f"email_templates_user_{user_id}.json"
        
        backup_data = {
            "user_id": user_id,
            "backup_date": datetime.now().isoformat(),
            "templates": {}
        }
        
        if user_templates_file.exists():
            try:
                with open(user_templates_file, "r", encoding="utf-8") as f:
                    backup_data["templates"] = json.load(f)
            except Exception as e:
                logger.error(f"Error reading user templates for backup: {e}")
                backup_data["templates"] = {}
        
        try:
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created backup for user {user_id}: {backup_file}")
            return str(backup_file)
        except Exception as e:
            logger.error(f"Error creating backup for user {user_id}: {e}")
            raise
    
    def restore_backup(self, backup_file: str, user_id: int) -> bool:
        """
        Restore user templates from backup.
        
        Args:
            backup_file: Path to backup file
            user_id: User ID to restore to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(backup_file, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            
            templates = backup_data.get("templates", {})
            
            # Save templates to user file
            user_templates_file = Path(settings.USER_TEMPLATES_PATH) / f"email_templates_user_{user_id}.json"
            user_templates_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(user_templates_file, "w", encoding="utf-8") as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Restored backup for user {user_id}: {len(templates)} templates")
            return True
        except Exception as e:
            logger.error(f"Error restoring backup for user {user_id}: {e}")
            return False
    
    def list_backups(self, user_id: Optional[int] = None) -> List[Dict]:
        """
        List available backups.
        
        Args:
            user_id: Optional user ID to filter backups
            
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        for backup_file in self.backup_path.glob("*.json"):
            try:
                with open(backup_file, "r", encoding="utf-8") as f:
                    backup_data = json.load(f)
                
                backup_user_id = backup_data.get("user_id")
                
                # Filter by user_id if specified
                if user_id is not None and backup_user_id != user_id:
                    continue
                
                backups.append({
                    "file": str(backup_file),
                    "user_id": backup_user_id,
                    "backup_date": backup_data.get("backup_date"),
                    "template_count": len(backup_data.get("templates", {})),
                    "file_size": backup_file.stat().st_size
                })
            except Exception as e:
                logger.error(f"Error reading backup file {backup_file}: {e}")
                continue
        
        # Sort by backup date (newest first)
        backups.sort(key=lambda x: x["backup_date"], reverse=True)
        return backups
    
    def delete_backup(self, backup_file: str) -> bool:
        """
        Delete a backup file.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            Path(backup_file).unlink()
            logger.info(f"Deleted backup: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Error deleting backup {backup_file}: {e}")
            return False
    
    def cleanup_old_backups(self, user_id: int, keep_count: int = 10) -> int:
        """
        Clean up old backups, keeping only the specified number of recent ones.
        
        Args:
            user_id: User ID to clean up backups for
            keep_count: Number of recent backups to keep
            
        Returns:
            Number of backups deleted
        """
        user_backups = self.list_backups(user_id)
        
        if len(user_backups) <= keep_count:
            return 0
        
        # Keep the most recent backups, delete the rest
        backups_to_delete = user_backups[keep_count:]
        deleted_count = 0
        
        for backup in backups_to_delete:
            if self.delete_backup(backup["file"]):
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old backups for user {user_id}")
        return deleted_count
    
    def export_all_user_data(self, user_id: int) -> Dict:
        """
        Export all user data (templates, etc.) for migration purposes.
        
        Args:
            user_id: User ID to export data for
            
        Returns:
            Dictionary containing all user data
        """
        export_data = {
            "user_id": user_id,
            "export_date": datetime.now().isoformat(),
            "templates": {},
            "backups": []
        }
        
        # Export templates
        user_templates_file = Path(settings.USER_TEMPLATES_PATH) / f"email_templates_user_{user_id}.json"
        if user_templates_file.exists():
            try:
                with open(user_templates_file, "r", encoding="utf-8") as f:
                    export_data["templates"] = json.load(f)
            except Exception as e:
                logger.error(f"Error reading templates for export: {e}")
        
        # Export backup information
        export_data["backups"] = self.list_backups(user_id)
        
        return export_data


# Global backup service instance
backup_service = BackupService()
