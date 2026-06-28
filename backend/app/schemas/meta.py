from pydantic import BaseModel, ConfigDict
from typing import Optional

class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None

class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    department_id: int
    description: Optional[str] = None

class ProjectMetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    key: str
    status: str

class UserMetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
