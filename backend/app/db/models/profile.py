from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.doctor_patient import DoctorPatient
    from app.db.models.user import User


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="doctor")
    specialization: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("role = 'doctor'", name="doctor_profiles_role_check"),
        ForeignKeyConstraint(
            ["user_id", "role"],
            ["users.id", "users.role"],
            ondelete="RESTRICT",
            name="doctor_profiles_user_fk",
        ),
    )

    user: Mapped["User"] = relationship(back_populates="doctor_profile")
    patients: Mapped[list["DoctorPatient"]] = relationship(
        back_populates="doctor",
        foreign_keys="DoctorPatient.doctor_id",
    )


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="patient")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("role = 'patient'", name="patient_profiles_role_check"),
        ForeignKeyConstraint(
            ["user_id", "role"],
            ["users.id", "users.role"],
            ondelete="RESTRICT",
            name="patient_profiles_user_fk",
        ),
    )

    user: Mapped["User"] = relationship(back_populates="patient_profile")
    doctors: Mapped[list["DoctorPatient"]] = relationship(
        back_populates="patient",
        foreign_keys="DoctorPatient.patient_id",
    )