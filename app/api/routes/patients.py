"""Patient list and patient-specific statistics endpoints."""

from fastapi import APIRouter

from app.schemas.patient import PatientSummary, PatientStats

router = APIRouter()


@router.get("/doctor/patients", response_model=list[PatientSummary])
def list_doctor_patients() -> list[PatientSummary]:
    ...


@router.get("/patients/{patient_id}/stats", response_model=PatientStats)
def get_patient_stats(patient_id: int) -> PatientStats:
    ...
