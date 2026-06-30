from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "https://technical-test-project-tracker.vercel.app",
]
VERCEL_FRONTEND_ORIGIN_REGEX = (
    r"^https://technical-test-project-tracker(?:-[a-z0-9-]+)*\.vercel\.app$"
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str | None = None
    DATABASE_SCHEMA: str | None = None
    ENVIRONMENT: str = "development"
    DEBUG: str = "false"
    CORS_ORIGINS: list[str] = DEFAULT_CORS_ORIGINS.copy()
    APP_TITLE: str = "Project Tracker API"
    APP_VERSION: str = "1.0.0"

    SECRET_KEY: str = "supersecretkeychangeinproduction"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = {
        "env_file": (BACKEND_DIR / ".env", PROJECT_ROOT / ".env"),
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def validate_database_url(self) -> "Settings":
        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL is required for runtime application startup. "
                "Use a local PostgreSQL URL for development and a Supabase Transaction "
                "Pooler URL for Vercel production."
            )
        return self

    @property
    def effective_cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS if origin.strip()]
        merged: list[str] = []
        for origin in [*DEFAULT_CORS_ORIGINS, *origins]:
            if origin not in merged:
                merged.append(origin)
        return merged

    @property
    def vercel_frontend_origin_regex(self) -> str:
        return VERCEL_FRONTEND_ORIGIN_REGEX


settings = Settings()
