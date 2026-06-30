import os
import sys
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tests.support.db_env import (
    assert_safe_test_database_url,
    derive_admin_database_url,
    load_supabase_database_url,
    load_test_database_url,
)


def test_load_test_database_url_prefers_explicit_test_value(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://remote.example.com/project_tracker\n"
        "TEST_DATABASE_URL=postgresql://localhost/project_tracker_test\n",
        encoding="utf-8",
    )

    database_url = load_test_database_url({}, (env_file,))

    assert database_url == "postgresql://localhost/project_tracker_test"


def test_load_test_database_url_does_not_fall_back_to_general_database_url(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://remote.example.com/project_tracker\n",
        encoding="utf-8",
    )

    database_url = load_test_database_url({}, (env_file,))

    assert (
        database_url
        == "postgresql://project_tracker_test:project_tracker_test@127.0.0.1:55432/project_tracker_test"
    )


def test_assert_safe_test_database_url_rejects_remote_without_opt_in():
    with pytest.raises(RuntimeError, match="remote PostgreSQL host"):
        assert_safe_test_database_url(
            "postgresql://postgres:postgres@aws-1-ap-northeast-1.pooler.supabase.com:5432/project_tracker_test"
        )


def test_assert_safe_test_database_url_rejects_non_test_database_name():
    with pytest.raises(RuntimeError, match="non-test database"):
        assert_safe_test_database_url(
            "postgresql://postgres:postgres@localhost:5432/project_tracker"
        )


def test_derive_admin_database_url_uses_postgres_database():
    admin_url = derive_admin_database_url(
        "postgresql://postgres:postgres@localhost:5432/project_tracker_test"
    )

    parsed = make_url(admin_url)
    assert parsed.database == "postgres"
    assert parsed.host == "localhost"


def test_load_supabase_database_url_uses_explicit_value(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SUPABASE_DATABASE_URL=postgresql://remote.example.com/postgres\n",
        encoding="utf-8",
    )

    supabase_url = load_supabase_database_url({}, (env_file,))

    assert supabase_url == "postgresql://remote.example.com/postgres"
