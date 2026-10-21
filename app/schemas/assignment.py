"""Assignment schemas."""

from datetime import date

from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    patient_id: int
    exercise_id: int
    due_date: date | None = None
    times_per_week: int = Field(ge=1)


class AssignmentIdResponse(BaseModel):
    id: int


class AssignedExercise(BaseModel):
    id: int
    title: str
    type: str
    video_url: str | None = None


class PatientAssignment(BaseModel):
    id: int
    exercise: AssignedExercise
    status: str
    due_date: date | None = None
    times_per_week: int
    done_this_week: int
