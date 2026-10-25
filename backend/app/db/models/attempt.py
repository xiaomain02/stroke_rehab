from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.assignment import Assignment
    from app.db.models.media_file import MediaFile


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assignments.id"), nullable=False
    )
    submission_key: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    auto_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    doctor_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    raw_result: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    patient_comment: Mapped[str | None] = mapped_column(String, nullable=True)
    doctor_feedback: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("doctor_profiles.user_id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("duration_ms >= 0", name="attempts_duration_check"),
        CheckConstraint(
            "auto_score IS NULL OR auto_score BETWEEN 0 AND 100",
            name="attempts_auto_score_check",
        ),
        CheckConstraint(
            "doctor_score IS NULL OR doctor_score BETWEEN 0 AND 100",
            name="attempts_doctor_score_check",
        ),
        CheckConstraint("completed_at >= started_at", name="attempts_period_check"),
        CheckConstraint(
            "(reviewed_by IS NULL) = (reviewed_at IS NULL)",
            name="attempts_review_pair_check",
        ),
        CheckConstraint(
            "doctor_score IS NULL OR reviewed_by IS NOT NULL",
            name="attempts_doctor_score_reviewed_check",
        ),
        CheckConstraint(
            "doctor_feedback IS NULL OR reviewed_by IS NOT NULL",
            name="attempts_feedback_reviewed_check",
        ),
        Index("attempts_assignment_time_idx", "assignment_id", "completed_at"),
        Index(
            "attempts_reviewer_idx",
            "reviewed_by",
            sqlite_where=text("reviewed_by IS NOT NULL"),
        ),
    )

    assignment: Mapped["Assignment"] = relationship(back_populates="attempts")
    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="attempt")