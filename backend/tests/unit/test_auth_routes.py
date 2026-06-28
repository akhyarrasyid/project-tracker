import pytest
from fastapi.testclient import TestClient

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from tests.conftest import seed_test_hierarchy


@pytest.fixture
def auth_client(db_session):
    # Clear overrides so that actual dependency flow runs
    app.dependency_overrides.clear()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_login_by_email_success(auth_client, db_session):
    seed = seed_test_hierarchy(db_session)
    user = User(
        email="test_auth@tracker.com",
        username="test_auth",
        full_name="Auth User",
        hashed_password=get_password_hash("pass123"),
        role="worker",
        team_id=seed["team_id"],
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    resp = auth_client.post(
        "/api/v1/auth/login",
        data={"username": "test_auth@tracker.com", "password": "pass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_by_username_success(auth_client, db_session):
    seed = seed_test_hierarchy(db_session)
    user = User(
        email="test_username@tracker.com",
        username="test_username",
        full_name="Auth User 2",
        hashed_password=get_password_hash("pass123"),
        role="worker",
        team_id=seed["team_id"],
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    resp = auth_client.post(
        "/api/v1/auth/login",
        data={"username": "test_username", "password": "pass123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(auth_client, db_session):
    seed = seed_test_hierarchy(db_session)
    user = User(
        email="test_pw@tracker.com",
        username="test_pw",
        full_name="Auth User 3",
        hashed_password=get_password_hash("pass123"),
        role="worker",
        team_id=seed["team_id"],
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    resp = auth_client.post(
        "/api/v1/auth/login",
        data={"username": "test_pw", "password": "wrongpassword"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Incorrect email/username or password"


def test_login_user_inactive(auth_client, db_session):
    seed = seed_test_hierarchy(db_session)
    user = User(
        email="test_inactive@tracker.com",
        username="test_inactive",
        full_name="Inactive User",
        hashed_password=get_password_hash("pass123"),
        role="worker",
        team_id=seed["team_id"],
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    resp = auth_client.post(
        "/api/v1/auth/login",
        data={"username": "test_inactive", "password": "pass123"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "User is inactive"


def test_login_non_existent(auth_client):
    resp = auth_client.post(
        "/api/v1/auth/login",
        data={"username": "doesnotexist", "password": "pass"},
    )
    assert resp.status_code == 400


def test_refresh_token_success(auth_client, db_session):
    seed = seed_test_hierarchy(db_session)
    user = User(
        email="test_refresh@tracker.com",
        username="test_refresh",
        full_name="Refresh User",
        hashed_password=get_password_hash("pass123"),
        role="worker",
        team_id=seed["team_id"],
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    token = create_refresh_token({"sub": str(user.id)})
    resp = auth_client.post(f"/api/v1/auth/refresh?refresh_token={token}")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_token_invalid(auth_client):
    resp = auth_client.post("/api/v1/auth/refresh?refresh_token=invalidtokenhere")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Could not validate credentials"


def test_refresh_token_missing_sub(auth_client):
    token = create_refresh_token({})
    resp = auth_client.post(f"/api/v1/auth/refresh?refresh_token={token}")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid refresh token"


def test_refresh_token_user_not_found(auth_client):
    token = create_refresh_token({"sub": "99999"})
    resp = auth_client.post(f"/api/v1/auth/refresh?refresh_token={token}")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "User not found or inactive"


def test_get_me_success(auth_client, db_session):
    seed = seed_test_hierarchy(db_session)
    user = User(
        email="test_me@tracker.com",
        username="test_me",
        full_name="Me User",
        hashed_password=get_password_hash("pass123"),
        role="worker",
        team_id=seed["team_id"],
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token({"sub": str(user.id)})
    resp = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "test_me"
    assert resp.json()["role"] == "worker"
