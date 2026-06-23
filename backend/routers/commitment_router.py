"""
Velora Commitment Router

Module 3 & 4: planned + retroactive commitment types
Module 6: push_to_tomorrow in CommitmentUpdate
Module 8: focus_area on commitment
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from backend.dependencies import get_db, get_current_user
from backend.models.user_model import User
from backend.models.commitment_model import Commitment
from backend.schemas.commitment_schema import (
    CommitmentCreate,
    CommitmentUpdate,
    CommitmentResponse,
    DashboardCommitmentStats,
    RetroactiveLogCreate,
)
from backend.services.commitment_service import (
    create_commitment,
    create_retroactive_commitment,
    update_commitment,
    compute_dashboard_stats,
    delete_commitment,
)

router = APIRouter(prefix="/commitments", tags=["Commitments"])


@router.post("/", response_model=CommitmentResponse)
def create_new_commitment(
    schema: CommitmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a planned time-blocked commitment."""
    return create_commitment(db, current_user.id, schema)


@router.post("/retroactive", response_model=CommitmentResponse)
def log_retroactive_commitment(
    schema: RetroactiveLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Module 4 — 'I Just Did It' quick capture.
    Logs work already completed. Immediately status=completed.
    Never affects execution rate, procrastination, or confidence analytics.
    """
    return create_retroactive_commitment(db, current_user.id, schema)


@router.put("/{commitment_id}", response_model=CommitmentResponse)
def update_existing_commitment(
    commitment_id: int,
    schema: CommitmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log outcome (completion %, failure reason, outcome note),
    reschedule, or push to tomorrow.
    Retroactive commitments cannot be updated.
    """
    updated = update_commitment(db, commitment_id, current_user.id, schema)
    if not updated:
        raise HTTPException(status_code=404, detail="Commitment not found.")
    return updated


@router.get("/daily", response_model=List[CommitmentResponse])
def get_daily_commitments(
    date: Optional[str] = None,
    user_timezone: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    All commitments for a specific date.
    DB stores naive local times — filter directly by date.
    """
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
            )
    else:
        target_date = datetime.now().date()

    commitments = (
        db.query(Commitment)
        .filter(Commitment.user_id == current_user.id)
        .order_by(Commitment.start_time)
        .all()
    )
    return [c for c in commitments if c.start_time.date() == target_date]


@router.get("/analytics/dashboard", response_model=DashboardCommitmentStats)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Multi-timeframe execution + time-allocation stats."""
    return compute_dashboard_stats(db, current_user.id)


@router.get("/recent", response_model=List[CommitmentResponse])
def get_recent_commitments(
    limit: int = 10,
    commitment_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recent commitments, optionally filtered by type."""
    q = db.query(Commitment).filter(Commitment.user_id == current_user.id)
    if commitment_type in ("planned", "retroactive"):
        q = q.filter(Commitment.commitment_type == commitment_type)
    return q.order_by(Commitment.start_time.desc()).limit(
        max(1, min(limit, 50))
    ).all()


@router.delete("/{commitment_id}")
def remove_commitment(
    commitment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a commitment."""
    success = delete_commitment(db, commitment_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Commitment not found or unauthorized."
        )
    return {"message": "Commitment deleted."}
