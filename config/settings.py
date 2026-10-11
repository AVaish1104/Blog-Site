"""
Django settings. All deployment-specific values come from environment variables
(optionally loaded from a local .env file). See .env.example for the full list.
"""

import os
import tempfile
from datetime import timedelta
from pathlib import Path

import dj_database_url
from csp.constants import NONE, SELF
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name, default=""):
    return os.environ.get(name, default).strip()


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = env(name)
    return int(value) if value else default


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# --- Core --------------------------------------------------------------------

# Vercel runs the app as serverless functions with a read-only, non-persistent
# filesystem. There the database lives in /tmp and is rebuilt (with demo content)
# on every cold start: nothing is saved permanently. See README "Vercel demo".
ON_VERCEL = bool(os.environ.get("VERCEL"))
EPHEMERAL_DATA = ON_VERCEL or env_bool("DJANGO_EPHEMERAL_DATA", False)

DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"  # noqa: S105
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
if ON_VERCEL:
    ALLOWED_HOSTS += [".vercel.app"] + [
        host for host in (env("VERCEL_URL"), env("VERCEL_PROJECT_PRODUCTION_URL")) if host
    ]
    CSRF_TRUSTED_ORIGINS += ["https://*.vercel.app"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "axes",
    "apps.core",
    "apps.accounts",
    "apps.images",
    "apps.blog",
    "apps.search",
    "apps.comments",
    "apps.newsletter",
    "apps.studio",
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
    "csp.middleware.CSPMiddleware",
    # Axes must be last so it can intercept lockouts.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
                "apps.studio.context_processors.studio",
            ],
        },
    },
]

# --- Database ----------------------------------------------------------------

DATA_DIR = Path(
    env("DJANGO_DATA_DIR")
    or (Path(tempfile.gettempdir()) / "marginalia" if ON_VERCEL else BASE_DIR / "data")
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL") or f"sqlite:///{(DATA_DIR / 'db.sqlite3').as_posix()}",
        conn_max_age=600,
    )
}
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    DATABASES["default"]["CONN_MAX_AGE"] = 0
    DATABASES["default"].setdefault("OPTIONS", {}).update(
        {
            # WAL lets readers and the writer work concurrently; IMMEDIATE avoids
            # "database is locked" errors when two requests write at once.
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
            "transaction_mode": "IMMEDIATE",
            "timeout": 20,
        }
    )

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Authentication ----------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "studio:dashboard"
LOGOUT_REDIRECT_URL = "blog:home"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Brute-force protection for the sign-in form.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "accounts/locked_out.html"
AXES_CLIENT_IP_CALLABLE = "apps.core.net.client_ip"
AXES_VERBOSE = False

SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
if ON_VERCEL:
    # Each serverless instance has its own throwaway database, so keep sessions in
    # signed cookies to stay signed in whichever instance answers.
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- Internationalisation ----------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# --- Static files and uploaded media -----------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT") or DATA_DIR / "media")
SERVE_MEDIA = DEBUG or ON_VERCEL or env_bool("DJANGO_SERVE_MEDIA", False)

S3_BUCKET_NAME = env("S3_BUCKET_NAME")
if S3_BUCKET_NAME:
    default_storage = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": S3_BUCKET_NAME,
            "endpoint_url": env("S3_ENDPOINT_URL") or None,
            "region_name": env("S3_REGION_NAME") or None,
            "access_key": env("S3_ACCESS_KEY_ID") or None,
            "secret_key": env("S3_SECRET_ACCESS_KEY") or None,
            "custom_domain": env("S3_CUSTOM_DOMAIN") or None,
            "file_overwrite": False,
            "querystring_auth": False,
        },
    }
    SERVE_MEDIA = False
else:
    default_storage = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    "default": default_storage,
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or ON_VERCEL
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
# On Vercel there is no collectstatic step: WhiteNoise serves files straight from
# the app and project static directories.
WHITENOISE_USE_FINDERS = ON_VERCEL
if ON_VERCEL:
    STATIC_ROOT = None  # nothing is collected on Vercel; avoids a WhiteNoise warning

IMAGE_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
IMAGE_MAX_PIXELS = 40_000_000
IMAGE_MAX_DIMENSION = 2400
FILE_UPLOAD_MAX_MEMORY_SIZE = IMAGE_MAX_UPLOAD_BYTES
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

# --- Cache -------------------------------------------------------------------

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- Email -------------------------------------------------------------------

EMAIL_HOST = env("EMAIL_HOST")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = env_int("EMAIL_PORT", 587)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
    EMAIL_TIMEOUT = 15
    EMAIL_DELIVERY = "smtp"
else:
    # No provider configured: messages are written to the server log, not delivered.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    EMAIL_DELIVERY = "console"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Marginalia <newsletter@example.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --- Publication -------------------------------------------------------------

SITE_NAME = env("SITE_NAME", "Marginalia")
SITE_TAGLINE = env("SITE_TAGLINE", "Essays, notes, and long reads.")
_vercel_host = env("VERCEL_PROJECT_PRODUCTION_URL") or env("VERCEL_URL")
SITE_URL = (
    env("SITE_URL")
    or (f"https://{_vercel_host}" if ON_VERCEL and _vercel_host else "http://127.0.0.1:8000")
).rstrip("/")
SITE_LANGUAGE = env("SITE_LANGUAGE", "en")
COMMENTS_ENABLED = env_bool("COMMENTS_ENABLED", True)
POSTS_PER_PAGE = 10
NEWSLETTER_PROVIDER = env("NEWSLETTER_PROVIDER", "apps.newsletter.providers.LocalProvider")
ADMIN_PATH = env("DJANGO_ADMIN_PATH", "django-admin/")

# --- Security ----------------------------------------------------------------

TRUST_X_FORWARDED_FOR = env_bool("DJANGO_TRUST_X_FORWARDED_FOR", ON_VERCEL)
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

if env_bool("DJANGO_BEHIND_PROXY", ON_VERCEL):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = False

_img_src = [SELF, "data:"]
if S3_BUCKET_NAME:
    _img_src.append(f"https://{env('S3_CUSTOM_DOMAIN')}" if env("S3_CUSTOM_DOMAIN") else "https:")

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF],
        "style-src": [SELF],
        "img-src": _img_src,
        "font-src": [SELF],
        "connect-src": [SELF],
        "object-src": [NONE],
        "base-uri": [SELF],
        "form-action": [SELF],
        "frame-ancestors": [NONE],
    }
}

# --- Logging -----------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "{levelname} {asctime} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "axes": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
