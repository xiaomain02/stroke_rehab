"""S3-хранилище медиафайлов (Yandex Object Storage).

Ключ объекта (storage_key) в БД относительный:
    'audio/2025/10/21/<uuid>.webm'
Физически — объект в бакете settings.S3_BUCKET по этому ключу.
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.config import get_settings

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
CHUNK = 1024 * 1024


_client = None


def _s3():
    global _client
    if _client is None:
        s = get_settings()
        if not s.S3_ACCESS_KEY or not s.S3_SECRET_KEY:
            raise RuntimeError(
                "S3_ACCESS_KEY / S3_SECRET_KEY are not set. "
                "Create a static access key for your service account in Yandex Cloud."
            )
        _client = boto3.client(
            "s3",
            endpoint_url=s.S3_ENDPOINT_URL,
            region_name=s.S3_REGION,
            aws_access_key_id=s.S3_ACCESS_KEY,
            aws_secret_access_key=s.S3_SECRET_KEY,
            use_ssl=s.S3_USE_SSL,
            config=Config(
                signature_version="s3v4",
                # Yandex: 'virtual' (bucket.storage.yandexcloud.net)
                # MinIO:  'path'    (localhost:9000/bucket)
                s3={"addressing_style": s.S3_ADDRESSING_STYLE},
            ),
        )
    return _client


def ensure_bucket() -> None:
    """
    Проверяет, что бакет существует.
    В Yandex бакет создаётся в консоли; S3_CREATE_BUCKET=false => только проверка.
    Если бакета нет и создавать не разрешено — падаем с понятной ошибкой.
    """
    s = get_settings()
    c = _s3()
    try:
        c.head_bucket(Bucket=s.S3_BUCKET)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket"):
            if s.S3_CREATE_BUCKET:
                c.create_bucket(Bucket=s.S3_BUCKET)
            else:
                raise RuntimeError(
                    f"Bucket '{s.S3_BUCKET}' does not exist. "
                    f"Create it in Yandex Cloud console (Object Storage → Create bucket) "
                    f"or set S3_CREATE_BUCKET=true (if your SA has rights)."
                ) from e
        else:
            # 403 — нет прав на head, но бакет может существовать.
            # Для presigned URL это ок, ошибку не глотаем только для upload.
            raise


def build_storage_key(media_type: str, original_name: str) -> str:
    ext = Path(original_name).suffix.lower() or ".bin"
    now = datetime.now(timezone.utc)
    return f"{media_type}/{now:%Y/%m/%d}/{uuid.uuid4()}{ext}"


def save_upload_stream(
    fileobj,
    *,
    media_type: str,
    original_name: str,
    content_type: str,
) -> tuple[str, int]:
    """
    Синхронная загрузка (boto3 sync). Вызывать через `await run_in_threadpool(...)`
    из FastAPI, чтобы не блокировать event loop.
    Возвращает (storage_key, size_bytes).
    """
    media_type = media_type.lower()
    if media_type not in ("audio", "video"):
        raise ValueError("media_type must be 'audio' or 'video'")
    if not (content_type or "").startswith(f"{media_type}/"):
        raise ValueError(f"content_type {content_type!r} does not match {media_type}")

    s = get_settings()
    key = build_storage_key(media_type, original_name)

    buf = io.BytesIO()
    size = 0
    while chunk := fileobj.read(CHUNK):
        size += len(chunk)
        if size > MAX_SIZE_BYTES:
            raise ValueError("file too large")
        buf.write(chunk)
    if size == 0:
        raise ValueError("empty file")
    buf.seek(0)

    _s3().put_object(
        Bucket=s.S3_BUCKET,
        Key=key,
        Body=buf,
        ContentType=content_type,
    )
    return key, size


def delete_object(storage_key: str) -> None:
    s = get_settings()
    _s3().delete_object(Bucket=s.S3_BUCKET, Key=storage_key)


def presigned_url(storage_key: str, *, ttl_seconds: int | None = None) -> str:
    """
    Временная ссылка на объект. Фронт использует её напрямую
    (аудио/видео тег), бэкенд не проксирует байты через себя.
    """
    s = get_settings()
    ttl = ttl_seconds or s.S3_PRESIGN_TTL_SECONDS
    return _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": s.S3_BUCKET, "Key": storage_key},
        ExpiresIn=ttl,
    )


def put_dummy(storage_key: str, *, media_type: str) -> int:
    """Для сида: кладём фиктивные байты."""
    s = get_settings()
    body = b"\x1aE\xdf\xa3" + b"\x00" * 64
    _s3().put_object(
        Bucket=s.S3_BUCKET,
        Key=storage_key,
        Body=body,
        ContentType=f"{media_type}/webm",
    )
    return len(body)