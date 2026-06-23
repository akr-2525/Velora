from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, date


class UserBase(BaseModel):
    name: str
    email: EmailStr
    primary_goal: Optional[str] = None
    focus_areas: List[str] = []
    struggles: List[str] = []
    habits: List[str] = []
    preferred_tone: str = "motivating"
    daily_time_minutes: int = 30
    timezone: str = "UTC"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    primary_goal: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    struggles: Optional[List[str]] = None
    habits: Optional[List[str]] = None
    preferred_tone: Optional[str] = None
    daily_time_minutes: Optional[int] = None
    timezone: Optional[str] = None


class UserStreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_completed_date: Optional[date] = None
    execution_streak: int = 0
    longest_execution_streak: int = 0
    last_execution_date: Optional[date] = None
    freeze_count: int = 0  # Module 7

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: int
    is_admin: bool = False
    is_subscribed: bool = True
    created_at: datetime
    streak: Optional[UserStreakResponse] = None

    class Config:
        from_attributes = True


class DailyCheckInCreate(BaseModel):
    mood_score: int = Field(..., ge=1, le=10)
    energy_score: int = Field(..., ge=1, le=10)
    productivity_score: int = Field(..., ge=1, le=10)
    notes: Optional[str] = None


class DailyCheckInResponse(DailyCheckInCreate):
    id: int
    date: date

    class Config:
        from_attributes = True


class HabitLogResponse(BaseModel):
    id: int
    habit_name: str
    completed_at: datetime

    class Config:
        from_attributes = True


class WeeklyReflectionPayload(BaseModel):
    biggest_distraction: str = Field(..., min_length=3)
    proud_moment: str = Field(..., min_length=3)
    what_went_well: str = Field(..., min_length=3)


class DailyNotePayload(BaseModel):
    notes: str = Field(..., min_length=1)


class WellnessCheckInPayload(BaseModel):
    """Full wellness check-in submitted from the Habits & Wellness tab."""
    mood_score: int = Field(..., ge=1, le=10)
    energy_score: int = Field(..., ge=1, le=10)
    productivity_score: int = Field(..., ge=1, le=10)
    notes: Optional[str] = None


class DailyPriorityPayload(BaseModel):
    priority_text: str = Field(..., min_length=3, max_length=300)


class DailyPriorityResponse(BaseModel):
    id: int
    date: date
    priority_text: str

    class Config:
        from_attributes = True


class ContentItemCreate(BaseModel):
    category: str
    content_type: str
    text: str
    author: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    target_date: Optional[date] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    target_date: Optional[date] = None
    status: Optional[str] = None


class GoalResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    target_date: Optional[date] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
