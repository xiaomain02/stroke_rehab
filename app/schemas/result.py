"""Result submission and media schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResultCreate(BaseModel):
    assignment_id: int
    score: float = Field(ge=0, le=100)
    duration_sec: int
    errors: int
    details: dict[str, Any] | None = None


class ResultIdResponse(BaseModel):
    id: int


class ResultMediaResponse(BaseModel):
    media_url: str
    media_type: Literal["audio", "video"] | None


class ResultSummary(BaseModel):
    id: int
    exercise_id: int
    exercise_title: str
    type: str
    score: float
    duration_sec: int
    errors: int
    created_at: datetime
    media_url: str | None = None
    media_type: Literal["audio", "video"] | None = None
