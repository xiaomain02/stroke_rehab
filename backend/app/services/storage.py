"""Synchronous Object Storage helpers; call from FastAPI via run_in_threadpool.

This module does not authorize users or create media_files rows. The caller must
check ownership, manage pending/ready/failed and reconcile DB/S3 failures.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings

MAX_SIZE_BYTES = 50 * 1024 * 1024
CHUNK = 1024 * 1024
PROBE_TIMEOUT_SECONDS = 15
MAX_PRESIGN_TTL_SECONDS = 3600  # Application policy, not the provider's maximum.

# Canonical MIME => (media type, canonical extension).
CONTENT_TYPES = {
    "video/webm": ("video", ".webm"),
    "video/mp4": ("video", ".mp4"),
    "audio/webm": ("audio", ".webm"),
    "audio/mp4": ("audio", ".m4a"),
    "audio/mpeg": ("audio", ".mp3"),
    "audio/wav": ("audio", ".wav"),
    "audio/ogg": ("audio", ".ogg"),
}
CONTENT_TYPE_ALIASES = {"audio/x-wav": "audio/wav"}
_client = None
_client_lock = threading.Lock()


class StorageError(RuntimeError):
    """Storage/configuration failure; the API may translate it to HTTP 502/503."""


class UploadTooLargeError(ValueError):
    """The API may translate this validation failure to HTTP 413."""


def _media_type(value: str) -> str:
    if not isinstance(value, str) or value.lower() not in ("audio", "video"):
        raise ValueError("media_type must be 'audio' or 'video'")
    return value.lower()


def normalize_content_type(media_type: str, content_type: str) -> str:
    """Accept MediaRecorder MIME parameters, but store/send a canonical MIME."""
    media_type = _media_type(media_type)
    if not isinstance(content_type, str) or any(c in content_type for c in "\r\n\x00"):
        raise ValueError("Invalid content type")
    mime = content_type.split(";", 1)[0].strip().lower()
    mime = CONTENT_TYPE_ALIASES.get(mime, mime)
    if mime not in CONTENT_TYPES or CONTENT_TYPES[mime][0] != media_type:
        raise ValueError("Unsupported audio/video content type")
    return mime


def _s3():
    global _client
    with _client_lock:
        if _client is None:
            settings = get_settings()
            if not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
                raise StorageError("Set S3_ACCESS_KEY and S3_SECRET_KEY on the backend.")
            if not settings.S3_BUCKET or not settings.S3_REGION:
                raise StorageError("Set S3_BUCKET and S3_REGION on the backend.")
            if settings.S3_ADDRESSING_STYLE not in ("virtual", "path", "auto"):
                raise StorageError("S3_ADDRESSING_STYLE must be virtual, path or auto.")
            if settings.S3_ENDPOINT_URL:
                endpoint = urlsplit(settings.S3_ENDPOINT_URL)
                if (endpoint.scheme not in ("http", "https") or not endpoint.hostname
                        or endpoint.username is not None or endpoint.password is not None
                        or endpoint.query or endpoint.fragment or endpoint.path not in ("", "/")):
                    raise StorageError("Invalid S3 endpoint URL.")
                if (endpoint.scheme == "https") != settings.S3_USE_SSL:
                    raise StorageError("S3_USE_SSL must match the endpoint URL scheme.")
            try:
                _client = boto3.client(
                    "s3", endpoint_url=settings.S3_ENDPOINT_URL,
                    region_name=settings.S3_REGION,
                    aws_access_key_id=settings.S3_ACCESS_KEY,
                    aws_secret_access_key=settings.S3_SECRET_KEY,
                    use_ssl=settings.S3_USE_SSL,
                    config=Config(signature_version="s3v4", connect_timeout=5, read_timeout=30,
                                  retries={"mode": "standard", "max_attempts": 2},
                                  s3={"addressing_style": settings.S3_ADDRESSING_STYLE}),
                )
            except (BotoCoreError, ValueError):
                raise StorageError("Could not initialize the S3 client; check backend settings.") from None
    return _client


def ensure_bucket() -> None:
    """Check access. A 403 is an access error, never evidence of a missing bucket."""
    settings = get_settings()
    client = _s3()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code in ("403", "AccessDenied", "Forbidden") or status == 403:
            raise StorageError("Bucket access denied; check the bucket name and service account permissions.") from None
        if code in ("404", "NoSuchBucket", "NotFound") or status == 404:
            if not settings.S3_CREATE_BUCKET:
                raise StorageError("Bucket was not found; create it in Yandex Cloud and set S3_BUCKET.") from None
            try:
                kwargs = {"Bucket": settings.S3_BUCKET}
                if settings.S3_ENDPOINT_URL is None and settings.S3_REGION != "us-east-1":
                    kwargs["CreateBucketConfiguration"] = {"LocationConstraint": settings.S3_REGION}
                client.create_bucket(**kwargs)
                client.head_bucket(Bucket=settings.S3_BUCKET)
            except (ClientError, BotoCoreError):
                raise StorageError("Could not create or access the configured bucket.") from None
        else:
            raise StorageError("Could not check the bucket; check the endpoint and storage settings.") from None
    except BotoCoreError:
        raise StorageError("Object Storage is unavailable; check connectivity and the endpoint.") from None


def build_storage_key(media_type: str, original_name: str) -> str:
    """Generate a UUID key; never embed the original filename or a user's name."""
    media_type = _media_type(media_type)
    if not isinstance(original_name, str):
        raise ValueError("original_name must be a string")
    extension = Path(original_name).suffix.lower() or ".webm"
    allowed = {ext for kind, ext in CONTENT_TYPES.values() if kind == media_type}
    if extension not in allowed:
        raise ValueError("Unsupported file extension")
    now = datetime.now(timezone.utc)
    return f"{media_type}/{now:%Y/%m/%d}/{uuid.uuid4()}{extension}"


def _validate_storage_key(storage_key: str) -> None:
    if (not isinstance(storage_key, str) or not storage_key.strip()
            or len(storage_key.encode("utf-8")) > 1024 or storage_key.startswith("/")
            or "\\" in storage_key or "://" in storage_key
            or any(ord(c) < 32 or ord(c) == 127 for c in storage_key)
            or any(part in ("", ".", "..") for part in storage_key.split("/"))):
        raise ValueError("Expected a relative Object Storage key, not a URL or local path")


def _validate_media(path: Path, content_type: str) -> None:
    # A subprocess bounds decode time and isolates native media parsing. Do not
    # include decoder stderr or file contents in API errors/logs.
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("media_probe.py")), str(path), content_type],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=PROBE_TIMEOUT_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired:
        raise ValueError("Media validation timed out") from None
    except OSError:
        raise StorageError("Could not start media validation") from None
    if result.returncode == 2:
        raise StorageError("Media validation requires PyAV; install backend dependencies.")
    if result.returncode != 0:
        raise ValueError("File is not valid decodable media of the declared type")
    try:
        valid = json.loads(result.stdout) == {"valid": True}
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise StorageError("Media validator returned an invalid response")


def save_upload_stream(fileobj, *, media_type: str, original_name: str,
                       content_type: str, storage_key: str | None = None) -> tuple[str, int]:
    """Validate and upload; return (key, measured size), as in the original API.

    Pass UploadFile.file, not the async UploadFile object. Seekable streams are
    rewound before copying; the caller's stream stays open. Copying uses CHUNK
    blocks; temporary files are removed on success and failure. This validates
    the container and first decoded frame, not every frame or browser support.
    Optional storage_key must be generated by the server, e.g. reserved in a
    pending DB row. Never take it directly from an untrusted API request.
    """
    media_type = _media_type(media_type)
    mime = normalize_content_type(media_type, content_type)
    extension = CONTENT_TYPES[mime][1]
    # The declared type is verified by the decoder before any S3 request.
    key = build_storage_key(media_type, "upload" + extension) if storage_key is None else storage_key
    _validate_storage_key(key)
    if not key.startswith(media_type + "/") or not key.endswith(extension):
        raise ValueError("Reserved storage key must match the media type and canonical extension")
    if callable(getattr(fileobj, "seekable", None)) and fileobj.seekable():
        fileobj.seek(0)
    with tempfile.TemporaryDirectory(prefix="rehab-upload-") as directory:
        path = Path(directory) / ("upload" + extension)
        size = 0
        with path.open("wb") as target:
            while True:
                chunk = fileobj.read(CHUNK)
                if not isinstance(chunk, bytes):
                    raise ValueError("Pass a binary synchronous stream, such as UploadFile.file")
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_SIZE_BYTES:
                    raise UploadTooLargeError("File exceeds the 50 MiB upload limit")
                target.write(chunk)
        if size == 0:
            raise ValueError("Empty files are not allowed")
        _validate_media(path, mime)
        settings = get_settings()
        try:
            with path.open("rb") as source:
                _s3().put_object(
                    Bucket=settings.S3_BUCKET, Key=key, Body=source,
                    ContentLength=size, ContentType=mime,
                    ContentDisposition="inline", CacheControl="private, no-store",
                )
        except (ClientError, BotoCoreError):
            raise StorageError("Object upload failed; check storage access and connectivity.") from None
    return key, size


def delete_object(storage_key: str) -> None:
    """Delete only after the caller checks access and DB consistency."""
    _validate_storage_key(storage_key)
    try:
        _s3().delete_object(Bucket=get_settings().S3_BUCKET, Key=storage_key)
    except (ClientError, BotoCoreError):
        raise StorageError("Object deletion failed; check storage permissions and connectivity.") from None


def presigned_url(storage_key: str, *, ttl_seconds: int | None = None) -> str:
    """Authorize the user BEFORE calling. Signing does not check object existence."""
    _validate_storage_key(storage_key)
    settings = get_settings()
    ttl = settings.S3_PRESIGN_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    if type(ttl) is not int or not 1 <= ttl <= MAX_PRESIGN_TTL_SECONDS:
        raise ValueError("Link TTL must be an integer from 1 to 3600 seconds")
    try:
        return _s3().generate_presigned_url(
            "get_object", Params={"Bucket": settings.S3_BUCKET, "Key": storage_key},
            ExpiresIn=ttl, HttpMethod="GET",
        )
    except (ClientError, BotoCoreError):
        raise StorageError("Could not sign an Object Storage URL.") from None
