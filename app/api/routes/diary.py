"""Patient diary endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import assert_patient_access, require_roles
from app.repositories.database import connect
from app.schemas.diary import DiaryCreate, DiaryIdResponse, DiaryEntry

router = APIRouter()


@router.post("/diary", response_model=DiaryIdResponse)
def create_diary_entry(payload: DiaryCreate, current_user: dict = Depends(require_roles("patient"))) -> DiaryIdResponse:
    with connect() as db:
        cursor = db.execute("INSERT INTO diaries(patient_id, date, mood, fatigue, note) VALUES (?, ?, ?, ?, ?)",
                            (current_user["id"], date.today().isoformat(), payload.mood, payload.fatigue, payload.note))
        return DiaryIdResponse(id=cursor.lastrowid)


@router.get("/diary", response_model=list[DiaryEntry])
def list_own_diary_entries(current_user: dict = Depends(require_roles("patient"))) -> list[DiaryEntry]:
    with connect() as db:
        rows = db.execute("SELECT * FROM diaries WHERE patient_id = ? ORDER BY date DESC, id DESC", (current_user["id"],)).fetchall()
        return [DiaryEntry(id=r["id"], date=date.fromisoformat(r["date"]), mood=r["mood"], fatigue=r["fatigue"], note=r["note"]) for r in rows]


@router.get("/patients/{patient_id}/diary", response_model=list[DiaryEntry])
def list_patient_diary(patient_id: int, current_user: dict = Depends(require_roles("doctor"))) -> list[DiaryEntry]:
    assert_patient_access(patient_id, current_user)
    with connect() as db:
        if db.execute("SELECT 1 FROM users WHERE id = ? AND role = 'patient'", (patient_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        rows = db.execute("SELECT * FROM diaries WHERE patient_id = ? ORDER BY date DESC, id DESC", (patient_id,)).fetchall()
        return [DiaryEntry(id=r["id"], date=date.fromisoformat(r["date"]), mood=r["mood"], fatigue=r["fatigue"], note=r["note"]) for r in rows]
