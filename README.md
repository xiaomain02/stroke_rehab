# stroke rehab

## Как делать миграции

```bash
cd backend
source .venv/bin/activate
python -m alembic upgrade head
python -m alembic revision --autogenerate -m "describe schema change"
python -m alembic upgrade head
python -m alembic check
```
