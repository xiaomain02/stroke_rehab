"""Diary schemas."""

from datetime import date

from pydantic import BaseModel, Field


class DiaryCreate(BaseModel):
    mood: int = Field(ge=1, le=5)
    fatigue: int = Field(ge=1, le=5)
    note: str | None = None


class DiaryIdResponse(BaseModel):
    id: int


class DiaryEntry(BaseModel):
    id: int
    date: date
    mood: int
    fatigue: int
    note: str | None = None
