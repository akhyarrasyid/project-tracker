import importlib
import os
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from app.core.config import settings
from tests.conftest import DATABASE_URL

blocked_flag_migration_path = (
    Path(__file__).resolve().parents[2] / "alembic" / "versions" / "004_blocked_flag.py"
)
blocked_flag_migration_spec = importlib.util.spec_from_file_location(
    "blocked_flag_migration", blocked_flag_migration_path
)
assert (
    blocked_flag_migration_spec is not None
    and blocked_flag_migration_spec.loader is not None
)
blocked_flag_migration = importlib.util.module_from_spec(blocked_flag_migration_spec)
blocked_flag_migration_spec.loader.exec_module(blocked_flag_migration)


def test_blocked_status_migration_backfills_flag_and_status():
    schema = f"mig_{uuid.uuid4().hex}"
    bootstrap_engine = create_engine(DATABASE_URL)
    with bootstrap_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    bootstrap_engine.dispose()

    previous_schema = settings.DATABASE_SCHEMA
    previous_env_schema = os.environ.get("DATABASE_SCHEMA")
    settings.DATABASE_SCHEMA = schema
    os.environ["DATABASE_SCHEMA"] = schema

    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))

    schema_engine = create_engine(
        DATABASE_URL,
        connect_args={"options": f"-csearch_path={schema}"},
    )

    try:
        command.upgrade(config, "003_issue_identity")

        with schema_engine.begin() as connection:
            team_id = connection.execute(
                text("SELECT id FROM teams ORDER BY id LIMIT 1")
            ).scalar()
            if team_id is None:
                department_id = connection.execute(
                    text(
                        """
                        INSERT INTO departments (name, description)
                        VALUES ('Engineering', 'Engineering')
                        RETURNING id
                        """
                    )
                ).scalar_one()
                team_id = connection.execute(
                    text(
                        """
                        INSERT INTO teams (name, department_id, description)
                        VALUES ('Backend Team', :department_id, 'Backend Team')
                        RETURNING id
                        """
                    ),
                    {"department_id": department_id},
                ).scalar_one()

            user_id = connection.execute(
                text("SELECT id FROM users WHERE username = 'admin'")
            ).scalar()
            if user_id is None:
                user_id = connection.execute(
                    text(
                        """
                        INSERT INTO users (
                            email, username, full_name, hashed_password, role, team_id, is_active
                        ) VALUES (
                            'admin@tracker.com', 'admin', 'Administrator', 'hashed', 'admin', :team_id, true
                        )
                        RETURNING id
                        """
                    ),
                    {"team_id": team_id},
                ).scalar_one()

            project_id = connection.execute(
                text("SELECT id FROM projects ORDER BY id LIMIT 1")
            ).scalar()
            if project_id is None:
                project_id = connection.execute(
                    text(
                        """
                        INSERT INTO projects (name, key, description, team_id, issue_sequence, status)
                        VALUES ('Migration Project', 'MIG', 'Migration Project', :team_id, 1, 'ACTIVE')
                        RETURNING id
                        """
                    ),
                    {"team_id": team_id},
                ).scalar_one()
            connection.execute(text("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_status"))
            connection.execute(
                text(
                    """
                    ALTER TABLE tasks
                    ADD CONSTRAINT ck_tasks_status
                    CHECK (status IN ('Todo', 'In Progress', 'Review', 'Done', 'Blocked'))
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO tasks (
                        project_id, sprint_id, epic_id, number, title, description, status,
                        priority, quarter, risk_level, customer_impact, assignee_id,
                        created_by_id, due_date, story_points, estimated_hours,
                        actual_hours, progress_percentage, attachments_count,
                        comments_count, watchers_count, sla_hours, dependencies, tags
                    ) VALUES (
                        :project_id, NULL, NULL, 1, 'Legacy blocked', 'Needs migration', 'Blocked',
                        'High', 'Q1', 'High', 'Low', NULL,
                        :user_id, CURRENT_DATE, 3, 8,
                        0, 40, 0,
                        0, 0, 48, '[]'::json, '[]'::json
                    )
                    """
                ),
                {"project_id": project_id, "user_id": user_id},
            )
            task_id = connection.execute(
                text("SELECT id FROM tasks WHERE project_id = :project_id AND number = 1"),
                {"project_id": project_id},
            ).scalar_one()
            connection.execute(
                text(
                    """
                    INSERT INTO activity_logs (
                        task_id, project_id, actor_id, action, field, old_value, new_value
                    ) VALUES (
                        :task_id, :project_id, :actor_id, 'Status Changed',
                        'status', 'Review', 'Blocked'
                    )
                    """
                ),
                {"task_id": task_id, "project_id": project_id, "actor_id": user_id},
            )

        with schema_engine.begin() as connection:
            migration_context = MigrationContext.configure(connection)
            operations = Operations(migration_context)
            previous_op = blocked_flag_migration.op
            blocked_flag_migration.op = operations
            try:
                blocked_flag_migration.upgrade()
            finally:
                blocked_flag_migration.op = previous_op

        with schema_engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT status, is_blocked, blocked_reason
                    FROM tasks
                    WHERE title = 'Legacy blocked'
                    """
                )
            ).one()
            assert row.status == "Review"
            assert row.is_blocked is True
            assert row.blocked_reason == "Migrated from legacy blocked status"
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
