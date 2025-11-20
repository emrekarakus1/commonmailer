"""
Django management command to check storage configuration and data persistence.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Check storage configuration and data persistence'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Storage Configuration Check ===\n'))
        
        # Check paths
        self.stdout.write('1. Storage Paths:')
        self.stdout.write(f'   DATA_STORAGE_PATH: {settings.DATA_STORAGE_PATH}')
        self.stdout.write(f'   USER_TEMPLATES_PATH: {settings.USER_TEMPLATES_PATH}')
        self.stdout.write(f'   EMAIL_TEMPLATES_PATH: {settings.EMAIL_TEMPLATES_PATH}')
        
        # Check if paths exist
        self.stdout.write('\n2. Path Existence:')
        data_path = Path(settings.DATA_STORAGE_PATH)
        user_templates_path = Path(settings.USER_TEMPLATES_PATH)
        
        self.stdout.write(f'   DATA_STORAGE_PATH exists: {data_path.exists()}')
        self.stdout.write(f'   USER_TEMPLATES_PATH exists: {user_templates_path.exists()}')
        
        # Check if writable
        self.stdout.write('\n3. Write Permissions:')
        try:
            test_file = data_path / '.test_write'
            test_file.write_text('test')
            test_file.unlink()
            self.stdout.write(self.style.SUCCESS('   ✅ DATA_STORAGE_PATH is writable'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ DATA_STORAGE_PATH is NOT writable: {e}'))
        
        # Check user templates
        self.stdout.write('\n4. User Templates:')
        if user_templates_path.exists():
            template_files = list(user_templates_path.glob('email_templates_user_*.json'))
            self.stdout.write(f'   Found {len(template_files)} user template files')
            
            for template_file in template_files[:10]:  # Show first 10
                user_id = template_file.stem.split('_')[-1]
                try:
                    user = User.objects.get(id=int(user_id))
                    size = template_file.stat().st_size
                    self.stdout.write(f'   - User {user_id} ({user.email}): {size} bytes')
                except User.DoesNotExist:
                    self.stdout.write(f'   - User {user_id} (deleted user): {template_file.stat().st_size} bytes')
        else:
            self.stdout.write(self.style.WARNING('   ⚠️  USER_TEMPLATES_PATH does not exist'))
        
        # Check database
        self.stdout.write('\n5. Database:')
        user_count = User.objects.count()
        self.stdout.write(f'   Total users in database: {user_count}')
        
        # Check Render environment
        self.stdout.write('\n6. Environment:')
        is_render = os.getenv('RENDER', '').lower() == 'true'
        self.stdout.write(f'   Running on Render: {is_render}')
        
        if is_render:
            persistent_path = os.getenv('DATA_STORAGE_PATH', '')
            if persistent_path.startswith('/app/persistent_data'):
                self.stdout.write(self.style.SUCCESS('   ✅ Using persistent volume path'))
            else:
                self.stdout.write(self.style.WARNING('   ⚠️  Not using persistent volume path'))
                self.stdout.write(f'      Current path: {persistent_path}')
                self.stdout.write('      Should be: /app/persistent_data')
        
        # Summary
        self.stdout.write('\n=== Summary ===')
        if data_path.exists() and user_templates_path.exists():
            self.stdout.write(self.style.SUCCESS('✅ Storage is configured correctly'))
        else:
            self.stdout.write(self.style.ERROR('❌ Storage paths do not exist'))
            self.stdout.write('   Action: Create persistent volume on Render and set environment variables')
        
        self.stdout.write('')

