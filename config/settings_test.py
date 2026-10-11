"""Settings for the automated test suite."""

import os
import tempfile

os.environ["DJANGO_DEBUG"] = "false"
os.environ["DJANGO_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DJANGO_ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
os.environ["DJANGO_SECURE_SSL_REDIRECT"] = "false"
os.environ.pop("DATABASE_URL", None)
os.environ.pop("EMAIL_HOST", None)
os.environ.pop("S3_BUCKET_NAME", None)

from .settings import *  # noqa: E402,F403
from .settings import STORAGES  # noqa: E402

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MEDIA_ROOT = tempfile.mkdtemp(prefix="blog-test-media-")
STATIC_ROOT = tempfile.mkdtemp(prefix="blog-test-static-")
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SITE_URL = "http://testserver"
EMAIL_DELIVERY = "console"
SERVE_MEDIA = True  # live-server browser tests load uploaded covers
