"""Password, token, and request authorization helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.repositories.database import connect

_bearer = HTTPBearer(auto_error=False)
_iterations = 310_000
_secret = os.environ.get("AUTH_SECRET", "local-development-secret-change-before-deployment").encode()


def create_user(email: str, password: str, full_name: str, role: str, doctor_id: int | None = None) -> dict[str, Any]:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _iterations)
    encoded = f"{_iterations}${_b64(salt)}${_b64(digest)}"
    with connect() as db:
        if doctor_id is not None:
            doctor = db.execute("SELECT role FROM users WHERE id = ?", (doctor_id,)).fetchone()
            if doctor is None or doctor["role"] != "doctor":
                raise HTTPException(status_code=400, detail="doctor_id must refer to an existing doctor")
        try:
            cursor = db.execute(
                "INSERT INTO users(email, full_name, role, doctor_id, password_hash) VALUES (?, ?, ?, ?, ?)",
                (email.strip().lower(), full_name.strip(), role, doctor_id, encoded),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="Email is already registered") from exc
        return _public_user(db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)).fetchone()
    if row is None:
        return None
    try:
        iterations, salt, expected = row["password_hash"].split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(iterations))
    except (ValueError, TypeError):
        return None
    return _public_user(row) if hmac.compare_digest(actual, _unb64(expected)) else None


def issue_token(user: dict[str, Any], expires_in: int = 3600) -> str:
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": user["id"], "iat": now, "exp": now + expires_in}, separators=(",", ":")).encode())
    message = f"{header}.{payload}"
    signature = _b64(hmac.new(_secret, message.encode(), hashlib.sha256).digest())
    return f"{message}.{signature}"


def _decode_token(token: str) -> int:
    try:
        header, payload, signature = token.split(".")
        expected = _b64(hmac.new(_secret, f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature):
            raise ValueError
        claims = json.loads(_unb64(payload))
        if claims["exp"] <= time.time() or not isinstance(claims["sub"], int):
            raise ValueError
        return claims["sub"]
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authentication token", headers={"WWW-Authenticate": "Bearer"})


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token", headers={"WWW-Authenticate": "Bearer"})
    user_id = _decode_token(credentials.credentials)
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="User no longer exists", headers={"WWW-Authenticate": "Bearer"})
    return _public_user(row)


def require_roles(*roles: str):
    def check(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to access this resource")
        return current_user
    return check


def assert_patient_access(patient_id: int, current_user: dict[str, Any]) -> None:
    with connect() as db:
        patient = db.execute("SELECT role, doctor_id FROM users WHERE id = ?", (patient_id,)).fetchone()
    if patient is None or patient["role"] != "patient":
        raise HTTPException(status_code=404, detail="Patient not found")
    if current_user["role"] == "patient":
        allowed = current_user["id"] == patient_id
    else:
        allowed = patient["doctor_id"] == current_user["id"]
    if not allowed:
        raise HTTPException(status_code=403, detail="You do not have access to this patient's data")


def require_patient_access(patient_id: int, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    assert_patient_access(patient_id, current_user)
    return current_user


def _public_user(row) -> dict[str, Any]:
    return {"id": row["id"], "full_name": row["full_name"], "email": row["email"], "role": row["role"], "doctor_id": row["doctor_id"]}


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
