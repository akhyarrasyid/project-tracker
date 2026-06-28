"""Evolve schema to project hierarchy and normalize tables.

Revision ID: 002_core_hierarchy
Revises: 001_initial_tasks
Create Date: 2026-06-28 08:30:00.000000
"""
from typing import Sequence, Union, Dict
import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision: str = "002_core_hierarchy"
down_revision: Union[str, None] = "001_initial_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    # 1. Create New Tables
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name")
    )
    op.create_index("ix_departments_name", "departments", ["name"], unique=True)

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "department_id", name="uq_team_name_department")
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="worker"),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=10), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key")
    )
    op.create_index("ix_projects_key", "projects", ["key"], unique=True)

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_role", sa.String(length=50), nullable=False, server_default="MEMBER"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member")
    )

    op.create_table(
        "sprints",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PLANNED"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_table(
        "epics",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.id"], ondelete="SET NULL"),
        # Foreign key for task_id will be added after tasks table update
        sa.PrimaryKeyConstraint("id")
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_table(
        "watchers",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "task_id")
    )

    op.create_table(
        "labels",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False, server_default="#6B7280"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name")
    )

    op.create_table(
        "task_labels",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["label_id"], ["labels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "label_id")
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("field", sa.String(length=100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id")
    )

    # 2. Add temporary nullable columns to tasks for migration
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("sprint_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("epic_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("assignee_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("completed_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_by_id", sa.Integer(), nullable=True))

    # 3. Data Migration
    connection = op.get_bind()
    
    # Check if there are tasks to migrate
    tasks_raw = connection.execute(sa.text("SELECT id, department, team, assignee, created_by, sprint FROM tasks")).fetchall()
    
    # If DB is empty (like in tests), we pre-seed default records
    departments_to_insert = set()
    teams_to_insert = set() # (team_name, department_name)
    users_to_insert = set() # full_name
    
    for t in tasks_raw:
        dept = t[1] or "Engineering"
        team = t[2] or "Backend Team"
        assignee = t[3]
        creator = t[4] or "admin"
        
        departments_to_insert.add(dept)
        teams_to_insert.add((team, dept))
        if assignee:
            users_to_insert.add(assignee)
        if creator:
            users_to_insert.add(creator)

    # Add defaults just in case
    if not departments_to_insert:
        departments_to_insert.add("Engineering")
    if not teams_to_insert:
        teams_to_insert.add(("Backend Team", "Engineering"))
    users_to_insert.add("admin")
    users_to_insert.add("worker")

    # Insert Departments
    dept_ids: Dict[str, int] = {}
    for dept in departments_to_insert:
        connection.execute(
            sa.text("INSERT INTO departments (name) VALUES (:name) ON CONFLICT(name) DO NOTHING"),
            {"name": dept}
        )
        res = connection.execute(sa.text("SELECT id FROM departments WHERE name = :name"), {"name": dept}).fetchone()
        dept_ids[dept] = res[0]

    # Insert Teams
    team_ids: Dict[str, int] = {}
    for team, dept in teams_to_insert:
        dept_id = dept_ids[dept]
        connection.execute(
            sa.text("INSERT INTO teams (name, department_id) VALUES (:name, :dept_id) ON CONFLICT DO NOTHING"),
            {"name": team, "dept_id": dept_id}
        )
        res = connection.execute(
            sa.text("SELECT id FROM teams WHERE name = :name AND department_id = :dept_id"),
            {"name": team, "dept_id": dept_id}
        ).fetchone()
        team_ids[team] = res[0]

    # Insert Users
    user_ids: Dict[str, int] = {}
    hashed_pwd = pwd_context.hash("password123")
    
    # Ensure team for default users
    default_team_id = list(team_ids.values())[0]

    for user_name in users_to_insert:
        username = user_name.replace(" ", ".").lower()
        email = f"{username}@tracker.com"
        role = "admin" if "admin" in username else "worker"
        
        # Try to find corresponding team_id from the user's tasks
        user_team_id = default_team_id
        for t in tasks_raw:
            if t[3] == user_name or t[4] == user_name:
                if t[2] in team_ids:
                    user_team_id = team_ids[t[2]]
                    break
        
        connection.execute(
            sa.text(
                "INSERT INTO users (email, username, full_name, hashed_password, role, team_id, is_active) "
                "VALUES (:email, :username, :full_name, :hashed, :role, :team_id, true) "
                "ON CONFLICT(email) DO NOTHING"
            ),
            {"email": email, "username": username, "full_name": user_name, "hashed": hashed_pwd, "role": role, "team_id": user_team_id}
        )
        res = connection.execute(sa.text("SELECT id FROM users WHERE username = :username"), {"username": username}).fetchone()
        user_ids[user_name] = res[0]

    # Ensure admin user exists with email admin@tracker.com
    if "admin" not in user_ids:
        connection.execute(
            sa.text(
                "INSERT INTO users (email, username, full_name, hashed_password, role, team_id, is_active) "
                "VALUES ('admin@tracker.com', 'admin', 'Administrator', :hashed, 'admin', :team_id, true) "
                "ON CONFLICT(email) DO NOTHING"
            ),
            {"hashed": hashed_pwd, "team_id": default_team_id}
        )
        res = connection.execute(sa.text("SELECT id FROM users WHERE username = 'admin'")).fetchone()
        user_ids["admin"] = res[0]

    # Ensure worker user exists with email worker@tracker.com
    if "worker" not in user_ids:
        connection.execute(
            sa.text(
                "INSERT INTO users (email, username, full_name, hashed_password, role, team_id, is_active) "
                "VALUES ('worker@tracker.com', 'worker', 'Worker User', :hashed, 'worker', :team_id, true) "
                "ON CONFLICT(email) DO NOTHING"
            ),
            {"hashed": hashed_pwd, "team_id": default_team_id}
        )
        res = connection.execute(sa.text("SELECT id FROM users WHERE username = 'worker'")).fetchone()
        user_ids["worker"] = res[0]

    # Insert Projects
    project_ids: Dict[int, int] = {} # team_id -> project_id
    for team_name, t_id in team_ids.items():
        key_base = "".join([w[0] for w in team_name.split() if w.isalnum()]).upper()[:4]
        if not key_base:
            key_base = "PRJ"
        
        # Ensure unique key
        key = key_base
        idx = 1
        while True:
            exists = connection.execute(sa.text("SELECT id FROM projects WHERE key = :key"), {"key": key}).fetchone()
            if not exists:
                break
            key = f"{key_base}{idx}"
            idx += 1

        connection.execute(
            sa.text(
                "INSERT INTO projects (name, key, description, team_id, status) "
                "VALUES (:name, :key, :desc, :team_id, 'ACTIVE') "
                "ON CONFLICT(key) DO NOTHING"
            ),
            {"name": f"{team_name} Project", "key": key, "desc": f"Workspace for {team_name}", "team_id": t_id}
        )
        res = connection.execute(sa.text("SELECT id FROM projects WHERE key = :key"), {"key": key}).fetchone()
        project_ids[t_id] = res[0]

        # Insert project members (admin and team users)
        for u_name, u_id in user_ids.items():
            # Check user's team
            u_team = connection.execute(sa.text("SELECT team_id FROM users WHERE id = :id"), {"id": u_id}).fetchone()
            if u_team and (u_team[0] == t_id or u_name == "admin"):
                connection.execute(
                    sa.text(
                        "INSERT INTO project_members (project_id, user_id, project_role) "
                        "VALUES (:project_id, :user_id, :role) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {"project_id": res[0], "user_id": u_id, "role": "OWNER" if u_name == "admin" else "MEMBER"}
                )

    # Insert Sprints
    sprint_ids: Dict[str, int] = {} # (project_id, name) -> sprint_id
    for t in tasks_raw:
        sprint_name = t[5]
        if sprint_name:
            team_name = t[2] or list(team_ids.keys())[0]
            t_id = team_ids[team_name]
            p_id = project_ids[t_id]
            key_combo = f"{p_id}:{sprint_name}"
            
            if key_combo not in sprint_ids:
                start = datetime.datetime.now(datetime.timezone.utc)
                end = start + datetime.timedelta(days=14)
                connection.execute(
                    sa.text(
                        "INSERT INTO sprints (project_id, name, start_date, end_date, status) "
                        "VALUES (:p_id, :name, :start, :end, 'ACTIVE')"
                    ),
                    {"p_id": p_id, "name": sprint_name, "start": start, "end": end}
                )
                res = connection.execute(
                    sa.text("SELECT id FROM sprints WHERE project_id = :p_id AND name = :name"),
                    {"p_id": p_id, "name": sprint_name}
                ).fetchone()
                sprint_ids[key_combo] = res[0]

    # Map existing Tasks
    default_project_id = list(project_ids.values())[0]
    default_user_id = user_ids.get("admin")

    for t in tasks_raw:
        task_id = t[0]
        old_team = t[2]
        old_assignee = t[3]
        old_creator = t[4]
        old_sprint = t[5]
        
        p_id = project_ids.get(team_ids.get(old_team, 0), default_project_id)
        a_id = user_ids.get(old_assignee)
        c_id = user_ids.get(old_creator, default_user_id)
        
        s_id = None
        if old_sprint:
            s_id = sprint_ids.get(f"{p_id}:{old_sprint}")
            
        connection.execute(
            sa.text(
                "UPDATE tasks SET project_id = :p_id, assignee_id = :a_id, created_by_id = :c_id, sprint_id = :s_id "
                "WHERE id = :task_id"
            ),
            {"p_id": p_id, "a_id": a_id, "c_id": c_id, "s_id": s_id, "task_id": task_id}
        )

    # If there are no tasks, make sure any newly created task can default
    # but since it's tests/empty, we don't have to update rows.

    # 4. Enforce NOT NULL and constraints on evolved columns
    # We must first ensure that all task rows have a project_id and created_by_id.
    # Set default values for any tasks that somehow remained NULL.
    connection.execute(
        sa.text("UPDATE tasks SET project_id = :p_id WHERE project_id IS NULL"),
        {"p_id": default_project_id}
    )
    connection.execute(
        sa.text("UPDATE tasks SET created_by_id = :u_id WHERE created_by_id IS NULL"),
        {"u_id": default_user_id}
    )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column("project_id", nullable=False, existing_type=sa.Integer())
        batch_op.alter_column("created_by_id", nullable=False, existing_type=sa.Integer())
        
        # Add foreign key constraints
        batch_op.create_foreign_key("fk_tasks_project", "projects", ["project_id"], ["id"], ondelete="RESTRICT")
        batch_op.create_foreign_key("fk_tasks_sprint", "sprints", ["sprint_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_tasks_epic", "epics", ["epic_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_tasks_assignee", "users", ["assignee_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_tasks_created_by", "users", ["created_by_id"], ["id"], ondelete="RESTRICT")
        batch_op.create_foreign_key("fk_tasks_completed_by", "users", ["completed_by_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_tasks_deleted_by", "users", ["deleted_by_id"], ["id"], ondelete="SET NULL")

    # Add comments task_id foreign key constraint now that tasks table has constraints
    with op.batch_alter_table("comments") as batch_op:
        batch_op.create_foreign_key("fk_comments_task", "tasks", ["task_id"], ["id"], ondelete="CASCADE")

    # Add task_labels task_id foreign key constraint
    with op.batch_alter_table("task_labels") as batch_op:
        batch_op.create_foreign_key("fk_task_labels_task", "tasks", ["task_id"], ["id"], ondelete="CASCADE")

    # 5. Remove obsolete columns from tasks
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("department")
        batch_op.drop_column("team")
        batch_op.drop_column("assignee")
        batch_op.drop_column("created_by")
        batch_op.drop_column("sprint")


def downgrade() -> None:
    # Downgrade is not strictly supported for complex normalization migrations,
    # but we can reconstruct a basic table structure for safety.
    raise NotImplementedError("Downgrade from normalized schema is not supported.")
