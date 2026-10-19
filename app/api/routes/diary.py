"""Patient diary endpoints."""

from fastapi import APIRouter

from app.schemas.diary import DiaryCreate, DiaryIdResponse, DiaryEntry

router = APIRouter()


@router.post("/diary", response_model=DiaryIdResponse)
def create_diary_entry(payload: DiaryCreate) -> DiaryIdResponse:
    ...


@router.get("/diary", response_model=list[DiaryEntry])
def list_own_diary_entries() -> list[DiaryEntry]:
    ...


@router.get("/patients/{patient_id}/diary", response_model=list[DiaryEntry])
def list_patient_diary(patient_id: int) -> list[DiaryEntry]:
    ...
