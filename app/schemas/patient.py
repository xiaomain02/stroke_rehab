"""Patient summary and aggregate statistics schemas."""

from datetime import datetime

from pydantic import BaseModel


class PatientSummary(BaseModel):
    id: int
    full_name: str
    last_activity: datetime | None = None
    avg_score: float | None = None
    trend: float | None = None


class PatientStats(BaseModel):
    avg_score: float | None = None
    trend: float | None = None
    sessions_total: int
    completion_rate: float
