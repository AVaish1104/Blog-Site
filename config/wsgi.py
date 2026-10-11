import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Ephemeral hosts (Vercel) start every instance with an empty filesystem: create the
# database and demo content now. A no-op unless EPHEMERAL_DATA is enabled.
from apps.core.bootstrap import prepare_ephemeral_instance  # noqa: E402

prepare_ephemeral_instance()
app = application
