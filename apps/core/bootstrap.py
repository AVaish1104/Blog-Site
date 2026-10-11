"""
Cold-start preparation for ephemeral deployments (Vercel).

The serverless filesystem is wiped between instances, so each new instance gets
a fresh SQLite database:

1. Copy the pre-built demo snapshot (deploy/demo-snapshot, made with
   `manage.py build_demo_snapshot`) into the data directory and shift its dates
   so the sample articles look recent; or, if there is no snapshot, migrate and
   run `seed_demo` from scratch.
2. Apply any migrations newer than the snapshot.
3. Create the studio editor account if EDITOR_PASSWORD is configured.

Nothing here runs locally or on hosts with persistent storage unless
EPHEMERAL_DATA is enabled.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = Path(settings.BASE_DIR) / "deploy" / "demo-snapshot"


def prepare_ephemeral_instance():
    if not settings.EPHEMERAL_DATA:
        return
    with connection.cursor() as cursor:
        if "blog_post" in connection.introspection.table_names(cursor):
            return  # this instance is already prepared

    out = StringIO()
    database = Path(settings.DATABASES["default"]["NAME"])
    snapshot_db = SNAPSHOT_DIR / "db.sqlite3"
    used_snapshot = False
    if snapshot_db.exists() and connection.vendor == "sqlite":
        connection.close()
        database.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot_db, database)
        if (SNAPSHOT_DIR / "media").exists():
            shutil.copytree(SNAPSHOT_DIR / "media", settings.MEDIA_ROOT, dirs_exist_ok=True)
        used_snapshot = True

    call_command("migrate", interactive=False, verbosity=0, stdout=out)
    if used_snapshot:
        _shift_demo_dates()
    else:
        call_command("seed_demo", stdout=out)

    if os.environ.get("EDITOR_PASSWORD"):
        username = os.environ.get("EDITOR_USERNAME", "editor")
        call_command("create_editor", username, "--name", "Editor", stdout=out)
    logger.info(
        "Ephemeral instance prepared (%s). %s",
        "from snapshot" if used_snapshot else "seeded from scratch",
        out.getvalue().strip(),
    )


def _shift_demo_dates():
    """Move snapshot timestamps forward so demo content keeps its relative ages."""
    from apps.blog.models import Post
    from apps.comments.models import Comment

    meta = json.loads((SNAPSHOT_DIR / "snapshot.json").read_text(encoding="utf-8"))
    delta = timezone.now() - datetime.fromisoformat(meta["built_at"])
    Post.objects.exclude(published_at=None).update(published_at=F("published_at") + delta)
    Post.objects.update(created_at=F("created_at") + delta, updated_at=F("updated_at") + delta)
    Comment.objects.update(created_at=F("created_at") + delta)
