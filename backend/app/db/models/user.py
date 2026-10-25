from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.media_file import MediaFile
    from app.db.models.profile import DoctorProfile, PatientProfile


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("id", "role", name="users_id_role_unique"),
        CheckConstraint("length(trim(full_name)) > 0", name="users_full_name_check"),
        CheckConstraint("role IN ('patient','doctor')", name="users_role_check"),
    )

    doctor_profile: Mapped["DoctorProfile | None"] = relationship(
        back_populates="user", uselist=False
    )
    patient_profile: Mapped["PatientProfile | None"] = relationship(
        back_populates="user", uselist=False
    )
    uploaded_media: Mapped[list["MediaFile"]] = relationship(
        back_populates="uploader"
    )