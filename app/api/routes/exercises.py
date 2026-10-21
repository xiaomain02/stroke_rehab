"""Exercise catalog and doctor video upload endpoints."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.security import get_current_user, require_roles
from app.repositories.database import connect
from app.schemas.exercise import ExerciseResponse, VideoResponse

router = APIRouter()


@router.get("/exercises", response_model=list[ExerciseResponse])
def list_exercises() -> list[ExerciseResponse]:
    with connect() as db:
        return [ExerciseResponse(**dict(row)) for row in db.execute("SELECT * FROM exercises ORDER BY id")]


@router.post("/doctor/exercises/{exercise_id}/video", response_model=VideoResponse)
async def upload_exercise_video(
    exercise_id: int,
    file: UploadFile,
    current_user: dict = Depends(require_roles("doctor")),
) -> VideoResponse:
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Upload must be a video file")
    content = await file.read(50 * 1024 * 1024 + 1)
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Video file exceeds the 50 MB limit")
    url = f"/media/exercises/{exercise_id}"
    with connect() as db:
        if db.execute("SELECT 1 FROM exercises WHERE id = ?", (exercise_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        db.execute(
            "INSERT INTO exercise_media(exercise_id, content_type, filename, content) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(exercise_id) DO UPDATE SET content_type=excluded.content_type, filename=excluded.filename, content=excluded.content",
            (exercise_id, file.content_type, file.filename or "video", content),
        )
        db.execute("UPDATE exercises SET video_url = ? WHERE id = ?", (url, exercise_id))
    return VideoResponse(video_url=url)


@router.get("/media/exercises/{exercise_id}")
def get_exercise_video(exercise_id: int, _user: dict = Depends(get_current_user)) -> Response:
    with connect() as db:
        row = db.execute("SELECT content_type, content FROM exercise_media WHERE exercise_id = ?", (exercise_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return Response(content=row["content"], media_type=row["content_type"],
                    headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
