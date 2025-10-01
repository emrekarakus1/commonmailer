import os
import shutil
import time
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Clean up old temporary files from upload processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Delete files older than this many hours (default: 24)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        temp_dir = getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
        if not temp_dir or not os.path.exists(temp_dir):
            self.stdout.write(
                self.style.WARNING('No temp directory configured or found')
            )
            return

        hours = options['hours']
        dry_run = options['dry_run']
        cutoff_time = time.time() - (hours * 3600)
        
        deleted_count = 0
        total_size = 0

        self.stdout.write(f"Cleaning up files older than {hours} hours...")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No files will be deleted"))

        # Walk through all subdirectories in temp directory
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_stat = os.stat(file_path)
                    if file_stat.st_mtime < cutoff_time:
                        file_size = file_stat.st_size
                        total_size += file_size
                        deleted_count += 1
                        
                        if dry_run:
                            self.stdout.write(f"Would delete: {file_path} ({file_size} bytes)")
                        else:
                            os.remove(file_path)
                            self.stdout.write(f"Deleted: {file_path}")
                            
                except OSError as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing {file_path}: {e}")
                    )

        # Remove empty directories
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):  # Directory is empty
                        if dry_run:
                            self.stdout.write(f"Would remove empty directory: {dir_path}")
                        else:
                            os.rmdir(dir_path)
                            self.stdout.write(f"Removed empty directory: {dir_path}")
                except OSError as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error removing directory {dir_path}: {e}")
                    )

        # Summary
        if deleted_count > 0:
            size_mb = total_size / (1024 * 1024)
            action = "Would delete" if dry_run else "Deleted"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} {deleted_count} files ({size_mb:.2f} MB)"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("No old files found to clean up")
            )
