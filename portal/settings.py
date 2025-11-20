from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-please-0b2dbd71d6e14a1b9a1e3a1b0b12a39",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"

ALLOWED_HOSTS: list[str] = os.getenv("ALLOWED_HOSTS", "*").split(",")

# CSRF Settings for Render
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if os.getenv("CSRF_TRUSTED_ORIGINS") else []


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local apps
    "automation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "automation.middleware.UploadSizeMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "portal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "portal.wsgi.application"
ASGI_APPLICATION = "portal.asgi.application"


# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases
import dj_database_url

# Use PostgreSQL from DATABASE_URL if available, fallback to SQLite for local dev
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Production: Use PostgreSQL from Render
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Local development: Use SQLite
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation - DISABLED (no password rules)
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = []


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []

# Security settings for Render deployment
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Whitenoise settings for better static file serving
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_MANIFEST_STRICT = False


# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"
LOGIN_URL = "/login/"

# File Upload Configuration
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024   # 100 MB request cap
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024    # >10MB goes to temp file
FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
]

# Create temp directory for uploads
FILE_UPLOAD_TEMP_DIR = os.path.join(BASE_DIR, "tmp_uploads")
try:
    os.makedirs(FILE_UPLOAD_TEMP_DIR, exist_ok=True)
except Exception:
    # Fallback to system temp if directory creation fails
    import tempfile
    FILE_UPLOAD_TEMP_DIR = tempfile.gettempdir()

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'automation': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Mail/Graph configuration via environment
GRAPH_TENANT_ID = os.getenv("GRAPH_TENANT_ID", "common")
GRAPH_CLIENT_ID = os.getenv("GRAPH_CLIENT_ID", "")
GRAPH_SCOPES = os.getenv("GRAPH_SCOPES", "Mail.Send")

# Persistent data storage configuration
DATA_STORAGE_PATH = os.getenv("DATA_STORAGE_PATH", str(BASE_DIR / "persistent_data"))
EMAIL_TEMPLATES_PATH = os.getenv("EMAIL_TEMPLATES_PATH", str(Path(DATA_STORAGE_PATH) / "email_templates.json"))
USER_TEMPLATES_PATH = os.getenv("USER_TEMPLATES_PATH", str(Path(DATA_STORAGE_PATH) / "user_templates"))

# Ensure persistent data directory exists
try:
    os.makedirs(DATA_STORAGE_PATH, exist_ok=True)
    os.makedirs(USER_TEMPLATES_PATH, exist_ok=True)
    # Log storage path for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Persistent storage initialized: DATA_STORAGE_PATH={DATA_STORAGE_PATH}, USER_TEMPLATES_PATH={USER_TEMPLATES_PATH}")
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not create persistent data directory: {e}")
    # Fallback to BASE_DIR
    DATA_STORAGE_PATH = str(BASE_DIR)
    EMAIL_TEMPLATES_PATH = str(BASE_DIR / "email_templates.json")
    USER_TEMPLATES_PATH = str(BASE_DIR / "user_templates")
    logger.warning(f"Using fallback paths: DATA_STORAGE_PATH={DATA_STORAGE_PATH}")


