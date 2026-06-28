from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core import security
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from tests.conftest import seed_test_hierarchy


def test_verify_password_exception():
    # Pass invalid values to trigger verify exception
    assert security.verify_password("", None) is False


def test_create_access_token_custom_expiry():
    token = security.create_access_token(
        {"sub": "123"}, expires_delta=timedelta(minutes=5)
    )
    payload = security.decode_token(token)
    assert payload["sub"] == "123"


def test_create_refresh_token_custom_expiry():
    token = security.create_refresh_token(
        {"sub": "123"}, expires_delta=timedelta(days=1)
    )
    payload = security.decode_token(token)
    assert payload["sub"] == "123"


def test_decode_token_invalid():
    with pytest.raises(HTTPException) as exc:
        security.decode_token("completelyinvalidtoken")
    assert exc.value.status_code == 401


def test_get_current_user_inactive(db_session):
    seed = seed_test_hierarchy(db_session)
    # Set user inactive
    seed["worker"].is_active = False
    db_session.commit()

    token = security.create_access_token({"sub": str(seed["worker"].id)})
    with pytest.raises(HTTPException) as exc:
        security.get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Inactive user"


def test_check_project_access_not_found(db_session):
    seed = seed_test_hierarchy(db_session)
    with pytest.raises(HTTPException) as exc:
        security.check_project_access(db_session, seed["admin"], 99999)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Project not found"


def test_check_project_access_not_member(db_session):
    seed = seed_test_hierarchy(db_session)
    # Create project with no members
    proj = Project(
        name="Private Proj",
        key="PRV",
        description="Private",
        team_id=seed["team_id"],
        status="ACTIVE",
    )
    db_session.add(proj)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        security.check_project_access(db_session, seed["worker"], proj.id)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Not a project member"


def test_check_project_access_insufficient_permissions(db_session):
    seed = seed_test_hierarchy(db_session)
    # Create project and add worker as VIEWER
    proj = Project(
        name="Review Proj",
        key="REV",
        description="Review",
        team_id=seed["team_id"],
        status="ACTIVE",
    )
    db_session.add(proj)
    db_session.commit()

    pm = ProjectMember(
        project_id=proj.id, user_id=seed["worker"].id, project_role="VIEWER"
    )
    db_session.add(pm)
    db_session.commit()

    # Worker accesses with VIEWER role -> OK
    assert (
        security.check_project_access(
            db_session, seed["worker"], proj.id, min_role="VIEWER"
        )
        == proj
    )

    # Worker accesses with MEMBER (default min_role is MEMBER) -> forbidden
    with pytest.raises(HTTPException) as exc:
        security.check_project_access(
            db_session, seed["worker"], proj.id, min_role="MEMBER"
        )
    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient project permissions"


def test_get_current_user_no_sub(db_session):
    # token with no "sub"
    token = security.create_access_token({})
    with pytest.raises(HTTPException) as exc:
        security.get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


def test_get_current_user_not_found(db_session):
    # token with sub pointing to non-existent ID
    token = security.create_access_token({"sub": "99999"})
    with pytest.raises(HTTPException) as exc:
        security.get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


def test_get_current_user_invalid_token(db_session):
    with pytest.raises(HTTPException) as exc:
        security.get_current_user(token="completelyinvalidtoken", db=db_session)
    assert exc.value.status_code == 401
