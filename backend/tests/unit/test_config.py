import pytest
from pydantic_core import ValidationError

from app.core.config import Settings


def test_runtime_settings_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="DATABASE_URL is required for runtime application startup"):
        Settings(_env_file=None)


def test_effective_cors_origins_always_include_frontend_domain():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://user:pass@127.0.0.1:5432/project_tracker",
        CORS_ORIGINS=["https://custom.example.com"],
    )

    assert "https://technical-test-project-tracker.vercel.app" in settings.effective_cors_origins
    assert "http://localhost:5173" in settings.effective_cors_origins
    assert "https://custom.example.com" in settings.effective_cors_origins
