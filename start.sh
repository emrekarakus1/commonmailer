#!/usr/bin/env bash
# Startup script for Render deployment
# This script runs when the web service starts

set -o errexit  # Exit on error

echo "Starting application..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set!"
    echo "Please create a PostgreSQL database in Render and set DATABASE_URL."
    echo "See RENDER_POSTGRESQL_SETUP.md for instructions."
    exit 1
fi

# Wait for database to be ready (PostgreSQL on Render is usually ready immediately)
echo "Checking database connection..."
python manage.py check --database default || {
    echo "ERROR: Database connection check failed!"
    exit 1
}

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput || {
    echo "ERROR: Migration failed!"
    exit 1
}

# Verify migrations completed
echo "Checking migration status..."
python manage.py showmigrations --list | grep -v "\[ \]" || echo "All migrations applied"

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn portal.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -


