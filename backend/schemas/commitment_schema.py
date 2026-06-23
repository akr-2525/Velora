from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


# ── CREATE ────────────────────────────────────────────────────────────────────

class CommitmentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    linked_goal_id: Optional[int] = None
    focus_area: Optional[str] = None
    start_time: datetime
    end_time: datetime
    confidence_level: Optional[int] = Field(None, ge=0, le=100)
    # commitment_type defaults to "planned" — only set to "retroactive" by the
    # retroactive-log endpoint which calls create_retroactive_commitment()
    commitment_type: Literal["planned", "retroactive"] = "planned"


class RetroactiveLogCreate(BaseModel):
    """Quick-capture form: I Just Did It. No scheduling, no confidence."""
    title: str = Field(..., min_length=3, max_length=300)
    duration_minutes: int = Field(..., ge=5, le=480)
    focus_area: Optional[str] = None
    linked_goal_id: Optional[int] = None
    outcome_note: Optional[str] = Field(None, max_length=500)


# ── UPDATE ────────────────────────────────────────────────────────────────────

class CommitmentUpdate(BaseModel):
    status: Optional[str] = Field(
        None, description="pending, active, completed, partial, missed"
    )
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    outcome_note: Optional[str] = Field(None, max_length=500)
    failure_reason: Optional[str] = Field(
        None,
        description=(
            "external_blocker | underestimated_time | distraction_avoidance"
        ),
    )
    # Reschedule fields
    new_start_time: Optional[datetime] = None
    new_end_time: Optional[datetime] = None
    # Push-to-tomorrow convenience (overrides new_start/end_time calculation)
    push_to_tomorrow: bool = False


# ── RESPONSE ──────────────────────────────────────────────────────────────────

class CommitmentResponse(BaseModel):
    id: int
    user_id: int
    title: str
    linked_goal_id: Optional[int] = None
    focus_area: Optional[str] = None
    start_time: datetime
    end_time: datetime
    commitment_type: str
    confidence_level: Optional[int] = None
    status: str
    completion_percentage: int
    outcome_note: Optional[str] = None
    failure_reason: Optional[str] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    reschedule_count: int
    procrastination_flag: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── ANALYTICS SCHEMAS ─────────────────────────────────────────────────────────

class DurationStats(BaseModel):
    short_session_rate: float
    medium_session_rate: float
    long_session_rate: float


class TimeframeStats(BaseModel):
    # Execution metrics (planned only)
    total_planned: int
    completed_count: int
    missed_count: int
    partial_count: int
    completion_rate_percentage: float
    procrastination_count: int
    overconfidence_flag: bool
    underconfidence_flag: bool
    recovery_rate_percentage: float
    best_time_slot: Optional[str]
    worst_time_slot: Optional[str]
    duration_stats: DurationStats
    # Time-allocation metrics (planned + retroactive)
    total_work_minutes: int
    retroactive_minutes: int
    focus_area_breakdown: dict  # {"Area Name": minutes, ...}


class DashboardCommitmentStats(BaseModel):
    current_week: TimeframeStats
    previous_week: TimeframeStats
    previous_month: Optional[TimeframeStats] = None
