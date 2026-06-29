import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.task import TaskUpdate, _serialize_dt


class IssueUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str


class IssueUpdateRequest(TaskUpdate):
    expected_version: int = Field(..., ge=1)


class IssueCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    parent_id: Optional[int] = None

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
        return value


class IssueCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    content: str
    parent_id: Optional[int] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    author: IssueUserSummary

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime.datetime, _info) -> str:
        return _serialize_dt(dt)


class IssueActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: Optional[int] = None
    project_id: Optional[int] = None
    action: str
    field: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime.datetime
    actor: IssueUserSummary

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime.datetime, _info) -> str:
        return _serialize_dt(dt)
