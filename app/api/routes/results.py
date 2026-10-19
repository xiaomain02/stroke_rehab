"""Result submission, media upload, and patient result history."""

from fastapi import APIRouter, UploadFile

from app.schemas.result import ResultCreate, ResultIdResponse, ResultMediaResponse, ResultSummary

router = APIRouter()


@router.post("/results", response_model=ResultIdResponse)
def submit_result(payload: ResultCreate) -> ResultIdResponse:
    ...


@router.post("/results/{result_id}/media", response_model=ResultMediaResponse)
def upload_result_media(result_id: int, file: UploadFile) -> ResultMediaResponse:
    ...


@router.get("/patients/{patient_id}/results", response_model=list[ResultSummary])
def list_patient_results(patient_id: int) -> list[ResultSummary]:
    ...
