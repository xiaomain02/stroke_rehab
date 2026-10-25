from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "rehab.db"
SQL_PATH = Path(__file__).resolve().parent / "init.sql"


def main() -> int:
    if not SQL_PATH.exists():
        print(f"[!] init.sql not found at {SQL_PATH}", file=sys.stderr)
        return 1

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        print(
            f"[!] {DB_PATH} already exists.\n"
            f"    Delete it first if you want a clean DB:\n"
            f"      rm {DB_PATH}\n"
            f"    Or continue using it as-is (script will not touch it)."
        )
        return 1

    script = SQL_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(script)

    print(f"[+] Applied {SQL_PATH.name} -> {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())