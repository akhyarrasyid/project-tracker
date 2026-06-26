import datetime
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    status: str = Field("Todo")

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in {"Todo", "In Progress", "Done"}:
            raise ValueError("Status must be one of: Todo, In Progress, Done")
        return v

    @field_validator("description", mode="before")
    @classmethod
    def empty_description_to_none(cls, v):
        if v == "":
            return None
        return v

class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    status: str | None = Field(None)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in {"Todo", "In Progress", "Done"}:
            raise ValueError("Status must be one of: Todo, In Progress, Done")
        return v

    @field_validator("description", mode="before")
    @classmethod
    def empty_description_to_none(cls, v):
        if v == "":
            return None
        return v

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime.datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)

