import os
import re
from pathlib import Path
from typing import Mapping, Sequence

from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

DEFAULT_TEST_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5432/project_tracker_test"
DEFAULT_ALLOWED_LOCAL_HOSTS = {"localhost", "127.0.0.1", "db", "postgres"}
DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def _read_env_value(env_files: Sequence[Path], key: str) -> str | None:
    for env_path in env_files:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            current_key, value = line.split("=", 1)
            if current_key.strip() == key:
                return value.strip()
    return None


def load_test_database_url(
    env: Mapping[str, str],
    env_files: Sequence[Path],
) -> str:
    return (
        env.get("TEST_DATABASE_URL")
        or _read_env_value(env_files, "TEST_DATABASE_URL")
        or DEFAULT_TEST_DATABASE_URL
    )


def load_supabase_database_url(
    env: Mapping[str, str],
    env_files: Sequence[Path],
) -> str | None:
    return (
        env.get("SUPABASE_DATABASE_URL")
        or _read_env_value(env_files, "SUPABASE_DATABASE_URL")
        or env.get("DATABASE_URL")
        or _read_env_value(env_files, "DATABASE_URL")
    )


def derive_admin_database_url(
    database_url: str,
    explicit_admin_url: str | None = None,
) -> str:
    if explicit_admin_url:
        return explicit_admin_url

    parsed = make_url(database_url)
    return str(parsed.set(database="postgres"))


def assert_safe_test_database_url(
    database_url: str,
    *,
    allow_remote: bool = False,
    allowed_local_hosts: set[str] | None = None,
) -> URL:
    parsed = make_url(database_url)
    allowed_hosts = allowed_local_hosts or DEFAULT_ALLOWED_LOCAL_HOSTS
    host = parsed.host or "localhost"
    database_name = parsed.database or ""

    if not allow_remote and host not in allowed_hosts:
        raise RuntimeError(
            "Refusing to run backend tests against a remote PostgreSQL host. "
            "Set TEST_DATABASE_URL to a local PostgreSQL database, or set "
            "ALLOW_REMOTE_TEST_DATABASE=1 only for explicit Supabase verification."
        )

    if not DATABASE_NAME_PATTERN.match(database_name):
        raise RuntimeError(
            f"Unsafe test database name '{database_name}'. Use only letters, numbers, and underscores."
        )

    if not allow_remote and "test" not in database_name.lower():
        raise RuntimeError(
            "Refusing to run backend tests against a non-test database. "
            "Use a dedicated *_test database name."
        )

    return parsed


def ensure_database_exists(database_url: str, admin_database_url: str) -> None:
    parsed = assert_safe_test_database_url(database_url, allow_remote=False)
    database_name = parsed.database
    assert database_name is not None

    admin_engine = create_engine(admin_database_url, isolation_level="AUTOCOMMIT")
    try:
        try:
            with admin_engine.connect() as connection:
                exists = connection.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                    {"database_name": database_name},
                ).scalar()
                if exists:
                    return
                connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        except OperationalError as exc:
            raise RuntimeError(
                "Unable to connect to the local PostgreSQL test server using "
                f"TEST_DATABASE_ADMIN_URL='{admin_database_url}'. "
                "Set TEST_DATABASE_URL / TEST_DATABASE_ADMIN_URL to valid local credentials, "
                "or start the local PostgreSQL service before running tests."
            ) from exc
    finally:
        admin_engine.dispose()


def test_mode_allows_remote_database(env: Mapping[str, str] | None = None) -> bool:
    source = env if env is not None else os.environ
    return source.get("ALLOW_REMOTE_TEST_DATABASE", "0") == "1"
