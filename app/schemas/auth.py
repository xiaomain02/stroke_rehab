"""Authentication schemas."""

from typing import Literal

from pydantic import BaseModel, EmailStr, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Literal["patient", "doctor"]
    doctor_id: int | None = None

    @model_validator(mode="after")
    def validate_doctor_link(self):
        if self.role == "doctor" and self.doctor_id is not None:
            raise ValueError("doctor accounts cannot have a doctor_id")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
