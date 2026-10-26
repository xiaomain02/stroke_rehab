from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime, utc_now_sql

if TYPE_CHECKING:
    from app.db.models.assignment import Assignment
    from app.db.models.media_file import MediaFile


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    component_key: Mapped[str] = mapped_column(String, nullable=False)
    default_config: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'")
    )
    scoring_version: Mapped[str] = mapped_column(
        String, nullable=False, default="v1"
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("doctor_profiles.user_id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=utc_now_sql()
    )

    __table_args__ = (
        CheckConstraint("length(trim(code)) > 0", name="exercises_code_check"),
        CheckConstraint("length(trim(title)) > 0", name="exercises_title_check"),
        CheckConstraint(
            "category IN ('motor','speech','memory')", name="exercises_category_check"
        ),
        CheckConstraint("is_active IN (0,1)", name="exercises_active_check"),
        CheckConstraint("json_valid(default_config)", name="exercises_config_json_check"),
        CheckConstraint("json_type(default_config) = 'object'", name="exercises_config_object_check"),
    )

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="exercise")
    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="exercise")
