"""
Django management command for backing up user data.
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from automation.services.backup import backup_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create backup of user templates and data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Specific user ID to backup (if not provided, backs up all users)',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old backups after creating new ones',
        )
        parser.add_argument(
            '--keep-count',
            type=int,
            default=10,
            help='Number of recent backups to keep when cleaning up (default: 10)',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        cleanup = options.get('cleanup', False)
        keep_count = options.get('keep_count', 10)

        try:
            if user_id:
                # Backup specific user
                self.backup_user(user_id)
                if cleanup:
                    backup_service.cleanup_old_backups(user_id, keep_count)
            else:
                # Backup all users
                users = User.objects.all()
                self.stdout.write(f"Backing up {users.count()} users...")
                
                for user in users:
                    self.backup_user(user.id)
                    if cleanup:
                        backup_service.cleanup_old_backups(user.id, keep_count)

            self.stdout.write(
                self.style.SUCCESS('Backup completed successfully!')
            )
        except Exception as e:
            raise CommandError(f'Backup failed: {e}')

    def backup_user(self, user_id: int):
        """Create backup for a specific user."""
        try:
            backup_file = backup_service.create_backup(user_id)
            self.stdout.write(f"Created backup for user {user_id}: {backup_file}")
        except Exception as e:
            logger.error(f"Failed to backup user {user_id}: {e}")
            self.stdout.write(
                self.style.ERROR(f"Failed to backup user {user_id}: {e}")
            )
