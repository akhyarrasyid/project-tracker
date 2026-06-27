from pathlib import Path

from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "sqlite:///./tasks.db"
    CORS_ORIGINS: list[str] = ["*"]
    APP_TITLE: str = "Project Tracker API"
    APP_VERSION: str = "1.0.0"

    model_config = {
        "env_file": (BACKEND_DIR / ".env", PROJECT_ROOT / ".env"),
        "extra": "ignore",
    }


settings = Settings()
