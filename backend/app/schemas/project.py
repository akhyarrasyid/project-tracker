from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    key: str = Field(..., min_length=2, max_length=10)
    description: Optional[str] = None
    team_id: int

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    key: str
    description: Optional[str] = None
    team_id: int
    status: str
