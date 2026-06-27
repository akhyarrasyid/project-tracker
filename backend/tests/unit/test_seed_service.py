"""Unit tests for the seed service."""
import argparse
import sys
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.db.models.task import Task
from app.services import seed_service
from tests.conftest import TestingSessionLocal, VALID_TASK_PAYLOAD


@pytest.fixture(autouse=True)
def mock_session_local(monkeypatch, db_session):
    class MockSessionLocal:
        def __init__(self):
            pass
        def __getattr__(self, name):
            if name == "close":
                return lambda: None
            return getattr(db_session, name)
    monkeypatch.setattr("app.services.seed_service.SessionLocal", MockSessionLocal)


@pytest.fixture
def mock_records():
    return [
        {**VALID_TASK_PAYLOAD, "id": 1, "title": "Task 1"},
        {**VALID_TASK_PAYLOAD, "id": 2, "title": "Task 2"},
    ]


@pytest.fixture
def mock_invalid_records():
    return [
        {**VALID_TASK_PAYLOAD, "id": 1, "title": "Task 1"},
        {**VALID_TASK_PAYLOAD, "id": 2, "title": "", "story_points": 4},  # empty title & invalid SP
    ]


def test_validate_records_success(mock_records):
    valid, errors = seed_service._validate_records(mock_records)
    assert len(valid) == 2
    assert len(errors) == 0
    assert valid[0]["title"] == "Task 1"
    assert valid[1]["title"] == "Task 2"


def test_validate_records_with_errors(mock_invalid_records):
    valid, errors = seed_service._validate_records(mock_invalid_records)
    assert len(valid) == 1
    assert len(errors) == 1
    assert errors[0]["index"] == 1
    assert errors[0]["id"] == 2
    assert len(errors[0]["errors"]) > 0


def test_cmd_validate_success(mock_records):
    with pytest.raises(SystemExit) as excinfo:
        seed_service.cmd_validate(mock_records)
    assert excinfo.value.code == 0


def test_cmd_validate_failure(mock_invalid_records):
    with pytest.raises(SystemExit) as excinfo:
        seed_service.cmd_validate(mock_invalid_records)
    assert excinfo.value.code == 1


def test_cmd_dry_run(mock_invalid_records):
    with pytest.raises(SystemExit) as excinfo:
        seed_service.cmd_dry_run(mock_invalid_records)
    assert excinfo.value.code == 0


def test_cmd_seed_success(mock_records, db_session):
    # Verify no tasks originally
    assert db_session.query(Task).count() == 0

    # Seed
    seed_service.cmd_seed(mock_records)

    # Verify tasks are inserted
    assert db_session.query(Task).count() == 2
    t1 = db_session.query(Task).filter(Task.id == 1).first()
    assert t1.title == "Task 1"


def test_cmd_seed_no_valid_records(mock_invalid_records):
    invalid_only = [mock_invalid_records[1]]
    with pytest.raises(SystemExit) as excinfo:
        seed_service.cmd_seed(invalid_only)
    assert excinfo.value.code == 1


def test_cmd_seed_idempotency(mock_records, db_session):
    # Seed once
    seed_service.cmd_seed(mock_records)
    assert db_session.query(Task).count() == 2

    # Seed again (should skip existing)
    seed_service.cmd_seed(mock_records)
    assert db_session.query(Task).count() == 2


def test_cmd_seed_db_error(mock_records, monkeypatch):
    def mock_bulk_save(*args, **kwargs):
        raise Exception("DB Error")

    # Patch bulk_save_objects to raise an exception
    monkeypatch.setattr("sqlalchemy.orm.Session.bulk_save_objects", mock_bulk_save)

    with pytest.raises(SystemExit) as excinfo:
        seed_service.cmd_seed(mock_records)
    assert excinfo.value.code == 1


def test_cmd_reset_success(mock_records, db_session):
    # Seed initially
    seed_service.cmd_seed(mock_records)
    assert db_session.query(Task).count() == 2

    # Reset with same records
    seed_service.cmd_reset(mock_records)
    assert db_session.query(Task).count() == 2



def test_cmd_reset_db_error(mock_records, monkeypatch):
    def mock_delete(*args, **kwargs):
        raise Exception("Delete Error")

    # Patch delete query to raise exception
    monkeypatch.setattr("sqlalchemy.orm.query.Query.delete", mock_delete)

    with pytest.raises(SystemExit) as excinfo:
        seed_service.cmd_reset(mock_records)
    assert excinfo.value.code == 1


def test_load_seed_data_missing_file(monkeypatch):
    monkeypatch.setattr("app.services.seed_service.SEED_FILE", seed_service.Path("nonexistent_file.json"))
    with pytest.raises(SystemExit) as excinfo:
        seed_service._load_seed_data()
    assert excinfo.value.code == 1


def test_load_seed_data_success():
    data = seed_service._load_seed_data()
    assert isinstance(data, list)
    assert len(data) == 500


@patch("argparse.ArgumentParser.parse_args")
@patch("app.services.seed_service._load_seed_data")
@patch("app.services.seed_service.cmd_validate")
def test_main_validate(mock_cmd_validate, mock_load, mock_parse, mock_records):
    mock_load.return_value = mock_records
    mock_parse.return_value = argparse.Namespace(validate=True, dry_run=False, seed=False, reset=False)
    seed_service.main()
    mock_cmd_validate.assert_called_once_with(mock_records)


@patch("argparse.ArgumentParser.parse_args")
@patch("app.services.seed_service._load_seed_data")
@patch("app.services.seed_service.cmd_dry_run")
def test_main_dry_run(mock_cmd_dry_run, mock_load, mock_parse, mock_records):
    mock_load.return_value = mock_records
    mock_parse.return_value = argparse.Namespace(validate=False, dry_run=True, seed=False, reset=False)
    seed_service.main()
    mock_cmd_dry_run.assert_called_once_with(mock_records)


@patch("argparse.ArgumentParser.parse_args")
@patch("app.services.seed_service._load_seed_data")
@patch("app.services.seed_service.cmd_seed")
def test_main_seed(mock_cmd_seed, mock_load, mock_parse, mock_records):
    mock_load.return_value = mock_records
    mock_parse.return_value = argparse.Namespace(validate=False, dry_run=False, seed=True, reset=False)
    seed_service.main()
    mock_cmd_seed.assert_called_once_with(mock_records)


@patch("argparse.ArgumentParser.parse_args")
@patch("app.services.seed_service._load_seed_data")
@patch("app.services.seed_service.cmd_reset")
def test_main_reset(mock_cmd_reset, mock_load, mock_parse, mock_records):
    mock_load.return_value = mock_records
    mock_parse.return_value = argparse.Namespace(validate=False, dry_run=False, seed=False, reset=True)
    seed_service.main()
    mock_cmd_reset.assert_called_once_with(mock_records)
