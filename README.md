# Django Mail Automation Portal

A Django-based web application for automated email sending with template management and file attachments.

## Features

- **Mail Automation**: Send personalized bulk emails with Excel data integration
- **Template Management**: Create and manage email templates with subject and body
- **File Attachments**: Automatically attach company-specific files based on Excel data
- **Microsoft Graph Integration**: Send emails through Microsoft Graph API
- **Excel Reporting**: Generate detailed Excel reports of email sending results
- **Dry Run Mode**: Preview emails before sending
- **Modern UI**: Responsive, modern interface with Font Awesome icons

## Prerequisites

- Python 3.8+
- Django 5.2+
- Microsoft Azure App Registration for Graph API access

## Environment Variables

Set the following environment variables for Microsoft Graph integration:

```bash
GRAPH_CLIENT_ID=your_azure_app_client_id
GRAPH_TENANT_ID=your_azure_tenant_id
GRAPH_SCOPES=Mail.Send
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd commonportal
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run database migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

## Running the Development Server

To start the Django development server:

```bash
python manage.py runserver 127.0.0.1:8000
```

For more verbose logging during development:

```bash
python manage.py runserver 127.0.0.1:8000 --verbosity 3
```

The application will be available at:
- Main application: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/healthz/
- Dashboard: http://127.0.0.1:8000/dashboard/
- Mail Automation: http://127.0.0.1:8000/mail/
- Template Manager: http://127.0.0.1:8000/templates/

## Usage

### 1. Mail Automation

1. Navigate to the Mail Automation page
2. Sign in with your Microsoft account (Device Code Flow)
3. Upload an Excel file with email addresses and optional company names
4. Upload invoice files (ZIP or individual files)
5. Select an email template
6. Preview with Dry Run or send emails directly
7. Download Excel report with detailed results

### 2. Template Management

1. Navigate to the Template Manager page
2. Create new templates with subject and body
3. Edit existing templates
4. Delete templates
5. Upload/download templates as JSON files

### Excel File Format

The Excel file should contain:
- `email` (required): Recipient email address
- `companyname` (optional): Company name for file matching
- `cc` (optional): CC recipients (comma-separated)

### File Attachments

- Upload a single ZIP file or individual file
- ZIP files are automatically extracted
- Files are matched to companies using case-insensitive substring search
- Supported file types: PDF, DOC, DOCX, etc.
- 20MB size limit per file

## Error Handling

The application includes comprehensive error handling:
- Health check endpoint at `/healthz/`
- Graceful error handling for all views
- Detailed logging for debugging
- Friendly error messages for users
- Upload size limits with graceful error handling
- Large file streaming to prevent memory issues

## File Upload Limits

- **Request Size**: Maximum 100 MB per request
- **Individual Files**: Maximum 20 MB per file (Microsoft Graph limit)
- **Memory Usage**: Files larger than 10 MB are streamed to disk
- **Temp Storage**: Files are stored in `tmp_uploads/` directory

### Upload Behavior
- ZIP files are automatically extracted
- Large files are streamed in chunks to prevent memory issues
- Temporary files are cleaned up automatically after processing
- Session-based temporary directories prevent conflicts

## Development

### Logging

The application uses Python's logging module with DEBUG level logging for view entry/exit and ERROR level for exceptions.

### Testing

Run tests with:
```bash
python manage.py test
```

### Cleanup

Clean up old temporary files:
```bash
# Clean files older than 24 hours
python manage.py cleanup_temp_files

# Clean files older than 1 hour (dry run)
python manage.py cleanup_temp_files --hours 1 --dry-run
```

### Code Quality

Check for linting errors:
```bash
python -m flake8 .
```

## Troubleshooting

### Common Issues

1. **Microsoft Graph Authentication**: Ensure environment variables are set correctly
2. **File Upload Issues**: Check file size limits and supported formats
3. **Excel Processing**: Verify Excel file format and column names
4. **Server Errors**: Check Django logs and health check endpoint

### Health Check

The application provides a simple health check endpoint:
```bash
curl http://127.0.0.1:8000/healthz/
```

Should return: `ok`

## License

This project is licensed under the MIT License.
