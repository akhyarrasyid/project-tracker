"""Aggregate all API v1 routes into a single router."""
from fastapi import APIRouter

from app.api.v1.task_routes import router as tasks_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(tasks_router)
