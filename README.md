# Фронт врача и администратора

    cp .env.example .env
    npm install
    npm run dev

`VITE_MOCK=true` - работает без бэкенда. Тестовые входы (пароль любой):
- `doctor@x.ru` - врач
- `admin@x.ru` - администратор больницы (создаёт врачей)
- `new@x.ru` - врач с временным паролем (покажет экран смены пароля)

Самостоятельной регистрации нет: врачей создаёт администратор, пациентов создаёт врач.
Для подключения бэка: `VITE_MOCK=false`, `VITE_API_URL=<адрес FastAPI>`. Полный контракт в `api-contract.xlsx`.

## Backend authentication

The FastAPI backend stores accounts, exercises, assignments, results, diary entries, and uploaded media in
`auth.sqlite3` (override with `AUTH_DATABASE_PATH`). It seeds a small exercise catalog on first use.
Set `AUTH_SECRET` in the backend process environment to a long random secret before deploying. The
development fallback secret is for local use only. Login and registration return signed bearer tokens
that expire after one hour. Protected requests must send `Authorization: Bearer <access_token>`.

Patient accounts can be linked to a doctor at registration with `doctor_id`. Doctor patient lists,
assignments, patient statistics, results, diaries, and media enforce that relationship. Uploaded media
is limited to 50 MB per file; media URLs require the same bearer token as API requests.

## Setup and startup (Windows PowerShell)

Run these commands from the project root. You need Python, Node.js, and npm installed.

### 1. Install backend dependencies

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configure and start the backend

Open a PowerShell terminal in the project root and run:

```powershell
$env:AUTH_SECRET = "replace-this-with-a-long-random-secret"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep this terminal open. The API is available at `http://127.0.0.1:8000`; interactive API docs are at
`http://127.0.0.1:8000/docs`. On first use, the backend creates `auth.sqlite3` in the project root.
Set `AUTH_DATABASE_PATH` in this terminal before starting the backend to use a different database file.
The backend reads these variables from its process environment; it does not load them from the Vite `.env` file.

### 3. Configure and start the frontend

Open a second PowerShell terminal in the project root:

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

For the live backend, edit `.env` and set:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
VITE_MOCK=false
```

Vite prints the frontend URL in the terminal, usually `http://localhost:5173`. Keep both terminals running.
For mock mode, set `VITE_MOCK=true`; the frontend then uses sample data and does not need the backend.
