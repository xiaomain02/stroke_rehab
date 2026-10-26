from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, utc_now_sql


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
        UTCDateTime(), nullable=False, server_default=utc_now_sql()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=utc_now_sql()
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
        UniqueConstraint("patient_id", "entry_date"),
    )
