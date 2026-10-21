"""Authentication and current-user endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import authenticate, create_user, get_current_user, issue_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter()
profile_router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest) -> TokenResponse:
    user = create_user(payload.email, payload.password, payload.full_name, payload.role, payload.doctor_id)
    return TokenResponse(access_token=issue_token(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = authenticate(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    return TokenResponse(access_token=issue_token(user))


@profile_router.get("/me", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**current_user)
