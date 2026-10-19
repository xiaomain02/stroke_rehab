# Stroke Rehab Backend

Backend skeleton outlined from `api-contract.xlsx`. The layout uses FastAPI conventions because the repository did not define a backend framework.

## Structure

- `app/main.py`, `app/api/router.py` — application entry point and route aggregation.
- `app/api/routes/` — handlers grouped by auth, exercises, assignments, patients, results, and diary.
- `app/schemas/` — request/response shapes from the contract.
- `app/core/security.py` — placeholders for bearer authentication and role/patient access checks.
- `app/services/` — future business logic.
- `app/repositories/` — future persistence access.
- `app/models/` — future persistence models.

All handler and security function bodies are intentionally left as `...` stubs. No database, token implementation, file storage, or business logic is included.

## Contract conventions to implement later

- JSON over UTF-8; file upload fields use `multipart/form-data` with the field name `file`.
- Bearer token required except for `/auth/register` and `/auth/login`.
- Roles: `patient` and `doctor`; exercise types: `motor`, `speech`, `memory`; assignment statuses: `new`, `in_progress`, `done`, `overdue`.
- API errors use `{ "detail": "..." }` with the contract's 400, 401, 403, 404, and 422 statuses.
- Doctors can access only their patients; patients can access only their own data. Patient media access is limited to the owner and that patient's doctor.
- Trend is the percent change between the average score of the latest five sessions and the previous five. Completion rate is completed assignments divided by assignments in the period.
