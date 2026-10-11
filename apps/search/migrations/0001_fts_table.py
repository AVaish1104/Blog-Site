from django.db import migrations

FTS_TABLE = "search_post_fts"


def create_fts_table(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        return
    with schema_editor.connection.cursor() as cursor:
        try:
            cursor.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5("
                "title, excerpt, body, tags, category, tokenize = 'porter unicode61')"
            )
        except Exception:  # noqa: BLE001 — SQLite built without FTS5: fall back to basic search
            pass


def drop_fts_table(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        schema_editor.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}")


class Migration(migrations.Migration):
    dependencies = [("blog", "0001_initial")]

    operations = [migrations.RunPython(create_fts_table, drop_fts_table)]
