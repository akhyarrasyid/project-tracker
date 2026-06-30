import pytest
from pydantic_core import ValidationError

from app.core.config import Settings


def test_runtime_settings_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="DATABASE_URL is required for runtime application startup"):
        Settings(_env_file=None)
