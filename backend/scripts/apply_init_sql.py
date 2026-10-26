"""Backward-compatible entry point; Alembic is the only schema writer."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alembic import command
from alembic.config import Config


def main() -> int:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, "head")
    print("Database schema is at the latest migration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
