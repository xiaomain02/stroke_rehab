from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.attempt import Attempt
    from app.db.models.exercise import Exercise
    from app.db.models.user import User


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uploaded_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    exercise_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("exercises.id"), nullable=True
    )
    attempt_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("attempts.id"), nullable=True
    )
    media_type: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "media_type IN ('audio','video')", name="media_files_type_check"
        ),
        CheckConstraint(
            "length(trim(storage_key)) > 0", name="media_files_storage_key_check"
        ),
        CheckConstraint("size_bytes > 0", name="media_files_size_check"),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="media_files_duration_check",
        ),
        CheckConstraint(
            "status IN ('pending','ready','failed')", name="media_files_status_check"
        ),
        CheckConstraint(
            "(exercise_id IS NOT NULL) <> (attempt_id IS NOT NULL)",
            name="media_files_target_check",
        ),
        CheckConstraint(
            "(media_type = 'audio' AND mime_type LIKE 'audio/%') OR "
            "(media_type = 'video' AND mime_type LIKE 'video/%')",
            name="media_files_mime_check",
        ),
        Index(
            "media_files_exercise_idx",
            "exercise_id",
            sqlite_where=text("exercise_id IS NOT NULL"),
        ),
        Index(
            "media_files_attempt_idx",
            "attempt_id",
            sqlite_where=text("attempt_id IS NOT NULL"),
        ),
        Index("media_files_uploader_idx", "uploaded_by"),
    )

    uploader: Mapped["User"] = relationship(back_populates="uploaded_media")
    exercise: Mapped["Exercise | None"] = relationship(back_populates="media_files")
    attempt: Mapped["Attempt | None"] = relationship(back_populates="media_files")