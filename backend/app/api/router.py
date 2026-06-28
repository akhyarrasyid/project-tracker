"""Aggregate all API v1 routes into a single router."""
from fastapi import APIRouter

from app.api.v1.task_routes import router as tasks_router
from app.api.v1.auth_routes import router as auth_router
from app.api.v1.project_routes import router as projects_router
from app.api.v1.meta_routes import router as meta_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(meta_router)
api_router.include_router(tasks_router)
