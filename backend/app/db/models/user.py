from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Integer,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime, utc_now_sql

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
        UTCDateTime(), nullable=False, server_default=utc_now_sql()
    )

    __table_args__ = (
        UniqueConstraint("id", "role"),
        CheckConstraint("length(trim(full_name)) > 0", name="users_full_name_check"),
        CheckConstraint("role IN ('patient','doctor')", name="users_role_check"),
        CheckConstraint("is_active IN (0,1)", name="users_active_check"),
        Index("users_email_unique", func.lower(email), unique=True),
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
