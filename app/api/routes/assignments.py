"""Doctor assignment endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_roles
from app.repositories.database import connect
from app.schemas.assignment import AssignmentCreate, AssignmentIdResponse, PatientAssignment
from app.services.analytics import assignment_progress

router = APIRouter()


@router.post("/doctor/assignments", response_model=AssignmentIdResponse)
def create_assignment(
    payload: AssignmentCreate,
    current_user: dict = Depends(require_roles("doctor")),
) -> AssignmentIdResponse:
    with connect() as db:
        patient = db.execute("SELECT role, doctor_id FROM users WHERE id = ?", (payload.patient_id,)).fetchone()
        if patient is None or patient["role"] != "patient":
            raise HTTPException(status_code=404, detail="Patient not found")
        if patient["doctor_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="You do not have access to this patient")
        if db.execute("SELECT 1 FROM exercises WHERE id = ?", (payload.exercise_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        cursor = db.execute(
            "INSERT INTO assignments(patient_id, doctor_id, exercise_id, due_date, times_per_week, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (payload.patient_id, current_user["id"], payload.exercise_id, payload.due_date.isoformat() if payload.due_date else None,
             payload.times_per_week, datetime.now(timezone.utc).isoformat()),
        )
        return AssignmentIdResponse(id=cursor.lastrowid)


@router.get("/patient/assignments", response_model=list[PatientAssignment])
def list_patient_assignments(current_user: dict = Depends(require_roles("patient"))) -> list[PatientAssignment]:
    with connect() as db:
        rows = db.execute(
            """SELECT a.*, e.title, e.type, e.video_url FROM assignments a
               JOIN exercises e ON e.id = a.exercise_id WHERE a.patient_id = ? ORDER BY a.id DESC""",
            (current_user["id"],),
        ).fetchall()
        response = []
        for row in rows:
            status, done = assignment_progress(db, row)
            response.append(PatientAssignment(
                id=row["id"], exercise={"id": row["exercise_id"], "title": row["title"], "type": row["type"], "video_url": row["video_url"]},
                status=status, due_date=row["due_date"], times_per_week=row["times_per_week"], done_this_week=done,
            ))
        return response
