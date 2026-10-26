"""UTC timestamps in SQLite's TEXT columns, matching the initial SQL schema."""
from datetime import datetime, timezone

from sqlalchemy import Text, text
from sqlalchemy.types import TypeDecorator


def utc_now_sql():
    return text("(strftime('%Y-%m-%dT%H:%M:%fZ','now'))")


class UTCDateTime(TypeDecorator):
    """ISO UTC with millisecond precision; SQLite does not retain tzinfo itself."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError("Use a timezone-aware datetime, for example datetime.now(timezone.utc).")
        return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Older SQLAlchemy SQLite DateTime columns dropped tzinfo; their values
        # were intended to be UTC. Reading them must not expose a naive datetime.
        return parsed.replace(tzinfo=timezone.utc) if parsed.utcoffset() is None else parsed.astimezone(timezone.utc)
