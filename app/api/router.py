"""Aggregate API route modules."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.api.routes import assignments, auth, diary, exercises, patients, results

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(auth.profile_router, tags=["auth"])
protected = [Depends(get_current_user)]
api_router.include_router(exercises.router, prefix="", tags=["exercises"], dependencies=protected)
api_router.include_router(assignments.router, prefix="", tags=["assignments"], dependencies=protected)
api_router.include_router(patients.router, prefix="", tags=["patients"], dependencies=protected)
api_router.include_router(results.router, prefix="", tags=["results"], dependencies=protected)
api_router.include_router(diary.router, prefix="", tags=["diary"], dependencies=protected)
