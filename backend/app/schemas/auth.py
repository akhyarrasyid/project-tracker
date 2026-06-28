from typing import Optional

from pydantic import BaseModel


class LoginPayload(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None


class UserMe(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    team_id: int

    class Config:
        from_attributes = True
