"""Exercise schemas."""

from pydantic import BaseModel


class ExerciseResponse(BaseModel):
    id: int
    title: str
    type: str
    description: str
    video_url: str | None = None


class VideoResponse(BaseModel):
    video_url: str
