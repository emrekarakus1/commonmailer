"""
Django management command to keep the database connection alive.
This prevents Render's free PostgreSQL database from being deleted due to inactivity.

Usage:
    python manage.py keep_database_alive
"""
import logging
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Keep database connection alive by executing a simple query'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        
        try:
            # Execute a simple query to keep the database connection alive
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            if verbose:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Database connection is alive. Query result: {result}'
                    )
                )
            else:
                self.stdout.write('ok')
                
            # Log success
            logger.info("Database keep-alive check successful")
            
        except OperationalError as e:
            error_msg = f'✗ Database connection failed: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(f"Database keep-alive check failed: {str(e)}")
            raise
        except Exception as e:
            error_msg = f'✗ Unexpected error: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(f"Unexpected error during database keep-alive: {str(e)}")
            raise

