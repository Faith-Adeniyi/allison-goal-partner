from datetime import datetime
from typing import Literal, Optional

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


class ChatHistoryItem(BaseModel):
    sender: Literal["user", "ai", "assistant", "system"] = "user"
    text: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    goal_id: str = "general"
    message: str = Field(min_length=1, max_length=4000)
    mode: str = "assistant"
    chat_history: list[ChatHistoryItem] = Field(default_factory=list)
    conversation_id: Optional[str] = None


class CheckinPayload(BaseModel):
    worked_today: bool
    notes: str = ""
    blockers: str = ""
    energy_level: str = "steady"


class DueDateUpdate(BaseModel):
    due_date: Optional[str] = Field(
        default=None,
        description="ISO date string (YYYY-MM-DD) or null to clear.",
    )


class TaskUpdatePayload(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=240)
    due_date: Optional[str] = Field(
        default=None,
        description="ISO date string (YYYY-MM-DD) or null to clear.",
    )


class PlanMetaUpdatePayload(BaseModel):
    target_date: Optional[str] = Field(
        default=None,
        description="Goal target date as ISO date string (YYYY-MM-DD).",
    )


class StreakStatus(BaseModel):
    current_streak: int = 0
    longest_streak: int = 0
    last_active_date: Optional[str] = None  # YYYY-MM-DD
    freeze_available: int = 1  # 1 freeze per week
    freeze_week_key: Optional[str] = None  # e.g. '2026-W10'


class IntentRouter(BaseModel):
    """Schema for intent classification with strict two-phase commitment protocol."""
    # Dictates the operational mode: 0 designates Conversational Coach, 1 designates Plan Builder.
    action_mode: int = Field(
        default=0,
        description="Must remain 0 unless the user has explicitly confirmed they want a structural plan built."
    )
    conversational_reply: str = Field(
        description="The appropriate text reply to the user if action_mode is False."
    )
    Goal_Topic_Summary: str = Field(
        description="A brief summary of the user's goal topic, extracted exclusively if action_mode is True."
    )
