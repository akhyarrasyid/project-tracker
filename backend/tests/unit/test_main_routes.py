from unittest.mock import MagicMock

from app.core.exceptions import ValidationException
from app.main import app, engine


def test_validation_handler(client):
    # Dynamically add a temporary route to test the handler
    @app.get("/test-val-error-handler")
    def route():
        raise ValidationException("Test validation error")

    resp = client.get("/test-val-error-handler")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Test validation error"
    assert resp.json()["error_type"] == "validation_error"


def test_health_does_not_touch_database(client, monkeypatch):
    connect_spy = MagicMock()
    monkeypatch.setattr(engine, "connect", connect_spy)

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    connect_spy.assert_not_called()


def test_docs_route_is_available(client):
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_readiness_error(client, monkeypatch):
    def mock_connect():
        raise Exception("DB Down")

    monkeypatch.setattr(engine, "connect", mock_connect)

    resp = client.get("/readiness")
    assert resp.status_code == 503
    assert resp.json()["status"] == "unavailable"
    assert resp.json()["detail"] == "Database connection failed"
    assert resp.json()["error_type"] == "Exception"
