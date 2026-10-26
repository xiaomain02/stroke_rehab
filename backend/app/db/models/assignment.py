from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.db.base import Base
from app.db.types import UTCDateTime, utc_now_sql

if TYPE_CHECKING:
    from app.db.models.attempt import Attempt
    from app.db.models.doctor_patient import DoctorPatient
    from app.db.models.exercise import Exercise


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("doctor_patients.id"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exercises.id"), nullable=False
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    target_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    doctor_note: Mapped[str | None] = mapped_column(String, nullable=True)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=utc_now_sql()
    )

    __table_args__ = (
        CheckConstraint("target_attempts > 0", name="assignments_target_check"),
        CheckConstraint(
            "status IN ('active','completed','cancelled')",
            name="assignments_status_check",
        ),
        CheckConstraint("ends_on >= starts_on", name="assignments_period_check"),
        CheckConstraint("json_valid(config_snapshot)", name="assignments_config_json_check"),
        CheckConstraint("json_type(config_snapshot) = 'object'", name="assignments_config_object_check"),
        Index("assignments_relationship_idx", "doctor_patient_id", "status"),
        Index("assignments_exercise_idx", "exercise_id"),
    )

    relationship: Mapped["DoctorPatient"] = orm_relationship(back_populates="assignments")
    exercise: Mapped["Exercise"] = orm_relationship(back_populates="assignments")
    attempts: Mapped[list["Attempt"]] = orm_relationship(back_populates="assignment")
