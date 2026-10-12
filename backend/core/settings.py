"""
Django settings for core project.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# BASE_DIR = .../interserver-clone/backend
BASE_DIR = Path(__file__).resolve().parent.parent

# Project root = .../interserver-clone  (one level above backend)
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-fallback-change-me-in-production",
)

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]

# Render terminates HTTPS at its proxy and forwards the original scheme here.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ---------------------------------------------------------------
# Applications
# ---------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # local
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

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

WSGI_APPLICATION = "core.wsgi.application"


# ---------------------------------------------------------------
# Database — SQLite for now, easy to swap to Postgres later
# ---------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{(BASE_DIR / 'db.sqlite3').as_posix()}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# ---------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------
# i18n
# ---------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------
# Static files
#   STATIC_URL    -> served at /static/
#   STATICFILES_DIRS -> looks in ../static/ (i.e. interserver-clone/static)
#   STATIC_ROOT   -> where collectstatic dumps files in prod
# ---------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [PROJECT_ROOT / "static"]
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_ROOT / "media"


# ---------------------------------------------------------------
# Auth
# ---------------------------------------------------------------
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "logged_out"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ===============================================================
# PAYHERO (v2 Developer API — Basic Auth + Channel ID)
# ===============================================================
PAYHERO_API_URL = os.getenv(
    "PAYHERO_API_URL",
    "https://backend.payhero.co.ke/api/v2/payments",
)
PAYHERO_AUTH_TOKEN = os.getenv("PAYHERO_AUTH_TOKEN", "")
PAYHERO_CHANNEL_ID = os.getenv("PAYHERO_CHANNEL_ID", "")
PAYHERO_PROVIDER = os.getenv("PAYHERO_PROVIDER", "m-pesa")
PAYHERO_CALLBACK_URL = os.getenv("PAYHERO_CALLBACK_URL", "")

# Currency conversion
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY", "")
EXCHANGE_RATE_FALLBACK_KES_PER_USD = float(
    os.getenv("EXCHANGE_RATE_FALLBACK_KES_PER_USD", "130.00")
)

# Credential encryption
CREDENTIALS_ENCRYPTION_KEY = os.getenv("CREDENTIALS_ENCRYPTION_KEY", "")

# Django 6 form rendering compatibility
FORM_RENDERER = "django.forms.renderers.DjangoTemplates"

# Email — console backend in development; replace with SMTP in production.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@interserver.local"