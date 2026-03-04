from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChatRequest(BaseModel):
    goal_id: str
    message: str = Field(min_length=1)


class CheckinPayload(BaseModel):
    worked_today: bool
    notes: str = ""
    blockers: str = ""
    energy_level: str = "steady"
