from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # S3 / S3-совместимое хранилище (Yandex Object Storage)
    S3_ENDPOINT_URL: str | None      # None => AWS; для Yandex: https://storage.yandexcloud.net
    S3_REGION: str                   # для Yandex: ru-central1
    S3_BUCKET: str
    S3_ACCESS_KEY: str = field(repr=False)  # Yandex: static key ID
    S3_SECRET_KEY: str = field(repr=False)  # Never display in a Settings repr.
    S3_USE_SSL: bool
    S3_PRESIGN_TTL_SECONDS: int
    S3_ADDRESSING_STYLE: str         # 'virtual' | 'path'
    S3_CREATE_BUCKET: bool           # Yandex: False (бакет создаётся вручную)


@lru_cache
def get_settings() -> Settings:
    # Existing process variables (Docker/CI) take precedence over .env.
    load_dotenv(BACKEND_ROOT / ".env", override=False)

    def _database_urls() -> tuple[str, str]:
        async_value = os.environ.get("DATABASE_URL")
        sync_value = os.environ.get("DATABASE_URL_SYNC")
        default = "sqlite+aiosqlite:///" + str(BACKEND_ROOT / "data" / "rehab.db")
        for raw in (async_value, sync_value):
            if raw and make_url(raw).get_backend_name() != "sqlite":
                raise ValueError("This project schema supports SQLite; PostgreSQL needs a separate migration.")
        urls = (
            make_url(async_value or sync_value or default).set(drivername="sqlite+aiosqlite"),
            make_url(sync_value or async_value or default).set(drivername="sqlite"),
        )
        normalized = []
        for url in urls:
            if not url.database or url.database == ":memory:" or url.query:
                raise ValueError("Use a SQLite database file without URI query parameters.")
            path = Path(url.database)
            if not path.is_absolute():
                path = BACKEND_ROOT / path
            normalized.append(url.set(database=str(path.resolve())))
        if normalized[0].database != normalized[1].database:
            raise ValueError("DATABASE_URL and DATABASE_URL_SYNC must point to the same SQLite file.")
        return tuple(url.render_as_string(hide_password=False) for url in normalized)

    database_url, database_url_sync = _database_urls()

    def _bool(name: str, default: str) -> bool:
        return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")

    return Settings(
        DATABASE_URL=database_url,
        DATABASE_URL_SYNC=database_url_sync,
        # --- S3 (Yandex Object Storage по умолчанию) ---
        S3_ENDPOINT_URL=os.environ.get(
            "S3_ENDPOINT_URL", "https://storage.yandexcloud.net"
        ) or None,
        S3_REGION=os.environ.get("S3_REGION", "ru-central1"),
        S3_BUCKET=os.environ.get("S3_BUCKET", "rehab-media"),
        S3_ACCESS_KEY=os.environ.get("S3_ACCESS_KEY", ""),
        S3_SECRET_KEY=os.environ.get("S3_SECRET_KEY", ""),
        S3_USE_SSL=_bool("S3_USE_SSL", "true"),
        S3_PRESIGN_TTL_SECONDS=int(os.environ.get("S3_PRESIGN_TTL_SECONDS", "900")),
        S3_ADDRESSING_STYLE=os.environ.get("S3_ADDRESSING_STYLE", "virtual"),
        S3_CREATE_BUCKET=_bool("S3_CREATE_BUCKET", "false"),
    )
