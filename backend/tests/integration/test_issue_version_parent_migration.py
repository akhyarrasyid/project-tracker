import importlib
import os
import uuid
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from app.core.config import settings
from tests.conftest import DATABASE_URL

migration_path = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "006_issue_version_parent.py"
)
migration_spec = importlib.util.spec_from_file_location(
    "issue_version_parent_migration", migration_path
)
assert migration_spec is not None and migration_spec.loader is not None
migration_module = importlib.util.module_from_spec(migration_spec)
migration_spec.loader.exec_module(migration_module)


def test_issue_version_parent_migration_backfills_version_and_parent_contract():
    schema = f"issue_parent_{uuid.uuid4().hex}"
    bootstrap_engine = create_engine(DATABASE_URL)
    with bootstrap_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    bootstrap_engine.dispose()

    previous_schema = settings.DATABASE_SCHEMA
    previous_env_schema = os.environ.get("DATABASE_SCHEMA")
    settings.DATABASE_SCHEMA = schema
    os.environ["DATABASE_SCHEMA"] = schema

    schema_engine = create_engine(
        DATABASE_URL,
        connect_args={"options": f"-csearch_path={schema}"},
    )

    try:
        with schema_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE departments (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        description TEXT
                    );
                    CREATE TABLE teams (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
                        description TEXT
                    );
                    CREATE TABLE users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) NOT NULL UNIQUE,
                        username VARCHAR(255) NOT NULL UNIQUE,
                        full_name VARCHAR(255) NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL DEFAULT 'worker',
                        team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        deleted_at TIMESTAMPTZ
                    );
                    CREATE TABLE projects (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        key VARCHAR(10) NOT NULL UNIQUE,
                        description TEXT,
                        team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
                        issue_sequence INTEGER NOT NULL DEFAULT 0,
                        status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE'
                    );
                    CREATE TABLE tasks (
                        id SERIAL PRIMARY KEY,
                        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
                        number INTEGER NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        description TEXT NOT NULL DEFAULT '',
                        status VARCHAR(50) NOT NULL,
                        is_blocked BOOLEAN NOT NULL DEFAULT false,
                        blocked_reason TEXT,
                        priority VARCHAR(50) NOT NULL DEFAULT 'Medium',
                        quarter VARCHAR(5) NOT NULL DEFAULT 'Q1',
                        risk_level VARCHAR(10) NOT NULL DEFAULT 'Low',
                        customer_impact VARCHAR(20) NOT NULL DEFAULT 'None',
                        created_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        due_date DATE NOT NULL,
                        story_points SMALLINT NOT NULL DEFAULT 1,
                        estimated_hours INTEGER NOT NULL DEFAULT 8,
                        actual_hours INTEGER NOT NULL DEFAULT 0,
                        progress_percentage SMALLINT NOT NULL DEFAULT 0,
                        attachments_count SMALLINT NOT NULL DEFAULT 0,
                        comments_count SMALLINT NOT NULL DEFAULT 0,
                        watchers_count SMALLINT NOT NULL DEFAULT 0,
                        sla_hours INTEGER NOT NULL DEFAULT 48,
                        dependencies JSON NOT NULL DEFAULT '[]'::json,
                        tags JSON NOT NULL DEFAULT '[]'::json,
                        rank BIGINT NOT NULL DEFAULT 1024,
                        deleted_at TIMESTAMPTZ
                    );
                    """
                )
            )
            department_id = connection.execute(
                text(
                    "INSERT INTO departments (name, description) VALUES ('Engineering', 'Eng') RETURNING id"
                )
            ).scalar_one()
            team_id = connection.execute(
                text(
                    """
                    INSERT INTO teams (name, department_id, description)
                    VALUES ('Platform', :department_id, 'Platform') RETURNING id
                    """
                ),
                {"department_id": department_id},
            ).scalar_one()
            user_id = connection.execute(
                text(
                    """
                    INSERT INTO users (
                        email, username, full_name, hashed_password, role, team_id, is_active
                    ) VALUES (
                        'admin@tracker.com', 'admin', 'Administrator', 'hashed', 'admin', :team_id, true
                    ) RETURNING id
                    """
                ),
                {"team_id": team_id},
            ).scalar_one()
            project_id = connection.execute(
                text(
                    """
                    INSERT INTO projects (name, key, description, team_id, issue_sequence, status)
                    VALUES ('Migration', 'MIG', 'Migration', :team_id, 2, 'ACTIVE')
                    RETURNING id
                    """
                ),
                {"team_id": team_id},
            ).scalar_one()
            connection.execute(
                text(
                    """
                    INSERT INTO tasks (
                        project_id, number, title, description, status, priority, quarter, risk_level,
                        customer_impact, created_by_id, due_date, story_points, estimated_hours,
                        actual_hours, progress_percentage, attachments_count, comments_count,
                        watchers_count, sla_hours, dependencies, tags, rank
                    ) VALUES
                        (:project_id, 1, 'Parent', 'Parent', 'Todo', 'Medium', 'Q1', 'Low',
                         'None', :user_id, CURRENT_DATE, 3, 8, 0, 0, 0, 0, 0, 48, '[]'::json, '[]'::json, 1024),
                        (:project_id, 2, 'Child', 'Child', 'Todo', 'Medium', 'Q1', 'Low',
                         'None', :user_id, CURRENT_DATE, 3, 8, 0, 0, 0, 0, 0, 48, '[]'::json, '[]'::json, 2048)
                    """
                ),
                {"project_id": project_id, "user_id": user_id},
            )

        with schema_engine.begin() as connection:
            migration_context = MigrationContext.configure(connection)
            operations = Operations(migration_context)
            previous_op = migration_module.op
            migration_module.op = operations
            try:
                migration_module.upgrade()
            finally:
                migration_module.op = previous_op

        with schema_engine.begin() as connection:
            rows = connection.execute(
                text("SELECT number, version, parent_id FROM tasks ORDER BY number")
            ).all()
            index_exists = connection.execute(
                text("SELECT to_regclass(:index_name)"),
                {"index_name": f"{schema}.ix_tasks_parent_id"},
            ).scalar_one()
            constraints = {
                row[0]
                for row in connection.execute(
                    text(
                        """
                        SELECT conname
                        FROM pg_constraint
                        WHERE conname IN ('fk_tasks_parent_id_tasks', 'ck_tasks_parent_not_self')
                        """
                    )
                ).all()
            }

        assert rows == [(1, 1, None), (2, 1, None)]
        assert index_exists == "ix_tasks_parent_id"
        assert constraints == {"fk_tasks_parent_id_tasks", "ck_tasks_parent_not_self"}
    finally:
        settings.DATABASE_SCHEMA = previous_schema
        if previous_env_schema is None:
            os.environ.pop("DATABASE_SCHEMA", None)
        else:
            os.environ["DATABASE_SCHEMA"] = previous_env_schema
        schema_engine.dispose()
        cleanup_engine = create_engine(DATABASE_URL)
        with cleanup_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        cleanup_engine.dispose()
