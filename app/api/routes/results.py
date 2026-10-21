"""Result submission, media upload, and patient result history."""

import json

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.security import assert_patient_access, get_current_user, require_patient_access, require_roles
from app.repositories.database import connect
from app.schemas.result import ResultCreate, ResultIdResponse, ResultMediaResponse, ResultSummary

router = APIRouter()


@router.post("/results", response_model=ResultIdResponse)
def submit_result(payload: ResultCreate, current_user: dict = Depends(require_roles("patient"))) -> ResultIdResponse:
    with connect() as db:
        assignment = db.execute("SELECT * FROM assignments WHERE id = ?", (payload.assignment_id,)).fetchone()
        if assignment is None:
            raise HTTPException(status_code=404, detail="Assignment not found")
        if assignment["patient_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="You do not have access to this assignment")
        cursor = db.execute(
            "INSERT INTO results(assignment_id, patient_id, exercise_id, score, duration_sec, errors, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (assignment["id"], current_user["id"], assignment["exercise_id"], payload.score, payload.duration_sec,
             payload.errors, json.dumps(payload.details, ensure_ascii=False) if payload.details is not None else None,
             datetime.now(timezone.utc).isoformat()),
        )
        return ResultIdResponse(id=cursor.lastrowid)


@router.post("/results/{result_id}/media", response_model=ResultMediaResponse)
async def upload_result_media(
    result_id: int,
    file: UploadFile,
    current_user: dict = Depends(require_roles("patient")),
) -> ResultMediaResponse:
    if not file.content_type or not (file.content_type.startswith("audio/") or file.content_type.startswith("video/")):
        raise HTTPException(status_code=400, detail="Upload must be an audio or video file")
    content = await file.read(50 * 1024 * 1024 + 1)
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Media file exceeds the 50 MB limit")
    with connect() as db:
        row = db.execute("SELECT patient_id FROM results WHERE id = ?", (result_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Result not found")
        if row["patient_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="You do not have access to this result")
        media_type = "audio" if file.content_type.startswith("audio/") else "video"
        url = f"/media/results/{result_id}"
        db.execute("UPDATE results SET media_url = ?, media_type = ?, media_content_type = ?, media = ? WHERE id = ?",
                   (url, media_type, file.content_type, content, result_id))
    return ResultMediaResponse(media_url=url, media_type=media_type)


@router.get("/patients/{patient_id}/results", response_model=list[ResultSummary])
def list_patient_results(
    patient_id: int,
    _user: dict = Depends(require_patient_access),
) -> list[ResultSummary]:
    with connect() as db:
        rows = db.execute(
            """SELECT r.*, e.title AS exercise_title, e.type FROM results r
               JOIN exercises e ON e.id = r.exercise_id WHERE r.patient_id = ?
               ORDER BY r.created_at DESC, r.id DESC""", (patient_id,),
        ).fetchall()
        return [ResultSummary(id=r["id"], exercise_id=r["exercise_id"], exercise_title=r["exercise_title"], type=r["type"],
                              score=r["score"], duration_sec=r["duration_sec"], errors=r["errors"],
                              created_at=datetime.fromisoformat(r["created_at"]), media_url=r["media_url"], media_type=r["media_type"])
                for r in rows]


@router.get("/media/results/{result_id}")
def get_result_media(result_id: int, current_user: dict = Depends(get_current_user)) -> Response:
    with connect() as db:
        row = db.execute("SELECT patient_id, media_content_type, media FROM results WHERE id = ?", (result_id,)).fetchone()
    if row is None or row["media"] is None:
        raise HTTPException(status_code=404, detail="Media not found")
    assert_patient_access(row["patient_id"], current_user)
    return Response(content=row["media"], media_type=row["media_content_type"] or "application/octet-stream",
                    headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
