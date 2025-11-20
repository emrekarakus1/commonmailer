"""
Django management command to migrate existing templates to persistent storage.
"""
import json
import logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate existing templates to persistent storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually moving files',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        try:
            self.stdout.write("Starting migration to persistent storage...")
            
            # Create persistent directories
            persistent_path = Path(settings.DATA_STORAGE_PATH)
            user_templates_path = Path(settings.USER_TEMPLATES_PATH)
            
            if not dry_run:
                persistent_path.mkdir(parents=True, exist_ok=True)
                user_templates_path.mkdir(parents=True, exist_ok=True)
                self.stdout.write(f"Created persistent directories")
            
            # Migrate global templates
            self.migrate_global_templates(dry_run)
            
            # Migrate user templates
            self.migrate_user_templates(dry_run)
            
            # Create initial backup
            if not dry_run:
                self.create_initial_backup()
            
            self.stdout.write(
                self.style.SUCCESS('Migration completed successfully!')
            )
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('This was a dry run. Run without --dry-run to actually migrate.')
                )
                
        except Exception as e:
            raise CommandError(f'Migration failed: {e}')

    def migrate_global_templates(self, dry_run: bool):
        """Migrate global email templates."""
        source_file = Path("email_templates.json")
        target_file = Path(settings.EMAIL_TEMPLATES_PATH)
        
        if source_file.exists():
            if not dry_run:
                # Copy to persistent location
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8")
                self.stdout.write(f"Migrated global templates to: {target_file}")
            else:
                self.stdout.write(f"Would migrate global templates: {source_file} -> {target_file}")
        else:
            self.stdout.write("No global templates found to migrate")

    def migrate_user_templates(self, dry_run: bool):
        """Migrate user-specific templates."""
        user_templates_path = Path(settings.USER_TEMPLATES_PATH)
        migrated_count = 0
        
        # Look for existing user template files in root directory
        for template_file in Path(".").glob("email_templates_user_*.json"):
            if not dry_run:
                # Copy to persistent location
                target_file = user_templates_path / template_file.name
                target_file.write_text(template_file.read_text(encoding="utf-8"), encoding="utf-8")
                self.stdout.write(f"Migrated user templates: {template_file} -> {target_file}")
            else:
                target_file = user_templates_path / template_file.name
                self.stdout.write(f"Would migrate user templates: {template_file} -> {target_file}")
            
            migrated_count += 1
        
        if migrated_count == 0:
            self.stdout.write("No user template files found to migrate")
        else:
            self.stdout.write(f"Found {migrated_count} user template files")

    def create_initial_backup(self):
        """Create initial backup of migrated data."""
        from automation.services.backup import backup_service
        
        # Create backup for each user
        user_template_files = Path(settings.USER_TEMPLATES_PATH).glob("email_templates_user_*.json")
        
        for template_file in user_template_files:
            # Extract user ID from filename
            user_id_str = template_file.stem.replace("email_templates_user_", "")
            try:
                user_id = int(user_id_str)
                backup_file = backup_service.create_backup(user_id, f"migration_backup_{user_id}.json")
                self.stdout.write(f"Created migration backup for user {user_id}: {backup_file}")
            except ValueError:
                self.stdout.write(
                    self.style.WARNING(f"Could not extract user ID from filename: {template_file}")
                )
