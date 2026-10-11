"""Vercel serverless entry point: exposes the Django WSGI application as `app`."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()

from apps.core.bootstrap import prepare_ephemeral_instance  # noqa: E402

prepare_ephemeral_instance()

app = application
