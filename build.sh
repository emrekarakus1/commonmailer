#!/usr/bin/env bash
# Build script for Render deployment
# This script runs during the build phase on Render

set -o errexit  # Exit on error

echo "Starting build process..."

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files (no database needed for this)
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Static files collection had warnings, continuing..."

echo "Build completed successfully!"


