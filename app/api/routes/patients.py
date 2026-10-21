"""Patient list and patient-specific statistics endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_patient_access, require_roles
from app.repositories.database import connect
from app.schemas.patient import PatientSummary, PatientStats
from app.services.analytics import patient_stats

router = APIRouter()


@router.get("/doctor/patients", response_model=list[PatientSummary])
def list_doctor_patients(current_user: dict = Depends(require_roles("doctor"))) -> list[PatientSummary]:
    with connect() as db:
        patients = db.execute("SELECT id, full_name FROM users WHERE role = 'patient' AND doctor_id = ? ORDER BY full_name", (current_user["id"],)).fetchall()
        response = []
        for patient in patients:
            activity = db.execute("SELECT MAX(created_at) FROM results WHERE patient_id = ?", (patient["id"],)).fetchone()[0]
            stats = patient_stats(db, patient["id"])
            response.append(PatientSummary(id=patient["id"], full_name=patient["full_name"], last_activity=activity,
                                           avg_score=stats["avg_score"], trend=stats["trend"]))
        return response


@router.get("/patients/{patient_id}/stats", response_model=PatientStats)
def get_patient_stats(patient_id: int, current_user: dict = Depends(require_patient_access)) -> PatientStats:
    with connect() as db:
        if db.execute("SELECT 1 FROM users WHERE id = ? AND role = 'patient'", (patient_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        return PatientStats(**patient_stats(db, patient_id))
