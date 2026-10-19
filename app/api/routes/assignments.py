"""Doctor assignment endpoints."""

from fastapi import APIRouter

from app.schemas.assignment import AssignmentCreate, AssignmentIdResponse

router = APIRouter()


@router.post("/doctor/assignments", response_model=AssignmentIdResponse)
def create_assignment(payload: AssignmentCreate) -> AssignmentIdResponse:
    ...


@router.get("/patient/assignments")
def list_patient_assignments():
    ...
