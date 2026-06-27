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


def test_readiness_error(client, monkeypatch):
    def mock_connect():
        raise Exception("DB Down")

    monkeypatch.setattr(engine, "connect", mock_connect)

    resp = client.get("/readiness")
    assert resp.status_code == 503
    assert resp.json()["status"] == "unavailable"
    assert "DB Down" in resp.json()["detail"]
