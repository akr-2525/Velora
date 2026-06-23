"""
Telemetry router.
Note: Daily check-ins are primarily captured via the one-click email buttons
(GET /analytics/email-checkin). This endpoint exists for programmatic or
dashboard-based overrides only.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from backend.dependencies import get_current_user, get_db
from backend.models.user_model import User, DailyCheckIn
from backend.schemas.user_schema import DailyCheckInCreate, DailyCheckInResponse

router = APIRouter(prefix="/checkins", tags=["Telemetry"])


@router.get("/today", response_model=Optional[DailyCheckInResponse])
def get_todays_checkin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch today's check-in if it exists, so the wellness sliders can pre-fill.
    Returns null (HTTP 200 with null body) if no check-in yet today.
    """
    today = datetime.now(timezone.utc).date()
    existing = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == current_user.id,
        DailyCheckIn.date == today,
    ).first()
    return existing  # None returns as null in JSON, Pydantic Optional handles it


@router.post("/", response_model=DailyCheckInResponse)
def submit_daily_checkin(
    checkin_data: DailyCheckInCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manual check-in override.
    The primary check-in path is the email one-click button at /analytics/email-checkin.
    Use this endpoint for testing or if building a future in-app check-in UI.
    """
    today = datetime.now(timezone.utc).date()

    existing = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == current_user.id,
        DailyCheckIn.date == today,
    ).first()

    if existing:
        existing.mood_score = checkin_data.mood_score
        existing.energy_score = checkin_data.energy_score
        existing.productivity_score = checkin_data.productivity_score
        if checkin_data.notes is not None:
            existing.notes = checkin_data.notes
        db.commit()
        db.refresh(existing)
        return existing

    new_checkin = DailyCheckIn(
        user_id=current_user.id,
        date=today,
        mood_score=checkin_data.mood_score,
        energy_score=checkin_data.energy_score,
        productivity_score=checkin_data.productivity_score,
        notes=checkin_data.notes,
    )
    db.add(new_checkin)
    db.commit()
    db.refresh(new_checkin)
    return new_checkin
