"""Create a consistent SQLite backup without modifying the source database."""
from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy.engine import make_url

from app.config import get_settings


def backup_database(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError("Database file does not exist; no backup created.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents overwriting a previous backup or the source.
    with destination.open("xb"):
        pass
    try:
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src:
            with sqlite3.connect(destination) as dst:
                src.backup(dst)
                if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup integrity check failed.")
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main() -> None:
    source = Path(make_url(get_settings().DATABASE_URL_SYNC).database)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = source.parent / "backups" / f"{source.stem}-{timestamp}-{uuid.uuid4().hex[:8]}.db"
    backup_database(source, destination)
    print(f"Backup saved: {destination}")


if __name__ == "__main__":
    main()
