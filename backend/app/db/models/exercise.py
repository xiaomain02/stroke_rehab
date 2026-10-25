from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

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
        JSON, nullable=False, default=dict
    )
    scoring_version: Mapped[str] = mapped_column(
        String, nullable=False, default="v1"
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("doctor_profiles.user_id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(trim(code)) > 0", name="exercises_code_check"),
        CheckConstraint("length(trim(title)) > 0", name="exercises_title_check"),
        CheckConstraint(
            "category IN ('motor','speech','memory')", name="exercises_category_check"
        ),
    )

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="exercise")
    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="exercise")