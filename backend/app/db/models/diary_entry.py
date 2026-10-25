from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patient_profiles.user_id"), nullable=False
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    wellbeing: Mapped[int] = mapped_column(Integer, nullable=False)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fatigue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("wellbeing BETWEEN 1 AND 5", name="diary_wellbeing_check"),
        CheckConstraint(
            "mood IS NULL OR mood BETWEEN 1 AND 5", name="diary_mood_check"
        ),
        CheckConstraint(
            "fatigue IS NULL OR fatigue BETWEEN 0 AND 10",
            name="diary_fatigue_check",
        ),
        UniqueConstraint("patient_id", "entry_date", name="diary_patient_date_unique"),
    )