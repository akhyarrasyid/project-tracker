from unittest.mock import MagicMock

import app.db.session
from app.db.session import _build_connect_args


def test_get_db(monkeypatch):
    mock_session = MagicMock()
    mock_session_local = MagicMock(return_value=mock_session)
    monkeypatch.setattr(app.db.session, "SessionLocal", mock_session_local)

    db_gen = app.db.session.get_db()
    db = next(db_gen)
    assert db == mock_session

    try:
        next(db_gen)
    except StopIteration:
        pass

    mock_session.close.assert_called_once()


def test_get_task_repository():
    mock_db = MagicMock()
    from app.api.dependencies import get_task_repository

    repo = get_task_repository(mock_db)
    assert repo is not None


def test_build_connect_args_uses_sqlite_thread_flag():
    connect_args = _build_connect_args("sqlite:///./tasks.db", None)
    assert connect_args == {"check_same_thread": False}


def test_build_connect_args_adds_postgres_search_path():
    connect_args = _build_connect_args(
        "postgresql://example:secret@db.example.com/postgres", "test_schema"
    )
    assert connect_args == {"options": "-csearch_path=test_schema"}
