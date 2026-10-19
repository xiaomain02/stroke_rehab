"""Authentication and current-user endpoints."""

from fastapi import APIRouter

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter()
profile_router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest) -> TokenResponse:
    ...


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    ...


@profile_router.get("/me", response_model=UserResponse)
def get_current_user() -> UserResponse:
    ...
