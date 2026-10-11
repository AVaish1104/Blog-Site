import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

SNAPSHOT_DIR = Path(settings.BASE_DIR) / "deploy" / "demo-snapshot"


class Command(BaseCommand):
    help = (
        "Build a pre-seeded SQLite database + media snapshot used to start ephemeral "
        "(Vercel) instances quickly. Re-run after changing models or demo content."
    )

    def handle(self, *args, **options):
        work = Path(tempfile.mkdtemp(prefix="demo-snapshot-"))
        env = {
            **os.environ,
            "DJANGO_DATA_DIR": str(work),
            "DJANGO_EPHEMERAL_DATA": "false",
            "DATABASE_URL": "",
            "MEDIA_ROOT": "",
        }
        manage = str(Path(settings.BASE_DIR) / "manage.py")
        for args in (["migrate", "--noinput", "-v", "0"], ["seed_demo"]):
            subprocess.run([sys.executable, manage, *args], env=env, check=True)  # noqa: S603

        database = work / "db.sqlite3"
        connection = sqlite3.connect(database)
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("VACUUM")
        connection.close()

        if SNAPSHOT_DIR.exists():
            shutil.rmtree(SNAPSHOT_DIR)
        SNAPSHOT_DIR.mkdir(parents=True)
        shutil.copy2(database, SNAPSHOT_DIR / "db.sqlite3")
        if (work / "media").exists():
            shutil.copytree(work / "media", SNAPSHOT_DIR / "media")
        (SNAPSHOT_DIR / "snapshot.json").write_text(
            json.dumps({"built_at": timezone.now().isoformat()}), encoding="utf-8"
        )
        shutil.rmtree(work, ignore_errors=True)
        call_command("check", stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(f"Demo snapshot written to {SNAPSHOT_DIR}"))
