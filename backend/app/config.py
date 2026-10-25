from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # S3 / S3-совместимое хранилище (Yandex Object Storage)
    S3_ENDPOINT_URL: str | None      # None => AWS; для Yandex: https://storage.yandexcloud.net
    S3_REGION: str                   # для Yandex: ru-central1
    S3_BUCKET: str
    S3_ACCESS_KEY: str               # Yandex: статический ключ (key_id)
    S3_SECRET_KEY: str               # Yandex: секрет статического ключа
    S3_USE_SSL: bool
    S3_PRESIGN_TTL_SECONDS: int
    S3_ADDRESSING_STYLE: str         # 'virtual' | 'path'
    S3_CREATE_BUCKET: bool           # Yandex: False (бакет создаётся вручную)


@lru_cache
def get_settings() -> Settings:
    def _bool(name: str, default: str) -> bool:
        return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")

    return Settings(
        DATABASE_URL=os.environ.get(
            "DATABASE_URL", "sqlite+aiosqlite:///./data/rehab.db"
        ),
        DATABASE_URL_SYNC=os.environ.get(
            "DATABASE_URL_SYNC", "sqlite:///./data/rehab.db"
        ),
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