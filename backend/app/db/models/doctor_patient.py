from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.assignment import Assignment
    from app.db.models.profile import DoctorProfile, PatientProfile


class DoctorPatient(Base):
    __tablename__ = "doctor_patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("doctor_profiles.user_id"), nullable=False
    )
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patient_profiles.user_id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="doctor_patients_period_check",
        ),
        Index(
            "doctor_patients_active_unique",
            "doctor_id",
            "patient_id",
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
        ),
        Index("doctor_patients_patient_idx", "patient_id"),
    )

    doctor: Mapped["DoctorProfile"] = relationship(
        back_populates="patients", foreign_keys=[doctor_id]
    )
    patient: Mapped["PatientProfile"] = relationship(
        back_populates="doctors", foreign_keys=[patient_id]
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="relationship"
    )