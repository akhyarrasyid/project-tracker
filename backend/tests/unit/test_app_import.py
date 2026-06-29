import importlib
import sys
from unittest.mock import MagicMock, patch


def test_importing_app_does_not_connect_or_run_ddl(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://project_tracker_test:project_tracker_test@127.0.0.1:55432/project_tracker_test",
    )

    for module_name in ("app.main", "app.db.session", "app.core.config"):
        sys.modules.pop(module_name, None)

    fake_engine = MagicMock()
    fake_engine.connect = MagicMock()

    with patch("sqlalchemy.create_engine", return_value=fake_engine):
        with patch("sqlalchemy.schema.MetaData.create_all") as mock_create_all:
            module = importlib.import_module("app.main")

    assert module.app is not None
    fake_engine.connect.assert_not_called()
    mock_create_all.assert_not_called()
