"""Application entry point."""

from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(title="Stroke Rehab API")
app.include_router(api_router)
