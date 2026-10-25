from __future__ import annotations

import io
import json
import re
import subprocess
import wave
from pathlib import Path
from types import SimpleNamespace

import av
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.services import storage


def s3_error(code):
    return ClientError({"Error": {"Code": str(code), "Message": "private-debug-details"},
                        "ResponseMetadata": {"HTTPStatusCode": int(code)}}, "HeadBucket")


class FakeS3:
    def __init__(self):
        self.calls = []
        self.head_error = None
        self.put_error = None
        self.delete_error = None
        self.upload_path = None

    def head_bucket(self, **kwargs):
        self.calls.append(("head", kwargs))
        if self.head_error:
            raise self.head_error

    def create_bucket(self, **kwargs):
        self.calls.append(("create", kwargs))
        self.head_error = None

    def put_object(self, **kwargs):
        self.upload_path = Path(kwargs['Body'].name)
        assert self.upload_path.is_file()
        assert not isinstance(kwargs['Body'], io.BytesIO)
        body = kwargs['Body'].read()
        self.calls.append(("put", {**kwargs, "Body": body}))
        if self.put_error:
            raise self.put_error

    def delete_object(self, **kwargs):
        self.calls.append(("delete", kwargs))
        if self.delete_error:
            raise self.delete_error

    def generate_presigned_url(self, operation, **kwargs):
        self.calls.append(("presign", {"Operation": operation, **kwargs}))
        return "https://example.invalid/test-only-signed-url"


@pytest.fixture
def s3(monkeypatch):
    fake = FakeS3()
    settings = SimpleNamespace(
        S3_BUCKET="test-only-bucket", S3_REGION="ru-central1",
        S3_ACCESS_KEY="test-only-id", S3_SECRET_KEY="test-only-secret",
        S3_ENDPOINT_URL="https://storage.yandexcloud.net", S3_USE_SSL=True,
        S3_ADDRESSING_STYLE="virtual", S3_CREATE_BUCKET=False,
        S3_PRESIGN_TTL_SECONDS=900,
    )
    monkeypatch.setattr(storage, "_client", fake)
    monkeypatch.setattr(storage, "get_settings", lambda: settings)
    # If a test accidentally bypasses the fake, it still cannot create an SDK client.
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: pytest.fail("Unexpected real SDK client"))
    return fake, settings


@pytest.fixture(scope="module")
def wav_bytes():
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(bytes(1600))
    return output.getvalue()


@pytest.fixture(scope="module")
def video_bytes():
    result = {}
    for format_name, codec_name, mime in (("mp4", "libx264", "video/mp4"), ("webm", "libvpx", "video/webm")):
        output = io.BytesIO()
        with av.open(output, mode="w", format=format_name) as container:
            stream = container.add_stream(codec_name, rate=5)
            stream.width = stream.height = 32
            stream.pix_fmt = "yuv420p"
            for _ in range(2):
                frame = av.VideoFrame(32, 32, "yuv420p")
                for plane in frame.planes:
                    plane.update(bytes(plane.buffer_size))
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        result[mime] = output.getvalue()
    return result


def test_valid_wav_uploaded_from_disk_and_original_stream_stays_open(s3, wav_bytes):
    fake, _ = s3
    original = io.BytesIO(wav_bytes)
    original.seek(10)  # Service rewinds seekable uploads.
    key, size = storage.save_upload_stream(original, media_type="audio", original_name="../../name.wav",
                                           content_type="audio/x-wav")
    assert not original.closed
    assert size == len(wav_bytes)
    assert re.fullmatch(r"audio/\d{4}/\d{2}/\d{2}/[0-9a-f-]{36}\.wav", key)
    operation, request = fake.calls[-1]
    assert operation == "put"
    assert request["Body"] == wav_bytes
    assert request["ContentLength"] == size
    assert request["ContentType"] == "audio/wav"
    assert request["CacheControl"] == "private, no-store"
    assert not fake.upload_path.exists()
    assert not fake.upload_path.parent.exists()


@pytest.mark.parametrize("mime", ["video/mp4", "video/webm"])
def test_real_video_container_and_first_frame_are_validated(s3, video_bytes, mime):
    fake, _ = s3
    key, size = storage.save_upload_stream(io.BytesIO(video_bytes[mime]), media_type="video",
        original_name="untrusted.exe", content_type=mime + ';codecs="test"')
    assert size == len(video_bytes[mime])
    assert key.endswith(".mp4" if mime == "video/mp4" else ".webm")
    assert fake.calls[-1][1]["ContentType"] == mime


@pytest.mark.parametrize("data,mime,media_type", [
    (b"not a video", "video/mp4", "video"),
    (b"\x1aE\xdf\xa3" + bytes(64), "audio/webm", "audio"),
    (b"<html>not media</html>", "video/webm", "video"),
])
def test_arbitrary_bytes_and_old_dummy_are_rejected_before_s3(s3, data, mime, media_type):
    fake, _ = s3
    with pytest.raises(ValueError, match="not valid decodable media"):
        storage.save_upload_stream(io.BytesIO(data), media_type=media_type,
                                   original_name="answer.webm", content_type=mime)
    assert fake.calls == []


def test_wav_cannot_masquerade_as_mp4(s3, wav_bytes):
    fake, _ = s3
    with pytest.raises(ValueError):
        storage.save_upload_stream(io.BytesIO(wav_bytes), media_type="video", original_name="answer.mp4", content_type="video/mp4")
    assert fake.calls == []


def test_video_cannot_masquerade_as_audio(s3, video_bytes):
    fake, _ = s3
    with pytest.raises(ValueError):
        storage.save_upload_stream(io.BytesIO(video_bytes['video/mp4']), media_type="audio", original_name="answer.m4a", content_type="audio/mp4")
    assert fake.calls == []


@pytest.mark.parametrize("mime", ["text/html", "audio/unknown", "audio/wav\r\nx-test: injected"])
def test_invalid_content_types_are_rejected(s3, mime):
    fake, _ = s3
    with pytest.raises(ValueError):
        storage.save_upload_stream(io.BytesIO(b"not used"), media_type="audio", original_name="answer.wav", content_type=mime)
    assert fake.calls == []


def test_empty_upload_is_rejected(s3):
    fake, _ = s3
    with pytest.raises(ValueError, match="Empty"):
        storage.save_upload_stream(io.BytesIO(), media_type="audio", original_name="answer.wav", content_type="audio/wav")
    assert fake.calls == []


def test_upload_limit_and_chunked_reading(s3, monkeypatch):
    fake, _ = s3
    monkeypatch.setattr(storage, "MAX_SIZE_BYTES", 12)
    monkeypatch.setattr(storage, "CHUNK", 8)
    class Stream:
        def read(self, size):
            assert size == 8
            return b"x" * 8
    with pytest.raises(storage.UploadTooLargeError):
        storage.save_upload_stream(Stream(), media_type="audio", original_name="answer.wav", content_type="audio/wav")
    assert fake.calls == []


def test_input_must_be_binary(s3):
    with pytest.raises(ValueError, match="binary synchronous"):
        storage.save_upload_stream(io.StringIO('text'), media_type="audio", original_name="a.wav", content_type="audio/wav")


def test_probe_timeout_cleans_temporary_file(s3, monkeypatch, wav_bytes):
    fake, _ = s3
    paths = []
    def timeout(args, **kwargs):
        paths.append(Path(args[2]))
        assert paths[-1].exists()
        assert kwargs["timeout"] == storage.PROBE_TIMEOUT_SECONDS
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])
    monkeypatch.setattr(storage.subprocess, "run", timeout)
    with pytest.raises(ValueError, match="timed out"):
        storage.save_upload_stream(io.BytesIO(wav_bytes), media_type="audio", original_name="a.wav", content_type="audio/wav")
    assert not paths[0].exists()
    assert fake.calls == []


def test_failed_s3_upload_cleans_temporary_file_and_hides_provider_details(s3, wav_bytes):
    fake, _ = s3
    fake.put_error = s3_error(403)
    with pytest.raises(storage.StorageError, match="Object upload failed") as error:
        storage.save_upload_stream(io.BytesIO(wav_bytes), media_type="audio", original_name="a.wav", content_type="audio/wav")
    assert 'private-debug-details' not in str(error.value)
    assert not fake.upload_path.parent.exists()


@pytest.mark.parametrize("ttl", [0, -1, 3601, 1.5, True, "900"])
def test_invalid_ttl_is_not_replaced_with_default(s3, ttl):
    fake, _ = s3
    with pytest.raises(ValueError, match="TTL"):
        storage.presigned_url("audio/test.webm", ttl_seconds=ttl)
    assert fake.calls == []


def test_explicit_ttl_and_default_ttl(s3):
    fake, _ = s3
    assert storage.presigned_url("audio/test.webm") == "https://example.invalid/test-only-signed-url"
    assert fake.calls[-1][1]["ExpiresIn"] == 900
    storage.presigned_url("audio/test.webm", ttl_seconds=120)
    assert fake.calls[-1][1]["ExpiresIn"] == 120
    assert fake.calls[-1][1]["HttpMethod"] == "GET"


@pytest.mark.parametrize("key", ["", " ", "/tmp/file.mp4", "../file.mp4", "a/../file.mp4", "a//b.mp4",
                                      "https://example.invalid/file.mp4", "a\\b.mp4", "a\x00.mp4"])
def test_invalid_keys_are_rejected_for_download_and_delete(s3, key):
    fake, _ = s3
    with pytest.raises(ValueError): storage.presigned_url(key)
    with pytest.raises(ValueError): storage.delete_object(key)
    assert fake.calls == []


def test_delete_uses_object_key_and_surfaces_errors(s3):
    fake, _ = s3
    storage.delete_object("audio/test.webm")
    assert fake.calls[-1] == ("delete", {"Bucket": "test-only-bucket", "Key": "audio/test.webm"})
    fake.delete_error = s3_error(403)
    with pytest.raises(storage.StorageError, match="deletion failed"):
        storage.delete_object("audio/test.webm")


def test_403_is_access_error_and_never_creates_bucket(s3):
    fake, settings = s3
    settings.S3_CREATE_BUCKET = True
    fake.head_error = s3_error(403)
    with pytest.raises(storage.StorageError, match="access denied"):
        storage.ensure_bucket()
    assert [name for name, _ in fake.calls] == ['head']


def test_missing_bucket_is_not_created_by_default(s3):
    fake, _ = s3
    fake.head_error = s3_error(404)
    with pytest.raises(storage.StorageError, match="not found"):
        storage.ensure_bucket()
    assert [name for name, _ in fake.calls] == ['head']


def test_bucket_creation_requires_explicit_setting(s3):
    fake, settings = s3
    settings.S3_CREATE_BUCKET = True
    fake.head_error = s3_error(404)
    storage.ensure_bucket()
    assert [name for name, _ in fake.calls] == ['head', 'create', 'head']


def test_network_failure_is_sanitized(s3):
    fake, _ = s3
    fake.head_error = EndpointConnectionError(endpoint_url='https://private-debug-details.invalid')
    with pytest.raises(storage.StorageError, match="unavailable") as error:
        storage.ensure_bucket()
    assert 'private-debug-details' not in str(error.value)


def test_client_configuration_and_missing_credentials(s3, monkeypatch):
    fake, settings = s3
    monkeypatch.setattr(storage, '_client', None)
    settings.S3_ACCESS_KEY = ''
    with pytest.raises(storage.StorageError, match='S3_ACCESS_KEY'):
        storage._s3()
    settings.S3_ACCESS_KEY = 'test-only-id'
    calls = []
    def factory(service, **kwargs):
        calls.append((service, kwargs))
        return fake
    monkeypatch.setattr(storage.boto3, 'client', factory)
    assert storage._s3() is fake
    assert calls[0][1]['config'].signature_version == 's3v4'
    assert calls[0][1]['config'].connect_timeout == 5
    assert calls[0][1]['config'].read_timeout == 30


def test_dummy_uploader_was_removed():
    assert not hasattr(storage, 'put_dummy')


@pytest.fixture(scope="module")
def compressed_audio_bytes():
    result = {}
    for mime, format_name, codec_name in (
        ('audio/mp4', 'mp4', 'aac'), ('audio/webm', 'webm', 'libopus'),
        ('audio/ogg', 'ogg', 'libopus'), ('audio/mpeg', 'mp3', 'libmp3lame'),
    ):
        output = io.BytesIO()
        with av.open(output, mode='w', format=format_name) as container:
            stream = container.add_stream(codec_name, rate=48000)
            stream.layout = 'mono'
            for _ in range(5):
                frame = av.AudioFrame(format='fltp', layout='mono', samples=1024)
                frame.sample_rate = 48000
                for plane in frame.planes:
                    plane.update(bytes(plane.buffer_size))
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        result[mime] = output.getvalue()
    return result


@pytest.mark.parametrize('mime', ['audio/mp4', 'audio/webm', 'audio/ogg', 'audio/mpeg'])
def test_real_compressed_audio_formats(s3, compressed_audio_bytes, mime):
    fake, _ = s3
    key, size = storage.save_upload_stream(io.BytesIO(compressed_audio_bytes[mime]),
        media_type='audio', original_name='recording', content_type=mime)
    assert size == len(compressed_audio_bytes[mime])
    assert key.endswith(storage.CONTENT_TYPES[mime][1])
    assert fake.calls[-1][1]['ContentType'] == mime


def test_reserved_key_is_used_for_the_pending_database_record(s3, wav_bytes):
    fake, _ = s3
    reserved = storage.build_storage_key('audio', 'upload.wav')
    key, _ = storage.save_upload_stream(io.BytesIO(wav_bytes), media_type='audio',
        original_name='answer.wav', content_type='audio/wav', storage_key=reserved)
    assert key == reserved == fake.calls[-1][1]['Key']


@pytest.mark.parametrize('key', ['video/test.wav', 'audio/test.mp4', '../test.wav'])
def test_reserved_key_must_match_validated_type(s3, key, wav_bytes):
    fake, _ = s3
    with pytest.raises(ValueError):
        storage.save_upload_stream(io.BytesIO(wav_bytes), media_type='audio',
            original_name='answer.wav', content_type='audio/wav', storage_key=key)
    assert fake.calls == []


def test_settings_repr_does_not_expose_storage_credentials():
    from dataclasses import fields
    from app.config import Settings
    hidden = {field.name for field in fields(Settings) if not field.repr}
    assert {'S3_ACCESS_KEY', 'S3_SECRET_KEY'} <= hidden
