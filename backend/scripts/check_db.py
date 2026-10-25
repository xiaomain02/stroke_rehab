"""Read-only DB diagnostics; does not display user or patient record contents."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy.engine import make_url
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.config import get_settings

TABLES = ("users", "doctor_profiles", "patient_profiles", "doctor_patients", "exercises",
          "assignments", "attempts", "media_files", "diary_entries")


def main() -> int:
    path = Path(make_url(get_settings().DATABASE_URL_SYNC).database)
    if not path.is_file():
        print("Database is missing. Run: python -m alembic upgrade head")
        return 1
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
        objects = {(row[0], row[1]) for row in connection.execute("SELECT type,name FROM sqlite_master")}
        required = {("table", name) for name in TABLES} | {
            ("view", "attempt_results"), ("trigger", "diary_entries_touch_updated_at"),
            ("index", "users_email_unique"), ("table", "alembic_version"),
        }
        if not required <= objects:
            print("Incomplete schema. Back up the database, then run: python -m alembic upgrade head")
            return 1
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            print("Database integrity check failed.")
            return 1
        if connection.execute("PRAGMA foreign_key_check").fetchone():
            print("Foreign key violations found.")
            return 1
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "alembic"))
        versions = {row[0] for row in connection.execute("SELECT version_num FROM alembic_version")}
        if versions != set(ScriptDirectory.from_config(config).get_heads()):
            print("Database revision differs from the current migration heads.")
            return 1
        print("Schema, integrity and foreign keys: OK")
        for table in TABLES:
            print(f"{table}: {connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]}")
    print("Object Storage connectivity was not checked; DB diagnostics are independent of cloud access.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
