"""Aggregate API route modules."""

from fastapi import APIRouter

from app.api.routes import assignments, auth, diary, exercises, patients, results

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(auth.profile_router, tags=["auth"])
api_router.include_router(exercises.router, prefix="", tags=["exercises"])
api_router.include_router(assignments.router, prefix="", tags=["assignments"])
api_router.include_router(patients.router, prefix="", tags=["patients"])
api_router.include_router(results.router, prefix="", tags=["results"])
api_router.include_router(diary.router, prefix="", tags=["diary"])
