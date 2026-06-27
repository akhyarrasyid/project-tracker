"""Pydantic schemas for Task — all 26 fields from project_tracker_seed.json."""
import datetime
import math
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.common import PaginatedResponse


# ── Enums ─────────────────────────────────────────────────────────────────────


class TaskStatus(str, Enum):
    TODO = "Todo"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    BLOCKED = "Blocked"
    DONE = "Done"


class TaskPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class CustomerImpact(str, Enum):
    NONE = "None"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    INTERNAL = "Internal"


class Quarter(str, Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


# ── Validators shared between Create and Update ───────────────────────────────

_VALID_STORY_POINTS = {1, 2, 3, 5, 8, 13}
_VALID_SLA_HOURS = {24, 48, 72, 120}


def _serialize_dt(dt: datetime.datetime) -> str:
    """Normalise datetime to UTC ISO-8601 with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


# ── TaskCreate ─────────────────────────────────────────────────────────────────


class TaskCreate(BaseModel):
    """Schema for POST /api/v1/tasks — all required fields."""

    # Required
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=0)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    department: str = Field(..., min_length=1, max_length=100)
    team: str = Field(..., min_length=1, max_length=100)
    assignee: str = Field(..., min_length=1, max_length=100)
    created_by: str = Field(..., min_length=1, max_length=50)
    due_date: datetime.date = Field(...)
    story_points: int = Field(..., ge=1)
    estimated_hours: int = Field(..., ge=1)
    actual_hours: int = Field(default=0, ge=0)
    progress_percentage: int = Field(default=0, ge=0, le=100)
    attachments_count: int = Field(default=0, ge=0)
    comments_count: int = Field(default=0, ge=0)
    watchers_count: int = Field(default=0, ge=0)
    sprint: str = Field(..., min_length=1, max_length=20)
    quarter: Quarter = Quarter.Q1
    risk_level: RiskLevel = RiskLevel.LOW
    customer_impact: CustomerImpact = CustomerImpact.NONE
    sla_hours: int = Field(default=48)
    completed_at: Optional[datetime.datetime] = None
    dependencies: List[int] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, v: object) -> object:
        if isinstance(v, str):
            v = v.strip()
        return v

    @field_validator("story_points")
    @classmethod
    def validate_story_points(cls, v: int) -> int:
        if v not in _VALID_STORY_POINTS:
            raise ValueError(f"story_points must be one of {sorted(_VALID_STORY_POINTS)}")
        return v

    @field_validator("sla_hours")
    @classmethod
    def validate_sla_hours(cls, v: int) -> int:
        if v not in _VALID_SLA_HOURS:
            raise ValueError(f"sla_hours must be one of {sorted(_VALID_SLA_HOURS)}")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags_length(cls, v: List[str]) -> List[str]:
        if len(v) > 4:
            raise ValueError("tags may contain at most 4 items")
        return v


# ── TaskUpdate ─────────────────────────────────────────────────────────────────


class TaskUpdate(BaseModel):
    """Schema for PUT /api/v1/tasks/{id} — all fields optional (partial update)."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    team: Optional[str] = Field(None, min_length=1, max_length=100)
    assignee: Optional[str] = Field(None, min_length=1, max_length=100)
    created_by: Optional[str] = Field(None, min_length=1, max_length=50)
    due_date: Optional[datetime.date] = None
    completed_at: Optional[datetime.datetime] = None
    story_points: Optional[int] = None
    estimated_hours: Optional[int] = Field(None, ge=1)
    actual_hours: Optional[int] = Field(None, ge=0)
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    attachments_count: Optional[int] = Field(None, ge=0)
    comments_count: Optional[int] = Field(None, ge=0)
    watchers_count: Optional[int] = Field(None, ge=0)
    sprint: Optional[str] = Field(None, min_length=1, max_length=20)
    quarter: Optional[Quarter] = None
    risk_level: Optional[RiskLevel] = None
    customer_impact: Optional[CustomerImpact] = None
    sla_hours: Optional[int] = None
    dependencies: Optional[List[int]] = None
    tags: Optional[List[str]] = None

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, v: object) -> object:
        if isinstance(v, str):
            v = v.strip()
        return v

    @field_validator("story_points")
    @classmethod
    def validate_story_points(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in _VALID_STORY_POINTS:
            raise ValueError(f"story_points must be one of {sorted(_VALID_STORY_POINTS)}")
        return v

    @field_validator("sla_hours")
    @classmethod
    def validate_sla_hours(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in _VALID_SLA_HOURS:
            raise ValueError(f"sla_hours must be one of {sorted(_VALID_SLA_HOURS)}")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags_length(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None and len(v) > 4:
            raise ValueError("tags may contain at most 4 items")
        return v


# ── TaskResponse ───────────────────────────────────────────────────────────────


class TaskResponse(BaseModel):
    """Full task representation returned by the API — all 26 fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    priority: str
    department: str
    team: str
    assignee: str
    created_by: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    due_date: datetime.date
    completed_at: Optional[datetime.datetime] = None
    story_points: int
    estimated_hours: int
    actual_hours: int
    progress_percentage: int
    attachments_count: int
    comments_count: int
    watchers_count: int
    sprint: str
    quarter: str
    risk_level: str
    customer_impact: str
    sla_hours: int
    dependencies: List[int]
    tags: List[str]

    @field_serializer("created_at", "updated_at", "completed_at")
    def serialize_dt(self, dt: Optional[datetime.datetime], _info) -> Optional[str]:
        if dt is None:
            return None
        return _serialize_dt(dt)


# ── TaskListResponse (pagination envelope) ─────────────────────────────────────

TaskListResponse = PaginatedResponse[TaskResponse]
