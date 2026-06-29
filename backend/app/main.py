"""FastAPI application factory."""

import app.db.models  # noqa: F401
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.db.session import engine


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        description="Enterprise Project Tracker API for operational issue management.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "status_code": exc.status_code,
                "error_type": "not_found",
            },
        )

    @app.exception_handler(ValidationException)
    async def validation_handler(request: Request, exc: ValidationException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "status_code": exc.status_code,
                "error_type": "validation_error",
            },
        )

    app.include_router(api_router)

    @app.get("/health", tags=["ops"], summary="Liveness check")
    async def health():
        return {"status": "healthy", "version": settings.APP_VERSION}

    @app.get("/readiness", tags=["ops"], summary="Readiness check (DB)")
    async def readiness():
        try:
            from sqlalchemy import text

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception as exc:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "detail": str(exc)},
            )

    return app


app = create_app()
