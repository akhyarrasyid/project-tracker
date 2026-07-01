import argparse
import datetime as dt
import json
import logging
import os
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.models.activity_log import ActivityLog
from app.db.models.attachment import Attachment
from app.db.models.comment import Comment
from app.db.models.department import Department
from app.db.models.epic import Epic
from app.db.models.label import Label
from app.db.models.notification import Notification
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.sprint import Sprint
from app.db.models.task import Task
from app.db.models.task_label import TaskLabel
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.watcher import Watcher
from app.db.session import SessionLocal
from app.schemas.notification import notification_action_for_type
from app.schemas.task import CustomerImpact, Quarter, RiskLevel, TaskCreate, TaskPriority, TaskStatus

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SEEDS_ROOT = Path(__file__).resolve().parents[2] / "app" / "db" / "seeds"
PROFILE_DIR = SEEDS_ROOT / "profiles"
CATALOG_DIR = SEEDS_ROOT / "catalogs"
SCENARIO_DIR = SEEDS_ROOT / "scenarios"
LEGACY_SEED_FILE = SEEDS_ROOT / "project_tracker_seed.json"
REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_PROFILE = "smoke"
DEFAULT_ANCHOR_DATE = dt.date(2026, 6, 30)
DEFAULT_PASSWORD = "password123"
DEMO_SEED_PASSWORD_ENV = "DEMO_SEED_PASSWORD"
DEMO_ACCOUNTS_LOCAL_FILE = REPO_ROOT / "backend" / ".runtime" / "demo-accounts.local.md"
REPORT_OUTPUT_DIR = REPO_ROOT / "backend" / ".runtime"
REPORT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.json$")
VALID_PROJECT_MEMBER_ROLES = {"OWNER", "MEMBER", "VIEWER"}
ACTIVE_WATCHER_STATE = {"is_watching": True, "unwatched_at": None}
AVAILABLE_PROFILE_NAMES = frozenset(path.stem for path in PROFILE_DIR.glob("*.json"))


@dataclass(frozen=True)
class ReportDestination:
    path: Path


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _iso_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    return dt.date.fromisoformat(value)


def _iso_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _to_datetime(value: dt.date | dt.datetime) -> dt.datetime:
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc)
    return dt.datetime.combine(value, dt.time.min, tzinfo=dt.timezone.utc)


def _slugify(value: str) -> str:
    lowered = value.lower().strip()
    chars = [ch if ch.isalnum() else "_" for ch in lowered]
    collapsed = "".join(chars)
    while "__" in collapsed:
        collapsed = collapsed.replace("__", "_")
    return collapsed.strip("_")


def _seed_url_kind(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1"}:
        return "local"
    return "remote"


def _resolve_profile_path(profile_name: str) -> Path:
    if profile_name not in AVAILABLE_PROFILE_NAMES:
        log.error("Seed profile is not recognized.")
        sys.exit(1)
    return PROFILE_DIR / f"{profile_name}.json"


def _sanitize_report_name(report_name: str) -> str:
    candidate = Path(report_name)
    parent = candidate.parent.as_posix().strip(".")
    if candidate.is_absolute():
        raise ValueError("Report path must be a local runtime report filename.")
    if parent not in {"", "runtime", ".runtime", "backend/.runtime"}:
        raise ValueError("Report path must stay within backend/.runtime.")

    sanitized_name = candidate.name
    if not REPORT_NAME_PATTERN.fullmatch(sanitized_name):
        raise ValueError("Report filename must be a simple .json file name.")

    return sanitized_name


def _validated_report_path(file_name: str) -> Path:
    runtime_root = REPORT_OUTPUT_DIR.resolve()
    candidate = (runtime_root / file_name).resolve()
    try:
        candidate.relative_to(runtime_root)
    except ValueError as exc:
        raise ValueError("Report path must stay within backend/.runtime.") from exc
    return candidate


def _build_report_destination(report_path: ReportDestination | None) -> Path | None:
    if report_path is None:
        return None
    runtime_root = REPORT_OUTPUT_DIR.resolve()
    candidate = report_path.path.resolve()
    try:
        candidate.relative_to(runtime_root)
    except ValueError as exc:
        raise ValueError("Report path must stay within backend/.runtime.") from exc
    return candidate


def _parse_report_path(value: str) -> ReportDestination:
    try:
        sanitized_name = _sanitize_report_name(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return ReportDestination(_validated_report_path(sanitized_name))


def _ensure_seed_allowed(profile_name: str) -> None:
    database_url = os.environ.get("DATABASE_URL") or ""
    if not database_url:
        log.error("DATABASE_URL is required to run the seed service.")
        sys.exit(1)

    if _seed_url_kind(database_url) == "local":
        return

    if os.environ.get("ALLOW_REMOTE_SEED") != "1":
        log.error(
            "Remote database seed is blocked. Set ALLOW_REMOTE_SEED=1 and "
            "SEED_CONFIRM_PROFILE to the selected profile to continue explicitly.",
        )
        sys.exit(1)

    if os.environ.get("SEED_CONFIRM_PROFILE") != profile_name:
        log.error("Remote database seed confirmation mismatch.")
        sys.exit(1)

    if not os.environ.get(DEMO_SEED_PASSWORD_ENV):
        log.error(
            "Remote database seed requires %s to be set for demo account passwords.",
            DEMO_SEED_PASSWORD_ENV,
        )
        sys.exit(1)


def _seed_password() -> str:
    return os.environ.get(DEMO_SEED_PASSWORD_ENV) or DEFAULT_PASSWORD


def _demo_urls() -> dict[str, str]:
    backend_url = os.environ.get("VITE_API_URL") or "http://localhost:8000"
    frontend_url = os.environ.get("DEMO_FRONTEND_URL") or "http://localhost:5173"
    return {
        "frontend": frontend_url.rstrip("/"),
        "backend_api": backend_url.rstrip("/"),
        "api_docs": f"{backend_url.rstrip('/')}/docs",
    }


def _write_demo_accounts_local_file(profile: dict[str, Any]) -> None:
    demo_accounts = profile.get("demo_accounts", [])
    if not demo_accounts:
        return

    password = _seed_password()
    urls = _demo_urls()
    DEMO_ACCOUNTS_LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Local Demo Credentials",
        "",
        "Generated from the latest `release_demo` seed.",
        "",
        "| Username | Password |",
        "|---|---|",
    ]
    lines.extend(
        f"| `{account['username']}` | `{password}` |" for account in demo_accounts
    )
    lines.extend(
        [
            "",
            "Application URLs:",
            "",
            f"- Frontend: `{urls['frontend']}`",
            f"- Backend API: `{urls['backend_api']}`",
            f"- API Docs: `{urls['api_docs']}`",
            "",
        ]
    )
    DEMO_ACCOUNTS_LOCAL_FILE.write_text("\n".join(lines), encoding="utf-8")


def _log_demo_accounts_ready(account_count: int) -> None:
    if account_count <= 0:
        return
    log.info("Demo accounts ready for %s accounts.", account_count)


def _summary_metrics(summary: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(summary.get("projects", 0)),
        int(summary.get("issues", 0)),
        int(summary.get("notifications", 0)),
        int(summary.get("watchers", 0)),
    )


def _log_seed_summary(action: str, summary: dict[str, Any]) -> None:
    projects, issues, notifications, watchers = _summary_metrics(summary)
    log.info(
        "%s completed. projects=%s issues=%s notifications=%s watchers=%s",
        action,
        projects,
        issues,
        notifications,
        watchers,
    )


def _parse_anchor_date(value: str | None) -> dt.date:
    return _iso_date(value) or DEFAULT_ANCHOR_DATE


def _profile_path(profile_name: str) -> Path:
    return _resolve_profile_path(profile_name)


def _load_seed_data(
    profile_name: str = DEFAULT_PROFILE,
    *,
    anchor_date: dt.date | None = None,
    random_seed: int | None = None,
) -> dict[str, Any]:
    profile_path = _profile_path(profile_name)
    if not profile_path.exists():
        log.error("Seed profile file is missing for the selected profile.")
        sys.exit(1)

    profile = _load_json(profile_path)
    bundle = {
        "profile": profile,
        "catalogs": {
            "organization": _load_json(CATALOG_DIR / "organization.json"),
            "people": _load_json(CATALOG_DIR / "people.json"),
            "labels": _load_json(CATALOG_DIR / "labels.json"),
            "projects": _load_json(CATALOG_DIR / "project_templates.json"),
            "issue_templates": _load_json(CATALOG_DIR / "issue_templates.json"),
        },
        "scenarios": [],
    }
    for scenario_name in profile["scenario_files"]:
        path = SCENARIO_DIR / f"{scenario_name}.json"
        if not path.exists():
            log.error("Scenario file is missing from the selected profile bundle.")
            sys.exit(1)
        bundle["scenarios"].append(_load_json(path))

    bundle["anchor_date"] = anchor_date or _parse_anchor_date(
        profile.get("anchor_date")
    )
    bundle["random_seed"] = (
        random_seed if random_seed is not None else int(profile["random_seed"])
    )
    return bundle


def _validate_project_member_role(role: str) -> None:
    if role not in VALID_PROJECT_MEMBER_ROLES:
        raise ValueError(f"Unsupported project role: {role}")


def _validate_profile_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    profile = bundle["profile"]
    organization = bundle["catalogs"]["organization"]
    projects = bundle["catalogs"]["projects"]
    labels_catalog = bundle["catalogs"]["labels"]
    issue_templates = bundle["catalogs"]["issue_templates"]

    department_names = {item["name"] for item in organization["departments"]}
    team_names = {
        team["name"]
        for item in organization["departments"]
        for team in item["teams"]
    }
    project_map = {project["key"]: project for project in projects["projects"]}
    label_names = {label["name"] for label in labels_catalog["labels"]}

    if len(label_names) != len(labels_catalog["labels"]):
        raise ValueError("Duplicate label names detected in labels catalog")

    selected_projects = []
    for project_key in profile["project_keys"]:
        if project_key not in project_map:
            raise ValueError(f"Profile references unknown project key: {project_key}")
        project = project_map[project_key]
        if project["team"] not in team_names:
            raise ValueError(
                f"Project {project_key} references unknown team {project['team']}"
            )
        for cross_team in project.get("cross_functional_teams", []):
            if cross_team not in team_names:
                raise ValueError(
                    f"Project {project_key} references unknown cross-functional team {cross_team}"
                )
        selected_projects.append(project)

    for project in selected_projects:
        if project["domain"] not in issue_templates["domains"]:
            raise ValueError(
                f"Project {project['key']} references unknown issue template domain "
                f"{project['domain']}"
            )

    for scenario in bundle["scenarios"]:
        for epic in scenario.get("epics", []):
            if epic["project_key"] not in profile["project_keys"]:
                continue
        for issue in scenario.get("issues", []):
            if issue["project_key"] not in profile["project_keys"]:
                continue
            TaskCreate(
                title=issue["title"],
                description=issue.get("description", ""),
                status=issue.get("status", TaskStatus.TODO.value),
                is_blocked=issue.get("is_blocked", False),
                blocked_reason=issue.get("blocked_reason"),
                priority=issue.get("priority", TaskPriority.MEDIUM.value),
                due_date=(bundle["anchor_date"] + dt.timedelta(days=issue.get("due_in_days", 0))),
                story_points=issue.get("story_points", 3),
                estimated_hours=issue.get("estimated_hours", 8),
                actual_hours=issue.get("actual_hours", 0),
                progress_percentage=issue.get("progress_percentage", 0),
                quarter=issue.get("quarter", Quarter.Q2.value),
                risk_level=issue.get("risk_level", RiskLevel.MEDIUM.value),
                customer_impact=issue.get("customer_impact", CustomerImpact.MEDIUM.value),
                sla_hours=issue.get("sla_hours", 48),
                dependencies=[],
                tags=issue.get("tags", []),
            )
            for label_name in issue.get("labels", []):
                if label_name not in label_names:
                    raise ValueError(f"Scenario issue references unknown label {label_name}")
        for department_name in scenario.get("departments", []):
            if department_name not in department_names:
                raise ValueError(f"Unknown scenario department {department_name}")

    return {
        "selected_project_count": len(selected_projects),
        "selected_projects": [project["key"] for project in selected_projects],
        "selected_teams": sorted(
            {
                *[project["team"] for project in selected_projects],
                *[
                    cross_team
                    for project in selected_projects
                    for cross_team in project.get("cross_functional_teams", [])
                ],
            }
        ),
        "selected_departments": sorted(
            {
                department["name"]
                for department in organization["departments"]
                if any(team["name"] in {project["team"] for project in selected_projects} for team in department["teams"])
            }
        ),
    }


class EnterpriseSeedBuilder:
    def __init__(self, bundle: dict[str, Any]):
        self.bundle = bundle
        self.profile = bundle["profile"]
        self.catalogs = bundle["catalogs"]
        self.anchor_date = bundle["anchor_date"]
        self.random = random.Random(bundle["random_seed"])
        self.targets = self.profile["targets"]
        self.generation = self.profile["generation"]

        self.organization = self.catalogs["organization"]
        self.people_catalog = self.catalogs["people"]
        self.labels_catalog = self.catalogs["labels"]
        self.project_catalog = self.catalogs["projects"]
        self.issue_templates = self.catalogs["issue_templates"]["domains"]
        self.project_templates = {
            item["key"]: item
            for item in self.project_catalog["projects"]
            if item["key"] in self.profile["project_keys"]
        }
        self.team_to_department = {}
        for department in self.organization["departments"]:
            for team in department["teams"]:
                self.team_to_department[team["name"]] = department["name"]

        self.data = {
            "departments": [],
            "teams": [],
            "users": [],
            "projects": [],
            "project_members": [],
            "sprints": [],
            "epics": [],
            "labels": [],
            "tasks": [],
            "comments": [],
            "attachments": [],
            "watchers": [],
            "notifications": [],
            "activity_logs": [],
        }
        self.user_by_username: dict[str, dict[str, Any]] = {}
        self.usernames_by_team: dict[str, list[str]] = defaultdict(list)
        self.tasks_by_ref: dict[str, dict[str, Any]] = {}
        self.tasks_by_key: dict[str, dict[str, Any]] = {}
        self.tasks_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.membership_keys: set[tuple[str, str]] = set()
        self.project_member_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.epic_index: dict[tuple[str, str], dict[str, Any]] = {}
        self.sprint_index: dict[tuple[str, str], dict[str, Any]] = {}
        self.label_map = {label["name"]: label for label in self.labels_catalog["labels"]}
        self.rank_cursor: defaultdict[tuple[str, str], int] = defaultdict(int)
        self.number_cursor: defaultdict[str, int] = defaultdict(int)
        self.used_names: set[str] = set()
        self.generated_name_cursor = 0
        self.activity_keys: set[tuple[str, str, str, str | None, str | None, dt.datetime]] = set()

    def _selected_team_names(self) -> list[str]:
        selected_teams = {
            *[project["team"] for project in self.project_templates.values()],
            *[
                cross_team
                for project in self.project_templates.values()
                for cross_team in project.get("cross_functional_teams", [])
            ],
        }
        allowed_teams = set(self.profile.get("team_allowlist", []))
        if allowed_teams:
            selected_teams = {
                team_name
                for team_name in selected_teams
                if team_name in allowed_teams
                or any(
                    project["team"] == team_name
                    for project in self.project_templates.values()
                )
            }
        return sorted(selected_teams)

    def build(self) -> dict[str, Any]:
        self._build_organization()
        self._build_users()
        self._build_projects()
        self._build_project_members()
        self._build_sprints_and_epics()
        self._build_labels()
        self._build_anchor_issues()
        self._build_generated_issues()
        self._build_parent_links()
        self._build_dependencies()
        self._build_comments()
        self._build_watchers()
        self._build_attachments()
        self._build_activity_logs()
        self._build_notifications()
        self._reconcile_task_counters()
        self._assert_targets()
        self.data["summary"] = self._summary()
        return self.data

    def _build_organization(self) -> None:
        selected_teams = set(self._selected_team_names())
        selected_departments = {
            self.team_to_department[team_name] for team_name in selected_teams
        }
        for department in self.organization["departments"]:
            if department["name"] not in selected_departments:
                continue
            self.data["departments"].append(
                {
                    "name": department["name"],
                    "description": department["description"],
                }
            )
            for team in department["teams"]:
                if team["name"] not in selected_teams:
                    continue
                self.data["teams"].append(
                    {
                        "name": team["name"],
                        "department_name": department["name"],
                        "description": team["description"],
                    }
                )

    def _make_user(
        self,
        full_name: str,
        team_name: str,
        *,
        role: str = "worker",
        explicit_username: str | None = None,
        is_demo_account: bool = False,
    ) -> dict[str, Any]:
        username = explicit_username or _slugify(full_name)
        suffix = 1
        base_username = username
        while username in self.user_by_username:
            suffix += 1
            username = f"{base_username}{suffix}"
        user = {
            "full_name": full_name,
            "username": username,
            "email": f"{username}@projecttracker.demo",
            "role": role,
            "team_name": team_name,
            "hashed_password": get_password_hash(_seed_password()),
            "is_active": True,
            "is_demo_account": is_demo_account,
        }
        self.user_by_username[username] = user
        self.usernames_by_team[team_name].append(username)
        self.used_names.add(full_name)
        self.data["users"].append(user)
        return user

    def _generate_unique_name(self) -> str:
        first_names = self.people_catalog["generated_name_pool"]["first_names"]
        last_names = self.people_catalog["generated_name_pool"]["last_names"]
        while True:
            index = self.generated_name_cursor
            first_name = first_names[index % len(first_names)]
            last_name = last_names[(index // len(first_names)) % len(last_names)]
            self.generated_name_cursor += 1
            full_name = f"{first_name} {last_name}"
            if full_name not in self.used_names:
                return full_name

    def _ensure_team_headcount(self, team_name: str, target_count: int) -> None:
        while len(self.usernames_by_team[team_name]) < target_count:
            generated = self._generate_unique_name()
            self._make_user(generated, team_name)

    def _build_users(self) -> None:
        selected_teams = set(self._selected_team_names())
        for account in self.profile.get("demo_accounts", []):
            self._make_user(
                account["full_name"],
                account["team"],
                role=account.get("role", "worker"),
                explicit_username=account["username"],
                is_demo_account=True,
            )

        for team_name, roster in self.people_catalog["anchor_staff"].items():
            if team_name not in selected_teams:
                continue
            for person in roster:
                role = "admin" if person.get("role") == "admin" else "worker"
                self._make_user(person["full_name"], team_name, role=role)

        if not any(user["role"] == "admin" for user in self.data["users"]):
            admin_team = sorted(selected_teams)[0]
            self._make_user("Administrator", admin_team, role="admin")

        team_count = len(selected_teams)
        base_target = max(self.generation["min_team_size"], self.targets["users"] // max(team_count, 1))
        for team_name in sorted(selected_teams):
            spread = self.random.randint(0, self.generation["team_size_spread"])
            self._ensure_team_headcount(
                team_name,
                min(self.generation["max_team_size"], base_target + spread),
            )

        while len(self.data["users"]) < self.targets["users"]:
            team_name = self.random.choice(sorted(selected_teams))
            self._make_user(self._generate_unique_name(), team_name)

    def _build_projects(self) -> None:
        for project_key in self.profile["project_keys"]:
            template = self.project_templates[project_key]
            self.data["projects"].append(
                {
                    "name": template["name"],
                    "key": template["key"],
                    "description": template["description"],
                    "team_name": template["team"],
                    "status": template.get("status", "ACTIVE"),
                    "domain": template["domain"],
                }
            )

    def _pick_team_members(self, team_name: str, count: int) -> list[str]:
        members = list(self.usernames_by_team[team_name])
        self.random.shuffle(members)
        return members[: min(count, len(members))]

    def _project_member_usernames(self, project_key: str) -> set[str]:
        return {
            membership["username"]
            for membership in self.data["project_members"]
            if membership["project_key"] == project_key
        }

    def _project_member_candidates(self, project_key: str) -> list[str]:
        return sorted(self._project_member_usernames(project_key))

    def _ensure_project_participant(self, project_key: str, username: str) -> None:
        if username in self._project_member_usernames(project_key):
            return
        self._add_membership(project_key, username, "MEMBER")

    def _build_project_members(self) -> None:
        for project in self.data["projects"]:
            template = self.project_templates[project["key"]]
            primary_team = template["team"]
            owner_username = _slugify(template["owner"])
            owner = self.user_by_username.get(owner_username)
            if owner is None:
                owner = self._make_user(template["owner"], primary_team)
            self._add_membership(project["key"], owner["username"], "OWNER")

            for username in self._pick_team_members(
                primary_team, self.generation["members_per_project"]
            ):
                role = "MEMBER"
                if username == owner["username"]:
                    continue
                self._add_membership(project["key"], username, role)

            for cross_team in template.get("cross_functional_teams", []):
                if cross_team not in self.usernames_by_team:
                    continue
                for username in self._pick_team_members(
                    cross_team, self.generation["cross_functional_members_per_team"]
                ):
                    self._add_membership(project["key"], username, "MEMBER")

            for username in self._pick_team_members(
                primary_team, self.generation["viewers_per_project"]
            ):
                if username not in self._project_member_usernames(project["key"]):
                    self._add_membership(project["key"], username, "VIEWER")

            if not any(
                membership["project_key"] == project["key"]
                and membership["project_role"] == "VIEWER"
                for membership in self.data["project_members"]
            ):
                viewer_candidates = [
                    username
                    for username in self.user_by_username
                    if username not in self._project_member_usernames(project["key"])
                ]
                if viewer_candidates:
                    self._add_membership(
                        project["key"], self.random.choice(viewer_candidates), "VIEWER"
                    )

        for account in self.profile.get("demo_accounts", []):
            for membership in account.get("memberships", []):
                self._add_membership(
                    membership["project_key"],
                    account["username"],
                    membership["project_role"],
                )

    def _add_membership(self, project_key: str, username: str, project_role: str) -> None:
        _validate_project_member_role(project_role)
        key = (project_key, username)
        if key in self.membership_keys:
            return
        self.membership_keys.add(key)
        self.project_member_index[project_key].append(key)
        self.data["project_members"].append(
            {
                "project_key": project_key,
                "username": username,
                "project_role": project_role,
                "joined_at": _to_datetime(self.anchor_date - dt.timedelta(days=self.random.randint(5, 180))),
            }
        )

    def _build_sprints_and_epics(self) -> None:
        sprint_templates = self.project_catalog["sprint_templates"]
        for project in self.data["projects"]:
            for index in range(self.generation["sprints_per_project"]):
                sprint_name = sprint_templates[index % len(sprint_templates)]
                start = _to_datetime(self.anchor_date - dt.timedelta(days=14 * (index + 1)))
                end = start + dt.timedelta(days=13)
                sprint = {
                    "project_key": project["key"],
                    "name": sprint_name,
                    "goal": f"{project['name']} delivery focus for {sprint_name.lower()}",
                    "start_date": start,
                    "end_date": end,
                    "status": "ACTIVE" if index == 0 else "CLOSED",
                }
                self.sprint_index[(project["key"], sprint_name)] = sprint
                self.data["sprints"].append(sprint)

            template = self.project_templates[project["key"]]
            epic_names = list(template["epic_themes"])
            for scenario in self.bundle["scenarios"]:
                for epic in scenario.get("epics", []):
                    if epic["project_key"] == project["key"] and epic["name"] not in epic_names:
                        epic_names.append(epic["name"])
            for epic_name in epic_names[: self.generation["epics_per_project"]]:
                epic = {
                    "project_key": project["key"],
                    "name": epic_name,
                    "description": f"{project['name']} initiative: {epic_name}",
                }
                self.epic_index[(project["key"], epic_name)] = epic
                self.data["epics"].append(epic)

    def _build_labels(self) -> None:
        for label in self.labels_catalog["labels"]:
            self.data["labels"].append(label)

        desired = self.targets.get("labels")
        generated_index = 1
        while len(self.data["labels"]) < desired:
            label_name = f"initiative-{generated_index:02d}"
            if label_name not in self.label_map:
                label = {"name": label_name, "color": self.random.choice(self.labels_catalog["palette"])}
                self.data["labels"].append(label)
                self.label_map[label_name] = label
            generated_index += 1

    def _next_number(self, project_key: str) -> int:
        self.number_cursor[project_key] += 1
        return self.number_cursor[project_key]

    def _next_rank(self, project_key: str, status: str) -> int:
        key = (project_key, status)
        self.rank_cursor[key] += 1024
        return self.rank_cursor[key]

    def _pick_assignee(self, project_key: str) -> str:
        members = [
            username
            for project, username in self.project_member_index[project_key]
            if any(
                membership["project_key"] == project_key
                and membership["username"] == username
                and membership["project_role"] in {"OWNER", "MEMBER"}
                for membership in self.data["project_members"]
            )
        ]
        return self.random.choice(members)

    def _pick_creator(self, project_key: str) -> str:
        usernames = [username for _, username in self.project_member_index[project_key]]
        return self.random.choice(usernames)

    def _ensure_epic(self, project_key: str, epic_name: str) -> None:
        key = (project_key, epic_name)
        if key in self.epic_index:
            return
        epic = {
            "project_key": project_key,
            "name": epic_name,
            "description": f"{self.project_templates[project_key]['name']} initiative: {epic_name}",
        }
        self.epic_index[key] = epic
        self.data["epics"].append(epic)

    def _ensure_sprint(self, project_key: str, sprint_name: str) -> None:
        key = (project_key, sprint_name)
        if key in self.sprint_index:
            return
        start = _to_datetime(self.anchor_date - dt.timedelta(days=14))
        sprint = {
            "project_key": project_key,
            "name": sprint_name,
            "goal": f"{self.project_templates[project_key]['name']} sprint goal",
            "start_date": start,
            "end_date": start + dt.timedelta(days=13),
            "status": "ACTIVE",
        }
        self.sprint_index[key] = sprint
        self.data["sprints"].append(sprint)

    def _task_from_template(self, issue: dict[str, Any]) -> dict[str, Any]:
        project_key = issue["project_key"]
        sprint_name = issue.get("sprint", self.project_catalog["sprint_templates"][0])
        epic_name = issue.get("epic") or self.project_templates[project_key]["epic_themes"][0]
        self._ensure_sprint(project_key, sprint_name)
        self._ensure_epic(project_key, epic_name)
        created_at = _to_datetime(self.anchor_date - dt.timedelta(days=issue.get("created_days_ago", 8)))
        updated_at = _to_datetime(self.anchor_date - dt.timedelta(days=issue.get("updated_days_ago", 2)))
        number = int(issue["number"])
        self.number_cursor[project_key] = max(self.number_cursor[project_key], number)
        task = {
            "ref": issue["ref"],
            "project_key": project_key,
            "number": number,
            "rank": self._next_rank(project_key, issue.get("status", TaskStatus.TODO.value)),
            "title": issue["title"],
            "description": issue.get("description", ""),
            "status": issue.get("status", TaskStatus.TODO.value),
            "is_blocked": issue.get("is_blocked", False),
            "blocked_reason": issue.get("blocked_reason"),
            "priority": issue.get("priority", TaskPriority.MEDIUM.value),
            "assignee_username": _slugify(issue["assignee"]),
            "created_by_username": _slugify(issue.get("created_by", issue["assignee"])),
            "created_at": created_at,
            "updated_at": updated_at,
            "due_date": self.anchor_date + dt.timedelta(days=issue.get("due_in_days", 7)),
            "completed_at": None
            if issue.get("status") != TaskStatus.DONE.value
            else updated_at,
            "story_points": issue.get("story_points", 3),
            "estimated_hours": issue.get("estimated_hours", 8),
            "actual_hours": issue.get("actual_hours", 0),
            "progress_percentage": issue.get("progress_percentage", 0),
            "quarter": issue.get("quarter", Quarter.Q2.value),
            "risk_level": issue.get("risk_level", RiskLevel.MEDIUM.value),
            "customer_impact": issue.get("customer_impact", CustomerImpact.MEDIUM.value),
            "sla_hours": issue.get("sla_hours", 48),
            "dependencies_refs": list(issue.get("dependencies", [])),
            "dependency_keys": [],
            "tags": list(issue.get("tags", [])),
            "label_names": list(issue.get("labels", [])),
            "sprint_name": sprint_name,
            "epic_name": epic_name,
            "parent_ref": issue.get("parent_ref"),
        }
        self._ensure_project_participant(project_key, task["assignee_username"])
        self._ensure_project_participant(project_key, task["created_by_username"])
        self.tasks_by_ref[task["ref"]] = task
        self.tasks_by_key[f"{project_key}-{number}"] = task
        self.tasks_by_project[project_key].append(task)
        self.data["tasks"].append(task)
        return task

    def _build_anchor_issues(self) -> None:
        for scenario in self.bundle["scenarios"]:
            for issue in scenario.get("issues", []):
                if issue["project_key"] not in self.project_templates:
                    continue
                task = self._task_from_template(issue)
                task["seed_comments"] = issue.get("comments", [])
                task["seed_attachments"] = issue.get("attachments", [])
                task["seed_watchers"] = issue.get("watchers", [])
                task["seed_activities"] = issue.get("activity", [])
                task["seed_notifications"] = issue.get("notifications", [])

    def _choice_weighted(self, weights: dict[str, int]) -> str:
        items = list(weights.items())
        population = [item[0] for item in items]
        return self.random.choices(population, weights=[item[1] for item in items], k=1)[0]

    def _pick_labels(self, project_key: str, domain: str, limit: int) -> list[str]:
        project_labels = set(self.project_templates[project_key].get("default_labels", []))
        domain_labels = [
            item["name"]
            for item in self.data["labels"]
            if domain in item.get("domains", []) or item["name"] in project_labels
        ]
        self.random.shuffle(domain_labels)
        result = domain_labels[:limit]
        if not result:
            result = ["needs-triage"]
        return result

    def _build_generated_issues(self) -> None:
        total_needed = self.targets["issues"] - len(self.data["tasks"])
        if total_needed <= 0:
            return

        project_keys = [project["key"] for project in self.data["projects"]]
        per_project = total_needed // max(len(project_keys), 1)
        remainder = total_needed % max(len(project_keys), 1)
        status_weights = self.generation["status_weights"]

        for index, project_key in enumerate(project_keys):
            project_total = per_project + (1 if index < remainder else 0)
            template = self.project_templates[project_key]
            domain = template["domain"]
            templates = self.issue_templates[domain]
            for _ in range(project_total):
                status = self._choice_weighted(status_weights)
                priority = self._choice_weighted(self.generation["priority_weights"])
                title = self.random.choice(templates["title_templates"]).format(
                    object=self.random.choice(templates["objects"]),
                    surface=self.random.choice(templates["surfaces"]),
                    workflow=self.random.choice(templates["workflows"]),
                    metric=self.random.choice(templates["metrics"]),
                )
                story_points = self.random.choice([1, 2, 3, 5, 8, 13])
                estimated_hours = story_points * self.random.choice([2, 3, 4])
                actual_hours = 0 if status == "Todo" else max(1, estimated_hours - self.random.randint(0, 3))
                progress = {
                    "Todo": 0,
                    "In Progress": self.random.randint(20, 75),
                    "Review": self.random.randint(75, 95),
                    "Done": 100,
                }[status]
                blocked = status != "Done" and self.random.random() < self.generation["blocked_ratio"]
                number = self._next_number(project_key)
                created_days_ago = self.random.randint(1, 90)
                updated_days_ago = max(0, created_days_ago - self.random.randint(0, 14))
                sprint_name = self.random.choice(
                    [sprint["name"] for sprint in self.data["sprints"] if sprint["project_key"] == project_key]
                )
                epic_name = self.random.choice(template["epic_themes"])
                self._ensure_epic(project_key, epic_name)
                task = {
                    "ref": f"{project_key.lower()}-{number}",
                    "project_key": project_key,
                    "number": number,
                    "rank": self._next_rank(project_key, status),
                    "title": title,
                    "description": self.random.choice(templates["descriptions"]).format(
                        project=self.project_templates[project_key]["name"],
                        workflow=self.random.choice(templates["workflows"]),
                        object=self.random.choice(templates["objects"]),
                        surface=self.random.choice(templates["surfaces"]),
                        metric=self.random.choice(templates["metrics"]),
                    ),
                    "status": status,
                    "is_blocked": blocked,
                    "blocked_reason": None
                    if not blocked
                    else self.random.choice(
                        templates.get(
                            "blocked_reasons",
                            [
                                "Waiting for dependent issue before work can continue",
                                "Pending external approval on the current workflow",
                                "Needs confirmed data from another operating team",
                            ],
                        )
                    ),
                    "priority": priority,
                    "assignee_username": self._pick_assignee(project_key),
                    "created_by_username": self._pick_creator(project_key),
                    "created_at": _to_datetime(self.anchor_date - dt.timedelta(days=created_days_ago)),
                    "updated_at": _to_datetime(self.anchor_date - dt.timedelta(days=updated_days_ago)),
                    "due_date": self.anchor_date + dt.timedelta(days=self.random.randint(-12, 30)),
                    "completed_at": None
                    if status != "Done"
                    else _to_datetime(self.anchor_date - dt.timedelta(days=updated_days_ago)),
                    "story_points": story_points,
                    "estimated_hours": estimated_hours,
                    "actual_hours": actual_hours,
                    "progress_percentage": progress,
                    "quarter": self.random.choice([item.value for item in Quarter]),
                    "risk_level": self._choice_weighted(self.generation["risk_weights"]),
                    "customer_impact": self._choice_weighted(self.generation["customer_impact_weights"]),
                    "sla_hours": self.random.choice([24, 48, 72, 120]),
                    "dependencies_refs": [],
                    "dependency_keys": [],
                    "tags": self.random.sample(templates["tags"], k=min(2, len(templates["tags"]))),
                    "label_names": self._pick_labels(
                        project_key,
                        domain,
                        self.random.randint(1, self.generation["max_labels_per_issue"]),
                    ),
                    "sprint_name": sprint_name,
                    "epic_name": epic_name,
                    "parent_ref": None,
                }
                self.tasks_by_ref[task["ref"]] = task
                self.tasks_by_key[f"{project_key}-{number}"] = task
                self.tasks_by_project[project_key].append(task)
                self.data["tasks"].append(task)

    def _build_parent_links(self) -> None:
        desired = min(self.targets["parent_links"], max(0, len(self.data["tasks"]) // 6))
        candidates = [
            task
            for task in self.data["tasks"]
            if task["status"] in {TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value, TaskStatus.REVIEW.value}
        ]
        self.random.shuffle(candidates)
        created = 0
        for project_key, tasks in self.tasks_by_project.items():
            parents = [task for task in tasks if task["story_points"] >= 5]
            children = [task for task in tasks if task["story_points"] <= 3]
            if not parents or not children:
                continue
            for child in children[: self.generation["max_children_per_project"]]:
                if created >= desired:
                    return
                parent = self.random.choice(parents)
                if parent["ref"] == child["ref"]:
                    continue
                child["parent_ref"] = parent["ref"]
                created += 1

    def _build_dependencies(self) -> None:
        desired = self.targets["dependencies"]
        task_pool = [task for task in self.data["tasks"] if task["status"] != TaskStatus.DONE.value]
        self.random.shuffle(task_pool)
        created = 0
        for task in task_pool:
            if created >= desired:
                break
            same_project = [
                candidate
                for candidate in self.tasks_by_project[task["project_key"]]
                if candidate["ref"] != task["ref"]
                and candidate["created_at"] <= task["created_at"]
                and candidate["ref"] != task.get("parent_ref")
            ]
            if not same_project:
                continue
            dependency = self.random.choice(same_project)
            if dependency["ref"] in task["dependencies_refs"]:
                continue
            task["dependencies_refs"].append(dependency["ref"])
            created += 1

    def _build_comments(self) -> None:
        for task in self.data["tasks"]:
            for index, comment in enumerate(task.pop("seed_comments", [])):
                created_at = task["created_at"] + dt.timedelta(hours=comment.get("hours_after_create", index + 1))
                self.data["comments"].append(
                    {
                        "task_ref": task["ref"],
                        "author_username": _slugify(comment["author"]),
                        "content": comment["content"],
                        "created_at": created_at,
                        "updated_at": created_at,
                        "parent_index": None,
                    }
                )

        remaining = self.targets["comments"] - len(self.data["comments"])
        comment_templates = self.catalogs["issue_templates"]["comment_templates"]
        tasks = list(self.data["tasks"])
        while remaining > 0:
            task = self.random.choice(tasks)
            author_username = self._pick_assignee(task["project_key"])
            mention = ""
            if self.random.random() < self.generation["mention_ratio"]:
                mention_target = self.random.choice(
                    [user for _, user in self.project_member_index[task["project_key"]] if user != author_username]
                )
                mention = f" @{mention_target}"
            created_at = task["updated_at"] - dt.timedelta(hours=self.random.randint(1, 72))
            self.data["comments"].append(
                {
                    "task_ref": task["ref"],
                    "author_username": author_username,
                    "content": self.random.choice(comment_templates).format(
                        title=task["title"],
                        mention=mention,
                    ),
                    "created_at": created_at,
                    "updated_at": created_at,
                    "parent_index": None,
                }
            )
            remaining -= 1

    def _build_watchers(self) -> None:
        watcher_keys = set()
        baseline_watchers_per_issue = max(
            1,
            min(
                self.generation["max_watchers_per_issue"],
                self.targets["watchers"] // max(1, len(self.data["tasks"])),
            ),
        )
        for task in self.data["tasks"]:
            project_members = set(self._project_member_candidates(task["project_key"]))
            seed_watchers = {
                _slugify(name)
                for name in task.pop("seed_watchers", [])
                if _slugify(name) in project_members
            }
            seed_watchers.add(task["created_by_username"])
            seed_watchers.add(task["assignee_username"])
            owner = next(
                (
                    membership["username"]
                    for membership in self.data["project_members"]
                    if membership["project_key"] == task["project_key"]
                    and membership["project_role"] == "OWNER"
                ),
                None,
            )
            if owner:
                seed_watchers.add(owner)
            commenters = {
                comment["author_username"]
                for comment in self.data["comments"]
                if comment["task_ref"] == task["ref"]
                and comment["author_username"] in project_members
            }
            seed_watchers.update(commenters)

            prioritized_usernames = [
                task["assignee_username"],
                task["created_by_username"],
                *sorted(seed_watchers - {task["assignee_username"], task["created_by_username"]}),
            ]
            seen_usernames = []
            for username in prioritized_usernames:
                if username not in seen_usernames:
                    seen_usernames.append(username)
            limit = min(len(seen_usernames), baseline_watchers_per_issue)
            for username in seen_usernames[:limit]:
                key = (task["ref"], username)
                if key in watcher_keys:
                    continue
                watcher_keys.add(key)
                self.data["watchers"].append(
                    {
                        "task_ref": task["ref"],
                        "username": username,
                        "added_by_username": task["created_by_username"],
                        **ACTIVE_WATCHER_STATE,
                        "created_at": task["created_at"] + dt.timedelta(hours=1),
                    }
                )

        while len(self.data["watchers"]) < self.targets["watchers"]:
            task = self.random.choice(self.data["tasks"])
            username = self.random.choice(self._project_member_candidates(task["project_key"]))
            key = (task["ref"], username)
            if key in watcher_keys:
                continue
            watcher_keys.add(key)
            active = len(self.data["watchers"]) >= (
                self.targets["watchers"] - self.targets.get("inactive_watchers", 0)
            )
            unwatched_at = (
                None
                if active
                else task["updated_at"] - dt.timedelta(hours=self.random.randint(1, 24))
            )
            self.data["watchers"].append(
                {
                    "task_ref": task["ref"],
                    "username": username,
                    "added_by_username": task["created_by_username"],
                    "is_watching": active,
                    "unwatched_at": unwatched_at,
                    "created_at": task["created_at"] + dt.timedelta(hours=2),
                }
            )

    def _build_attachments(self) -> None:
        for task in self.data["tasks"]:
            for attachment in task.pop("seed_attachments", []):
                self.data["attachments"].append(
                    {
                        "task_ref": task["ref"],
                        "uploaded_by_username": task["created_by_username"],
                        "filename": attachment["filename"],
                        "storage_path": f"seed/{task['project_key'].lower()}/{task['number']}/{attachment['filename']}",
                        "mime_type": attachment["mime_type"],
                        "size": attachment["size"],
                        "created_at": task["created_at"] + dt.timedelta(hours=attachment.get("hours_after_create", 2)),
                    }
                )

        attachment_templates = self.catalogs["issue_templates"]["attachment_templates"]
        while len(self.data["attachments"]) < self.targets["attachments"]:
            task = self.random.choice(self.data["tasks"])
            template = self.random.choice(attachment_templates)
            filename = template["filename_template"].format(
                project=task["project_key"].lower(),
                number=task["number"],
            )
            storage_path = f"seed/{task['project_key'].lower()}/{task['number']}/{filename}"
            if any(
                item["task_ref"] == task["ref"] and item["storage_path"] == storage_path
                for item in self.data["attachments"]
            ):
                continue
            self.data["attachments"].append(
                {
                    "task_ref": task["ref"],
                    "uploaded_by_username": task["created_by_username"],
                    "filename": filename,
                    "storage_path": storage_path,
                    "mime_type": template["mime_type"],
                    "size": self.random.randint(template["min_size"], template["max_size"]),
                    "created_at": task["updated_at"] - dt.timedelta(hours=self.random.randint(1, 96)),
                }
            )

    def _append_activity_log(self, record: dict[str, Any]) -> bool:
        key = (
            record["task_ref"],
            record["actor_username"],
            record["action"],
            record["field"],
            record["new_value"],
            record["created_at"],
        )
        if key in self.activity_keys:
            return False
        self.activity_keys.add(key)
        self.data["activity_logs"].append(record)
        return True

    def _build_activity_logs(self) -> None:
        for task in self.data["tasks"]:
            self._append_activity_log(
                {
                    "task_ref": task["ref"],
                    "project_key": task["project_key"],
                    "actor_username": task["created_by_username"],
                    "action": "created",
                    "field": None,
                    "old_value": None,
                    "new_value": task["title"],
                    "created_at": task["created_at"],
                }
            )
            for activity in task.pop("seed_activities", []):
                self._append_activity_log(
                    {
                        "task_ref": task["ref"],
                        "project_key": task["project_key"],
                        "actor_username": _slugify(activity["actor"]),
                        "action": activity["action"],
                        "field": activity.get("field"),
                        "old_value": activity.get("old_value"),
                        "new_value": activity.get("new_value"),
                        "created_at": task["created_at"] + dt.timedelta(hours=activity.get("hours_after_create", 1)),
                    }
                )
            for comment in [item for item in self.data["comments"] if item["task_ref"] == task["ref"]]:
                self._append_activity_log(
                    {
                        "task_ref": task["ref"],
                        "project_key": task["project_key"],
                        "actor_username": comment["author_username"],
                        "action": "commented",
                        "field": "comment",
                        "old_value": None,
                        "new_value": comment["content"][:120],
                        "created_at": comment["created_at"],
                    }
                )

        activity_templates = self.catalogs["issue_templates"]["activity_templates"]
        while len(self.data["activity_logs"]) < self.targets["activity_logs"]:
            task = self.random.choice(self.data["tasks"])
            template = self.random.choice(activity_templates)
            actor = self.random.choice(
                [item[1] for item in self.project_member_index[task["project_key"]]]
            )
            self._append_activity_log(
                {
                    "task_ref": task["ref"],
                    "project_key": task["project_key"],
                    "actor_username": actor,
                    "action": template["action"],
                    "field": template.get("field"),
                    "old_value": template.get("old_value"),
                    "new_value": template.get("new_value", task["status"]),
                    "created_at": task["updated_at"] - dt.timedelta(hours=self.random.randint(1, 120)),
                }
            )

    def _notification_target_route(self, task: dict[str, Any]) -> str:
        return f"/issues/{task['project_key']}-{task['number']}"

    def _preferred_demo_username(self) -> str | None:
        for username in (
            "payment_owner",
            "engineering_member",
            "legal_member",
            "viewer_user",
            "admin",
            "amanda_putri",
            "bima_santoso",
            "dina_lestari",
            "lia_wulandari",
        ):
            if username in self.user_by_username:
                return username
        active_users = sorted(self.user_by_username)
        return active_users[0] if active_users else None

    def _ensure_demo_inbox_notifications(self) -> None:
        demo_username = self._preferred_demo_username()
        if demo_username is None:
            return

        accessible_tasks = [
            task
            for task in self.data["tasks"]
            if any(
                membership["project_key"] == task["project_key"]
                and membership["username"] == demo_username
                for membership in self.data["project_members"]
            )
        ]
        if len(accessible_tasks) < 4:
            return

        templates = [
            {
                "type": "issue_assigned",
                "title": f"{self.user_by_username[accessible_tasks[0]['created_by_username']]['full_name']} assigned you to {accessible_tasks[0]['project_key']}-{accessible_tasks[0]['number']}",
                "body_preview": accessible_tasks[0]["title"],
                "task": accessible_tasks[0],
                "is_read": False,
            },
            {
                "type": "issue_mentioned",
                "title": f"{self.user_by_username[accessible_tasks[1]['created_by_username']]['full_name']} mentioned you in {accessible_tasks[1]['project_key']}-{accessible_tasks[1]['number']}",
                "body_preview": f"Please verify the latest change, @{demo_username}",
                "task": accessible_tasks[1],
                "is_read": False,
            },
            {
                "type": "issue_commented",
                "title": f"{self.user_by_username[accessible_tasks[2]['created_by_username']]['full_name']} commented on {accessible_tasks[2]['project_key']}-{accessible_tasks[2]['number']}",
                "body_preview": accessible_tasks[2]["title"],
                "task": accessible_tasks[2],
                "is_read": True,
            },
            {
                "type": "issue_status_changed",
                "title": f"{accessible_tasks[3]['project_key']}-{accessible_tasks[3]['number']} moved to {accessible_tasks[3]['status']}",
                "body_preview": accessible_tasks[3]["title"],
                "task": accessible_tasks[3],
                "is_read": False,
            },
        ]

        existing_dedupe = {item["dedupe_key"] for item in self.data["notifications"]}
        for index, item in enumerate(templates, start=1):
            task = item["task"]
            dedupe_key = f"seed-demo:{task['project_key']}-{task['number']}:{item['type']}:{demo_username}"
            if dedupe_key in existing_dedupe:
                continue
            existing_dedupe.add(dedupe_key)
            self.data["notifications"].append(
                {
                    "recipient_username": demo_username,
                    "actor_username": task["created_by_username"],
                    "task_ref": task["ref"],
                    "project_key": task["project_key"],
                    "type": item["type"],
                    "action": notification_action_for_type(item["type"]),
                    "title": item["title"],
                    "body_preview": item["body_preview"],
                    "metadata": {"route_target": self._notification_target_route(task)},
                    "is_read": item["is_read"],
                    "read_at": None,
                    "dedupe_key": dedupe_key,
                    "created_at": task["updated_at"] - dt.timedelta(hours=index),
                }
            )

            watcher_key = (task["ref"], demo_username)
            if watcher_key not in {(w["task_ref"], w["username"]) for w in self.data["watchers"]}:
                self.data["watchers"].append(
                    {
                        "task_ref": task["ref"],
                        "username": demo_username,
                        "added_by_username": task["created_by_username"],
                        **ACTIVE_WATCHER_STATE,
                        "created_at": task["created_at"] + dt.timedelta(hours=3),
                    }
                )

    def _build_notifications(self) -> None:
        dedupe_keys = set()
        for task in self.data["tasks"]:
            for item in task.pop("seed_notifications", []):
                recipient = _slugify(item["recipient"])
                dedupe_key = item["dedupe_key"]
                if dedupe_key in dedupe_keys:
                    continue
                dedupe_keys.add(dedupe_key)
                self.data["notifications"].append(
                {
                    "recipient_username": recipient,
                    "actor_username": None if item.get("actor") is None else _slugify(item["actor"]),
                    "task_ref": task["ref"],
                    "project_key": task["project_key"],
                    "type": item["type"],
                    "action": notification_action_for_type(item["type"]),
                    "title": item["title"],
                    "body_preview": item.get("body_preview"),
                    "metadata": {"route_target": self._notification_target_route(task)},
                        "is_read": item.get("is_read", False),
                        "read_at": None,
                        "dedupe_key": dedupe_key,
                        "created_at": task["created_at"] + dt.timedelta(hours=item.get("hours_after_create", 1)),
                    }
                )

        self._ensure_demo_inbox_notifications()
        notification_templates = self.catalogs["issue_templates"]["notification_templates"]
        while len(self.data["notifications"]) < self.targets["notifications"]:
            task = self.random.choice(self.data["tasks"])
            template = self.random.choice(notification_templates)
            actor = task["created_by_username"]
            recipient_choices = [
                username
                for _, username in self.project_member_index[task["project_key"]]
                if username != actor
            ]
            recipient = self.random.choice(recipient_choices)
            dedupe_key = f"{task['project_key']}-{task['number']}:{template['type']}:{recipient}:{len(self.data['notifications'])}"
            if dedupe_key in dedupe_keys:
                continue
            dedupe_keys.add(dedupe_key)
            title = template["title"].format(
                actor=self.user_by_username[actor]["full_name"],
                issue=f"{task['project_key']}-{task['number']}",
                status=task["status"],
            )
            self.data["notifications"].append(
                {
                    "recipient_username": recipient,
                    "actor_username": actor,
                    "task_ref": task["ref"],
                    "project_key": task["project_key"],
                    "type": template["type"],
                    "action": notification_action_for_type(template["type"]),
                    "title": title,
                    "body_preview": task["title"],
                    "metadata": {"route_target": self._notification_target_route(task)},
                    "is_read": self.random.random() < self.generation["read_notification_ratio"],
                    "read_at": None,
                    "dedupe_key": dedupe_key,
                    "created_at": task["updated_at"] - dt.timedelta(hours=self.random.randint(1, 96)),
                }
            )

        for notification in self.data["notifications"]:
            if notification["is_read"] and notification["read_at"] is None:
                notification["read_at"] = notification["created_at"] + dt.timedelta(hours=2)

    def _reconcile_task_counters(self) -> None:
        comment_counts = Counter(item["task_ref"] for item in self.data["comments"])
        watcher_counts = Counter(
            item["task_ref"] for item in self.data["watchers"] if item["is_watching"]
        )
        attachment_counts = Counter(item["task_ref"] for item in self.data["attachments"])
        for task in self.data["tasks"]:
            task["comments_count"] = comment_counts[task["ref"]]
            task["watchers_count"] = watcher_counts[task["ref"]]
            task["attachments_count"] = attachment_counts[task["ref"]]

    def _assert_targets(self) -> None:
        minimums = {
            "users": len(self.data["users"]),
            "projects": len(self.data["projects"]),
            "tasks": len(self.data["tasks"]),
            "comments": len(self.data["comments"]),
            "watchers": len(self.data["watchers"]),
            "notifications": len(self.data["notifications"]),
            "activity_logs": len(self.data["activity_logs"]),
            "attachments": len(self.data["attachments"]),
        }
        if minimums["tasks"] < self.targets["issues"]:
            raise ValueError("Generated issue count did not reach profile target")
        if minimums["comments"] < self.targets["comments"]:
            raise ValueError("Generated comment count did not reach profile target")
        if minimums["watchers"] < self.targets["watchers"]:
            raise ValueError("Generated watcher count did not reach profile target")
        if minimums["notifications"] < self.targets["notifications"]:
            raise ValueError("Generated notification count did not reach profile target")
        if minimums["activity_logs"] < self.targets["activity_logs"]:
            raise ValueError("Generated activity count did not reach profile target")
        if minimums["attachments"] < self.targets["attachments"]:
            raise ValueError("Generated attachment count did not reach profile target")

    def _summary(self) -> dict[str, Any]:
        return {
            "profile": self.profile["name"],
            "projects": len(self.data["projects"]),
            "users": len(self.data["users"]),
            "project_members": len(self.data["project_members"]),
            "sprints": len(self.data["sprints"]),
            "epics": len(self.data["epics"]),
            "labels": len(self.data["labels"]),
            "issues": len(self.data["tasks"]),
            "comments": len(self.data["comments"]),
            "watchers": len(self.data["watchers"]),
            "attachments": len(self.data["attachments"]),
            "notifications": len(self.data["notifications"]),
            "activity_logs": len(self.data["activity_logs"]),
            "blocked_issues": sum(1 for task in self.data["tasks"] if task["is_blocked"]),
            "sub_issue_links": sum(1 for task in self.data["tasks"] if task.get("parent_ref")),
            "dependency_links": sum(len(task["dependencies_refs"]) for task in self.data["tasks"]),
        }


class DbSeedContext:
    def __init__(self, db: Session):
        self.db = db
        self.departments = {
            department.name: department
            for department in db.query(Department).all()
        }
        self.teams = {
            (team.department.name, team.name): team
            for team in db.query(Team).all()
        }
        self.users = {
            user.username: user
            for user in db.query(User).all()
        }
        self.projects = {
            project.key: project
            for project in db.query(Project).all()
        }
        self.project_members = {
            (member.project_id, member.user_id)
            for member in db.query(ProjectMember).all()
        }
        self.sprints = {
            (project.key, sprint.name): sprint
            for sprint, project in db.query(Sprint, Project).join(Project, Sprint.project_id == Project.id).all()
        }
        self.epics = {
            (project.key, epic.name): epic
            for epic, project in db.query(Epic, Project).join(Project, Epic.project_id == Project.id).all()
        }
        self.labels = {
            label.name: label
            for label in db.query(Label).all()
        }
        self.tasks = {
            (project.key, task.number): task
            for task, project in db.query(Task, Project).join(Project, Task.project_id == Project.id).all()
        }
        self.comments = {
            (comment.task_id, comment.author_id, comment.content, comment.created_at): comment
            for comment in db.query(Comment).all()
        }
        self.attachments = {
            (attachment.task_id, attachment.storage_path): attachment
            for attachment in db.query(Attachment).all()
        }
        self.watchers = {
            (watcher.task_id, watcher.user_id): watcher
            for watcher in db.query(Watcher).all()
        }
        self.notifications = {
            notification.dedupe_key: notification
            for notification in db.query(Notification).filter(Notification.dedupe_key.isnot(None)).all()
        }
        self.activity_logs = {
            (
                activity.task_id,
                activity.actor_id,
                activity.action,
                activity.field,
                activity.new_value,
                activity.created_at,
            ): activity
            for activity in db.query(ActivityLog).all()
        }
        self.task_labels = {
            (task_label.task_id, task_label.label_id)
            for task_label in db.query(TaskLabel).all()
        }
        self.task_ids_by_ref: dict[str, int] = {}

    def get_or_create_department(self, name: str, description: str | None) -> Department:
        department = self.departments.get(name)
        if department:
            return department
        department = Department(name=name, description=description)
        self.db.add(department)
        self.db.flush()
        self.departments[name] = department
        return department

    def get_or_create_team(self, department_name: str, name: str, description: str | None) -> Team:
        key = (department_name, name)
        team = self.teams.get(key)
        if team:
            return team
        department = self.departments[department_name]
        team = Team(name=name, department_id=department.id, description=description)
        self.db.add(team)
        self.db.flush()
        self.teams[key] = team
        return team

    def get_or_create_user(self, record: dict[str, Any]) -> User:
        user = self.users.get(record["username"])
        if user:
            team = self.teams[(record["department_name"], record["team_name"])]
            user.email = record["email"]
            user.full_name = record["full_name"]
            if record.get("is_demo_account"):
                user.hashed_password = record["hashed_password"]
            user.role = record["role"]
            user.team_id = team.id
            user.is_active = record["is_active"]
            return user
        team = self.teams[(record["department_name"], record["team_name"])]
        user = User(
            email=record["email"],
            username=record["username"],
            full_name=record["full_name"],
            hashed_password=record["hashed_password"],
            role=record["role"],
            team_id=team.id,
            is_active=record["is_active"],
        )
        self.db.add(user)
        self.db.flush()
        self.users[user.username] = user
        return user


def _normalise_users(data: dict[str, Any], department_lookup: dict[str, str]) -> list[dict[str, Any]]:
    users = []
    for user in data["users"]:
        team_name = user["team_name"]
        users.append(
            {
                **user,
                "department_name": department_lookup[team_name],
            }
        )
    return users


def _seed_departments_and_teams(db: Session, ctx: DbSeedContext, data: dict[str, Any]) -> dict[str, str]:
    team_department_lookup = {}
    for department in data["departments"]:
        ctx.get_or_create_department(department["name"], department.get("description"))
    for team in data["teams"]:
        ctx.get_or_create_team(
            team["department_name"],
            team["name"],
            team.get("description"),
        )
        team_department_lookup[team["name"]] = team["department_name"]
    return team_department_lookup


def _seed_users(ctx: DbSeedContext, users: list[dict[str, Any]]) -> None:
    for user in users:
        ctx.get_or_create_user(user)


def _refresh_demo_account_passwords(
    ctx: DbSeedContext,
    users: list[dict[str, Any]],
) -> None:
    for user_record in users:
        if not user_record.get("is_demo_account"):
            continue
        user = ctx.users.get(user_record["username"])
        if user is None:
            continue
        user.hashed_password = user_record["hashed_password"]


def _prune_legacy_bootstrap(db: Session, keep_project_keys: set[str]) -> None:
    legacy_projects = db.query(Project).filter(
        ~Project.key.in_(sorted(keep_project_keys)),
        Project.name.like("%Team Project"),
        Project.description.like("Workspace for %"),
    ).all()
    legacy_project_ids = [project.id for project in legacy_projects]

    if legacy_project_ids:
        task_ids = [task_id for task_id, in db.query(Task.id).filter(Task.project_id.in_(legacy_project_ids)).all()]
        if task_ids:
            db.query(Notification).filter(Notification.issue_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(ActivityLog).filter(ActivityLog.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(Comment).filter(Comment.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(Attachment).filter(Attachment.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(Watcher).filter(Watcher.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(TaskLabel).filter(TaskLabel.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)

        db.query(Sprint).filter(Sprint.project_id.in_(legacy_project_ids)).delete(synchronize_session=False)
        db.query(Epic).filter(Epic.project_id.in_(legacy_project_ids)).delete(synchronize_session=False)
        db.query(ProjectMember).filter(ProjectMember.project_id.in_(legacy_project_ids)).delete(synchronize_session=False)
        db.query(Notification).filter(Notification.project_id.in_(legacy_project_ids)).delete(synchronize_session=False)
        db.query(Project).filter(Project.id.in_(legacy_project_ids)).delete(synchronize_session=False)

    db.execute(
        text(
            """
            DELETE FROM users
            WHERE username = 'worker'
              AND NOT EXISTS (
                  SELECT 1 FROM project_members pm WHERE pm.user_id = users.id
              )
            """
        )
    )


def _seed_projects(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["projects"]:
        project = ctx.projects.get(record["key"])
        if project:
            continue
        team = ctx.teams[(record["department_name"], record["team_name"])]
        project = Project(
            name=record["name"],
            key=record["key"],
            description=record.get("description"),
            team_id=team.id,
            status=record["status"],
            issue_sequence=0,
        )
        ctx.db.add(project)
        ctx.db.flush()
        ctx.projects[project.key] = project


def _seed_project_members(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["project_members"]:
        project = ctx.projects[record["project_key"]]
        user = ctx.users[record["username"]]
        key = (project.id, user.id)
        if key in ctx.project_members:
            continue
        membership = ProjectMember(
            project_id=project.id,
            user_id=user.id,
            project_role=record["project_role"],
            joined_at=record["joined_at"],
        )
        ctx.db.add(membership)
        ctx.db.flush()
        ctx.project_members.add(key)


def _seed_sprints_and_epics(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["sprints"]:
        key = (record["project_key"], record["name"])
        if key in ctx.sprints:
            continue
        project = ctx.projects[record["project_key"]]
        sprint = Sprint(
            project_id=project.id,
            name=record["name"],
            goal=record["goal"],
            start_date=record["start_date"],
            end_date=record["end_date"],
            status=record["status"],
        )
        ctx.db.add(sprint)
        ctx.db.flush()
        ctx.sprints[key] = sprint

    for record in data["epics"]:
        key = (record["project_key"], record["name"])
        if key in ctx.epics:
            continue
        project = ctx.projects[record["project_key"]]
        epic = Epic(
            project_id=project.id,
            name=record["name"],
            description=record.get("description"),
        )
        ctx.db.add(epic)
        ctx.db.flush()
        ctx.epics[key] = epic


def _seed_labels(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["labels"]:
        label = ctx.labels.get(record["name"])
        if label:
            continue
        label = Label(name=record["name"], color=record["color"])
        ctx.db.add(label)
        ctx.db.flush()
        ctx.labels[label.name] = label


def _seed_tasks(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["tasks"]:
        key = (record["project_key"], record["number"])
        project = ctx.projects[record["project_key"]]
        if key in ctx.tasks:
            task = ctx.tasks[key]
            ctx.task_ids_by_ref[record["ref"]] = task.id
            continue

        assignee = ctx.users[record["assignee_username"]]
        creator = ctx.users[record["created_by_username"]]
        sprint = ctx.sprints[(record["project_key"], record["sprint_name"])]
        epic = ctx.epics[(record["project_key"], record["epic_name"])]
        task = Task(
            project_id=project.id,
            sprint_id=sprint.id,
            epic_id=epic.id,
            number=record["number"],
            rank=record["rank"],
            version=1,
            title=record["title"],
            description=record["description"],
            status=record["status"],
            is_blocked=record["is_blocked"],
            blocked_reason=record["blocked_reason"],
            priority=record["priority"],
            quarter=record["quarter"],
            risk_level=record["risk_level"],
            customer_impact=record["customer_impact"],
            assignee_id=assignee.id,
            created_by_id=creator.id,
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            due_date=record["due_date"],
            completed_at=record["completed_at"],
            completed_by_id=assignee.id if record["completed_at"] else None,
            story_points=record["story_points"],
            estimated_hours=record["estimated_hours"],
            actual_hours=record["actual_hours"],
            progress_percentage=record["progress_percentage"],
            attachments_count=0,
            comments_count=0,
            watchers_count=0,
            sla_hours=record["sla_hours"],
            dependencies=[],
            tags=record["tags"],
        )
        ctx.db.add(task)
        ctx.db.flush()
        ctx.tasks[key] = task
        ctx.task_ids_by_ref[record["ref"]] = task.id
        project.issue_sequence = max(project.issue_sequence, record["number"])

    for record in data["tasks"]:
        task = ctx.tasks[(record["project_key"], record["number"])]
        parent_ref = record.get("parent_ref")
        if parent_ref:
            task.parent_id = ctx.task_ids_by_ref[parent_ref]
        task.dependencies = [ctx.task_ids_by_ref[ref] for ref in record["dependencies_refs"] if ref in ctx.task_ids_by_ref]
        task.updated_at = record["updated_at"]


def _seed_task_labels(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["tasks"]:
        task = ctx.tasks[(record["project_key"], record["number"])]
        for label_name in record["label_names"]:
            label = ctx.labels[label_name]
            key = (task.id, label.id)
            if key in ctx.task_labels:
                continue
            task_label = TaskLabel(task_id=task.id, label_id=label.id)
            ctx.db.add(task_label)
            ctx.task_labels.add(key)


def _seed_comments(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["comments"]:
        task_id = ctx.task_ids_by_ref[record["task_ref"]]
        author = ctx.users[record["author_username"]]
        key = (task_id, author.id, record["content"], record["created_at"])
        if key in ctx.comments:
            continue
        comment = Comment(
            task_id=task_id,
            author_id=author.id,
            content=record["content"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )
        ctx.db.add(comment)
        ctx.db.flush()
        ctx.comments[key] = comment


def _seed_attachments(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["attachments"]:
        task_id = ctx.task_ids_by_ref[record["task_ref"]]
        uploader = ctx.users[record["uploaded_by_username"]]
        key = (task_id, record["storage_path"])
        if key in ctx.attachments:
            continue
        attachment = Attachment(
            task_id=task_id,
            uploaded_by_id=uploader.id,
            filename=record["filename"],
            storage_path=record["storage_path"],
            mime_type=record["mime_type"],
            size=record["size"],
            created_at=record["created_at"],
        )
        ctx.db.add(attachment)
        ctx.db.flush()
        ctx.attachments[key] = attachment


def _seed_watchers(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["watchers"]:
        task_id = ctx.task_ids_by_ref[record["task_ref"]]
        user = ctx.users[record["username"]]
        key = (task_id, user.id)
        watcher = ctx.watchers.get(key)
        if watcher is None:
            watcher = Watcher(
                task_id=task_id,
                user_id=user.id,
                added_by_id=ctx.users[record["added_by_username"]].id,
                is_watching=record["is_watching"],
                unwatched_at=record["unwatched_at"],
                created_at=record["created_at"],
            )
            ctx.db.add(watcher)
            ctx.db.flush()
            ctx.watchers[key] = watcher
            continue
        watcher.is_watching = record["is_watching"]
        watcher.unwatched_at = record["unwatched_at"]
        watcher.added_by_id = ctx.users[record["added_by_username"]].id


def _seed_notifications(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["notifications"]:
        if record["dedupe_key"] in ctx.notifications:
            continue
        notification = Notification(
            recipient_id=ctx.users[record["recipient_username"]].id,
            actor_id=None
            if record["actor_username"] is None
            else ctx.users[record["actor_username"]].id,
            action=record["action"],
            entity_type="task",
            entity_id=ctx.task_ids_by_ref[record["task_ref"]],
            issue_id=ctx.task_ids_by_ref[record["task_ref"]],
            project_id=ctx.projects[record["project_key"]].id,
            type=record["type"],
            title=record["title"],
            body_preview=record["body_preview"],
            metadata_json=record["metadata"],
            is_read=record["is_read"],
            read_at=record["read_at"],
            dedupe_key=record["dedupe_key"],
            created_at=record["created_at"],
        )
        ctx.db.add(notification)
        ctx.db.flush()
        ctx.notifications[record["dedupe_key"]] = notification


def _seed_activity_logs(ctx: DbSeedContext, data: dict[str, Any]) -> None:
    for record in data["activity_logs"]:
        task_id = ctx.task_ids_by_ref[record["task_ref"]]
        actor_id = ctx.users[record["actor_username"]].id
        key = (
            task_id,
            actor_id,
            record["action"],
            record["field"],
            record["new_value"],
            record["created_at"],
        )
        if key in ctx.activity_logs:
            continue
        activity = ActivityLog(
            task_id=task_id,
            project_id=ctx.projects[record["project_key"]].id,
            actor_id=actor_id,
            action=record["action"],
            field=record["field"],
            old_value=record["old_value"],
            new_value=record["new_value"],
            created_at=record["created_at"],
        )
        ctx.db.add(activity)
        ctx.db.flush()
        ctx.activity_logs[key] = activity


def _recalculate_task_counters(ctx: DbSeedContext) -> None:
    task_ids = list(ctx.task_ids_by_ref.values())
    if not task_ids:
        return
    counts = {
        "comments": dict(
            ctx.db.execute(
                text(
                    """
                    SELECT task_id, COUNT(*)::INTEGER
                    FROM comments
                    WHERE deleted_at IS NULL
                    GROUP BY task_id
                    """
                )
            ).all()
        ),
        "attachments": dict(
            ctx.db.execute(
                text(
                    """
                    SELECT task_id, COUNT(*)::INTEGER
                    FROM attachments
                    WHERE deleted_at IS NULL
                    GROUP BY task_id
                    """
                )
            ).all()
        ),
        "watchers": dict(
            ctx.db.execute(
                text(
                    """
                    SELECT task_id, COUNT(*)::INTEGER
                    FROM watchers
                    WHERE is_watching = TRUE
                    GROUP BY task_id
                    """
                )
            ).all()
        ),
    }
    for task_id in task_ids:
        task = ctx.db.get(Task, task_id)
        task.comments_count = counts["comments"].get(task_id, 0)
        task.attachments_count = counts["attachments"].get(task_id, 0)
        task.watchers_count = counts["watchers"].get(task_id, 0)


REPORT_SUMMARY_KEYS = (
    "departments",
    "teams",
    "users",
    "projects",
    "issues",
    "comments",
    "attachments",
    "watchers",
    "notifications",
    "activity_logs",
    "blocked_issues",
    "sub_issue_links",
    "dependency_links",
)


def _safe_report_payload(mode: str, summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": mode,
        "summary": {
            key: int(summary.get(key, 0))
            for key in REPORT_SUMMARY_KEYS
        },
    }


def _safe_reset_report_payload(project_count: int) -> dict[str, Any]:
    return {
        "mode": "reset-profile",
        "summary": {
            "projects": int(project_count),
        },
    }


def _write_runtime_report(report_path: ReportDestination | None, payload: dict[str, Any]) -> None:
    destination = _build_report_destination(report_path)
    if not destination:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _build_profile_dataset(
    profile_name: str,
    *,
    anchor_date: dt.date | None = None,
    random_seed: int | None = None,
) -> dict[str, Any]:
    bundle = _load_seed_data(
        profile_name,
        anchor_date=anchor_date,
        random_seed=random_seed,
    )
    validation_summary = _validate_profile_bundle(bundle)
    builder = EnterpriseSeedBuilder(bundle)
    data = builder.build()
    data["validation_summary"] = validation_summary
    return data


def cmd_validate(
    profile_name: str,
    *,
    anchor_date: dt.date | None = None,
    random_seed: int | None = None,
    report_path: ReportDestination | None = None,
) -> None:
    data = _build_profile_dataset(
        profile_name,
        anchor_date=anchor_date,
        random_seed=random_seed,
    )
    _write_runtime_report(report_path, _safe_report_payload("validate", data["summary"]))
    _log_seed_summary("Validation", data["summary"])
    sys.exit(0)


def cmd_dry_run(
    profile_name: str,
    *,
    anchor_date: dt.date | None = None,
    random_seed: int | None = None,
    report_path: ReportDestination | None = None,
) -> None:
    data = _build_profile_dataset(
        profile_name,
        anchor_date=anchor_date,
        random_seed=random_seed,
    )
    _write_runtime_report(report_path, _safe_report_payload("dry-run", data["summary"]))
    _log_seed_summary("Dry run", data["summary"])
    sys.exit(0)


def _enrich_project_records(data: dict[str, Any], team_department_lookup: dict[str, str]) -> None:
    for project in data["projects"]:
        project["department_name"] = team_department_lookup[project["team_name"]]


def cmd_seed(
    profile_name: str,
    *,
    anchor_date: dt.date | None = None,
    random_seed: int | None = None,
    report_path: ReportDestination | None = None,
) -> None:
    _ensure_seed_allowed(profile_name)
    profile = _load_json(_profile_path(profile_name))
    data = _build_profile_dataset(
        profile_name,
        anchor_date=anchor_date,
        random_seed=random_seed,
    )
    db = SessionLocal()
    try:
        if profile_name == "release_demo":
            _prune_legacy_bootstrap(db, set(data["validation_summary"]["selected_projects"]))
        ctx = DbSeedContext(db)
        team_department_lookup = _seed_departments_and_teams(db, ctx, data)
        users = _normalise_users(data, team_department_lookup)
        _seed_users(ctx, users)
        _refresh_demo_account_passwords(ctx, users)
        for project in data["projects"]:
            project["department_name"] = team_department_lookup[project["team_name"]]
        _seed_projects(ctx, data)
        _seed_project_members(ctx, data)
        _seed_sprints_and_epics(ctx, data)
        _seed_labels(ctx, data)
        _seed_tasks(ctx, data)
        _seed_task_labels(ctx, data)
        _seed_comments(ctx, data)
        _seed_attachments(ctx, data)
        _seed_watchers(ctx, data)
        _seed_notifications(ctx, data)
        _seed_activity_logs(ctx, data)
        _recalculate_task_counters(ctx)
        db.commit()
        _write_runtime_report(report_path, _safe_report_payload("seed", data["summary"]))
        _write_demo_accounts_local_file(profile)
        _log_demo_accounts_ready(len(profile.get("demo_accounts", [])))
        _log_seed_summary("Seed", data["summary"])
    except Exception:
        db.rollback()
        log.exception("Seed failed, transaction rolled back.")
        sys.exit(1)
    finally:
        db.close()


def cmd_reset_profile(
    profile_name: str,
    *,
    report_path: ReportDestination | None = None,
) -> None:
    _ensure_seed_allowed(profile_name)
    bundle = _load_seed_data(profile_name)
    project_keys = bundle["profile"]["project_keys"]
    db = SessionLocal()
    try:
        project_ids = [
            project_id
            for project_id, in db.query(Project.id).filter(Project.key.in_(project_keys)).all()
        ]
        task_ids = []
        if project_ids:
            task_ids = [task_id for task_id, in db.query(Task.id).filter(Task.project_id.in_(project_ids)).all()]

        if task_ids:
            db.query(Notification).filter(Notification.issue_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(ActivityLog).filter(ActivityLog.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(Comment).filter(Comment.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(Attachment).filter(Attachment.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(Watcher).filter(Watcher.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(TaskLabel).filter(TaskLabel.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)

        if project_ids:
            db.query(Sprint).filter(Sprint.project_id.in_(project_ids)).delete(synchronize_session=False)
            db.query(Epic).filter(Epic.project_id.in_(project_ids)).delete(synchronize_session=False)
            db.query(ProjectMember).filter(ProjectMember.project_id.in_(project_ids)).delete(synchronize_session=False)
            db.query(Notification).filter(Notification.project_id.in_(project_ids)).delete(synchronize_session=False)
            db.query(Project).filter(Project.id.in_(project_ids)).delete(synchronize_session=False)

        db.commit()
        _write_runtime_report(report_path, _safe_reset_report_payload(len(project_keys)))
        log.info(
            "Reset selected profile projects successfully.",
        )
    except Exception:
        db.rollback()
        log.exception("Reset profile failed.")
        sys.exit(1)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Enterprise demo seed service")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed", action="store_true", help="Seed the selected profile")
    group.add_argument(
        "--reset-profile",
        action="store_true",
        dest="reset_profile",
        help="Delete seeded projects and issue data for the selected profile",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Build the selected profile without database writes",
    )
    group.add_argument(
        "--validate",
        action="store_true",
        help="Validate profile references and generated counts",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        choices=sorted(AVAILABLE_PROFILE_NAMES),
        help="Seed profile to use",
    )
    parser.add_argument(
        "--anchor-date",
        dest="anchor_date",
        help="Anchor date in YYYY-MM-DD format for deterministic timelines",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        help="Override the deterministic random seed from the selected profile",
    )
    parser.add_argument(
        "--report",
        type=_parse_report_path,
        help="Optional JSON output path for summary reporting",
    )
    args = parser.parse_args()
    anchor_date = _parse_anchor_date(args.anchor_date)

    if args.validate:
        cmd_validate(
            args.profile,
            anchor_date=anchor_date,
            random_seed=args.random_seed,
            report_path=args.report,
        )
    if args.dry_run:
        cmd_dry_run(
            args.profile,
            anchor_date=anchor_date,
            random_seed=args.random_seed,
            report_path=args.report,
        )
    if args.seed:
        cmd_seed(
            args.profile,
            anchor_date=anchor_date,
            random_seed=args.random_seed,
            report_path=args.report,
        )
    if args.reset_profile:
        cmd_reset_profile(args.profile, report_path=args.report)


if __name__ == "__main__":
    main()
