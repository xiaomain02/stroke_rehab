"""Exercise catalog and doctor video upload endpoints."""

from fastapi import APIRouter, UploadFile

from app.schemas.exercise import ExerciseResponse, VideoResponse

router = APIRouter()


@router.get("/exercises", response_model=list[ExerciseResponse])
def list_exercises() -> list[ExerciseResponse]:
    ...


@router.post("/doctor/exercises/{exercise_id}/video", response_model=VideoResponse)
def upload_exercise_video(exercise_id: int, file: UploadFile) -> VideoResponse:
    ...
