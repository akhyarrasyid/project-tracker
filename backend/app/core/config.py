from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str | None = None
    DATABASE_SCHEMA: str | None = None
    ENVIRONMENT: str = "development"
    DEBUG: str = "false"
    CORS_ORIGINS: list[str] = ["*"]
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


settings = Settings()
