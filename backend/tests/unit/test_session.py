from unittest.mock import MagicMock
import app.db.session
from app.db.session import get_db


def test_get_db(monkeypatch):
    mock_session = MagicMock()
    mock_session_local = MagicMock(return_value=mock_session)
    monkeypatch.setattr(app.db.session, "SessionLocal", mock_session_local)

    db_gen = get_db()
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

