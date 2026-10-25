"""Private subprocess worker: validate local media without network protocols."""
from __future__ import annotations

import json
import sys

# Force a specific demuxer instead of accepting playlists or arbitrary inputs.
FORMATS = {
    "video/webm": "matroska", "audio/webm": "matroska",
    "video/mp4": "mov", "audio/mp4": "mov",
    "audio/mpeg": "mp3", "audio/wav": "wav", "audio/ogg": "ogg",
}
MAX_PIXELS = 4096 * 2160


def validate(path: str, content_type: str) -> bool:
    import av

    expected = content_type.split("/", 1)[0]
    with av.open(path, mode="r", format=FORMATS[content_type], options={
        "protocol_whitelist": "file", "enable_drefs": "0", "use_absolute_path": "0",
    }) as container:
        streams = list(container.streams)
        if len(streams) > 8:
            return False
        if expected == "audio" and any(stream.type == "video" for stream in streams):
            return False
        candidates = [stream for stream in streams if stream.type == expected]
        if not candidates:
            return False
        stream = candidates[0]
        codec = stream.codec_context
        codec.thread_count = 1
        if expected == "video":
            if codec.width <= 0 or codec.height <= 0 or codec.width * codec.height > MAX_PIXELS:
                return False
        elif not 0 < len(codec.layout.channels) <= 8 or not 0 < codec.sample_rate <= 192000:
            return False
        if content_type.endswith("/webm"):
            # Matroska with arbitrary codecs must not masquerade as WebM.
            for candidate in streams:
                allowed = {"vp8", "vp9", "av1"} if candidate.type == "video" else {"opus", "vorbis"}
                if candidate.type not in ("audio", "video") or candidate.codec_context.name not in allowed:
                    return False
        for frame in container.decode(stream):
            if getattr(frame, "is_corrupt", False):
                return False
            if expected == "video":
                return frame.width > 0 and frame.height > 0 and frame.width * frame.height <= MAX_PIXELS
            return frame.samples > 0
    return False


def main() -> int:
    try:
        import av  # noqa: F401
    except ImportError:
        return 2
    if len(sys.argv) != 3 or sys.argv[2] not in FORMATS:
        return 1
    try:
        if validate(sys.argv[1], sys.argv[2]):
            print(json.dumps({"valid": True}))
            return 0
    except Exception:
        # Never print untrusted metadata, local paths, or decoder diagnostics.
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
