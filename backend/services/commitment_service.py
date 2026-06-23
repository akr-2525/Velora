"""
Velora Commitment Service

EXECUTION SYSTEM (planned commitments only):
- completion rate, procrastination, recovery, confidence calibration
- time-slot efficiency, duration success rates
- execution streak updates

WELLNESS SYSTEM (planned + retroactive):
- total_work_minutes, retroactive_minutes
- focus_area_breakdown (pie chart data)

Module 3: commitment_type = "planned" | "retroactive"
Module 4: create_retroactive_commitment()
Module 5: procrastination redesign — reschedule_count >= 2 OR distraction_avoidance
Module 6: push_to_tomorrow
Module 8: focus_area tagging + allocation analytics
Module 9: analytics separation by commitment_type
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from backend.models.commitment_model import Commitment
from backend.models.user_model import UserStreak
from backend.schemas.commitment_schema import (
    CommitmentCreate,
    CommitmentUpdate,
    RetroactiveLogCreate,
    DashboardCommitmentStats,
    TimeframeStats,
    DurationStats,
)
from fastapi import HTTPException


def _aware(dt: datetime) -> datetime:
    if not dt:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _duration_minutes(c: Commitment) -> float:
    return (_aware(c.end_time) - _aware(c.start_time)).total_seconds() / 60


# ─────────────────────────────────────────────────────────────────────────────
# CREATE — PLANNED
# ─────────────────────────────────────────────────────────────────────────────

def create_commitment(db: Session, user_id: int, schema: CommitmentCreate) -> Commitment:
    now = datetime.now(timezone.utc)

    if _aware(schema.start_time) < (now - timedelta(minutes=5)):
        raise HTTPException(
            status_code=400, detail="Cannot schedule a commitment in the past."
        )
    if _aware(schema.end_time) <= _aware(schema.start_time):
        raise HTTPException(
            status_code=400, detail="End time must be after start time."
        )

    # Overlap check — only against non-finished planned commitments
    overlapping = db.query(Commitment).filter(
        Commitment.user_id == user_id,
        Commitment.commitment_type == "planned",
        Commitment.status.notin_(["missed", "completed"]),
        Commitment.start_time < schema.end_time,
        Commitment.end_time > schema.start_time,
    ).first()

    if overlapping:
        raise HTTPException(
            status_code=400,
            detail=f"Time slot overlaps with '{overlapping.title}'.",
        )

    c = Commitment(
        user_id=user_id,
        linked_goal_id=schema.linked_goal_id,
        focus_area=schema.focus_area,
        title=schema.title,
        start_time=schema.start_time,
        end_time=schema.end_time,
        confidence_level=schema.confidence_level,
        commitment_type="planned",
        status="pending",
        completion_percentage=0,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# CREATE — RETROACTIVE (Module 4)
# ─────────────────────────────────────────────────────────────────────────────

def create_retroactive_commitment(
    db: Session, user_id: int, schema: RetroactiveLogCreate
) -> Commitment:
    """
    Quick-capture: 'I Just Did It'.
    start_time = now - duration_minutes
    end_time   = now
    status     = completed (immediately, no lifecycle)
    commitment_type = retroactive
    Never affects procrastination, confidence, or recovery metrics.
    """
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=schema.duration_minutes)

    c = Commitment(
        user_id=user_id,
        linked_goal_id=schema.linked_goal_id,
        focus_area=schema.focus_area,
        title=schema.title,
        start_time=start_time,
        end_time=now,
        commitment_type="retroactive",
        status="completed",
        completion_percentage=100,
        actual_start_time=start_time,
        actual_end_time=now,
        outcome_note=schema.outcome_note,
        confidence_level=None,
        procrastination_flag=False,
        reschedule_count=0,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    # Retroactive work counts toward execution streak
    _update_execution_streak(db, user_id)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE — PLANNED ONLY
# ─────────────────────────────────────────────────────────────────────────────

def update_commitment(
    db: Session, commitment_id: int, user_id: int, schema: CommitmentUpdate
) -> Commitment:
    c = db.query(Commitment).filter(
        Commitment.id == commitment_id,
        Commitment.user_id == user_id,
    ).first()

    if not c:
        return None

    # Retroactive commitments cannot be mutated post-creation
    if c.commitment_type == "retroactive":
        raise HTTPException(
            status_code=400,
            detail="Retroactive logs cannot be updated after creation.",
        )

    # ── Module 6: Push to Tomorrow ──────────────────────────────────────────
    if schema.push_to_tomorrow:
        # DB stores naive local times — add 1 day directly, no timezone conversion.
        new_start = c.start_time + timedelta(days=1)
        new_end   = c.end_time   + timedelta(days=1)

        overlapping = db.query(Commitment).filter(
            Commitment.id != commitment_id,
            Commitment.user_id == user_id,
            Commitment.commitment_type == "planned",
            Commitment.status.notin_(["missed", "completed"]),
            Commitment.start_time < new_end,
            Commitment.end_time > new_start,
        ).first()
        if overlapping:
            raise HTTPException(
                status_code=400,
                detail=f"Tomorrow that slot overlaps with '{overlapping.title}'.",
            )

        c.start_time = new_start
        c.end_time   = new_end
        c.reschedule_count += 1

        if c.reschedule_count >= 2:
            c.procrastination_flag = True

        db.commit()
        db.refresh(c)
        return c

    # ── Reschedule via explicit new times ───────────────────────────────────
    if schema.new_start_time and schema.new_end_time:
        if _aware(schema.new_end_time) <= _aware(schema.new_start_time):
            raise HTTPException(
                status_code=400, detail="New end time must be after new start time."
            )
        overlapping = db.query(Commitment).filter(
            Commitment.id != commitment_id,
            Commitment.user_id == user_id,
            Commitment.commitment_type == "planned",
            Commitment.status.notin_(["missed", "completed"]),
            Commitment.start_time < schema.new_end_time,
            Commitment.end_time > schema.new_start_time,
        ).first()
        if overlapping:
            raise HTTPException(
                status_code=400,
                detail="Rescheduled time overlaps with another commitment.",
            )
        c.start_time = schema.new_start_time
        c.end_time = schema.new_end_time
        c.reschedule_count += 1
        if c.reschedule_count >= 2:
            c.procrastination_flag = True

    # ── Completion percentage path ───────────────────────────────────────────
    if schema.completion_percentage is not None:
        c.completion_percentage = schema.completion_percentage
        if schema.completion_percentage == 100:
            c.status = "completed"
            c.actual_end_time = datetime.now(timezone.utc)
        elif schema.completion_percentage > 0:
            c.status = "partial"
            c.actual_end_time = datetime.now(timezone.utc)
        else:
            c.status = "missed"

    # ── Direct status path ───────────────────────────────────────────────────
    if schema.status and schema.completion_percentage is None:
        c.status = schema.status
        if schema.status == "active" and not c.actual_start_time:
            c.actual_start_time = datetime.now(timezone.utc)
        elif schema.status == "completed":
            c.completion_percentage = 100
            c.actual_end_time = datetime.now(timezone.utc)

    # ── Outcome note ─────────────────────────────────────────────────────────
    if schema.outcome_note is not None:
        c.outcome_note = schema.outcome_note

    # ── Module 5: Failure reason ─────────────────────────────────────────────
    if schema.failure_reason is not None:
        valid_reasons = {
            "external_blocker", "underestimated_time", "distraction_avoidance"
        }
        if schema.failure_reason not in valid_reasons:
            raise HTTPException(
                status_code=400,
                detail=f"failure_reason must be one of: {valid_reasons}",
            )
        c.failure_reason = schema.failure_reason
        # Only distraction_avoidance triggers procrastination flag
        if schema.failure_reason == "distraction_avoidance":
            c.procrastination_flag = True

    db.commit()
    db.refresh(c)

    # Update execution streak if just completed
    if c.status == "completed":
        _update_execution_streak(db, user_id)

    return c


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION STREAK UPDATE (called internally)
# ─────────────────────────────────────────────────────────────────────────────

def _update_execution_streak(db: Session, user_id: int):
    streak = db.query(UserStreak).filter(UserStreak.user_id == user_id).first()
    if not streak:
        streak = UserStreak(user_id=user_id)
        db.add(streak)

    today = datetime.now(timezone.utc).date()
    if streak.last_execution_date == today:
        db.commit()
        return

    if streak.last_execution_date == today - timedelta(days=1):
        streak.execution_streak = (streak.execution_streak or 0) + 1
    else:
        streak.execution_streak = 1

    if (streak.execution_streak or 0) > (streak.longest_execution_streak or 0):
        streak.longest_execution_streak = streak.execution_streak

    streak.last_execution_date = today
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-FINALIZE (only planned; retroactive always stays completed)
# ─────────────────────────────────────────────────────────────────────────────

def auto_finalize_expired_commitments(db: Session):
    now = datetime.now(timezone.utc)
    candidates = db.query(Commitment).filter(
        Commitment.commitment_type == "planned",
        Commitment.status.in_(["pending", "active"]),
    ).all()

    finalized = 0
    for c in candidates:
        if _aware(c.end_time) < now:
            c.status = "missed" if c.completion_percentage == 0 else "partial"
            finalized += 1

    if finalized:
        db.commit()
        print(f"[Velora] Auto-finalized {finalized} expired planned commitments.")


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────────────────────────────────

def delete_commitment(db: Session, commitment_id: int, user_id: int) -> bool:
    c = db.query(Commitment).filter(
        Commitment.id == commitment_id,
        Commitment.user_id == user_id,
    ).first()
    if not c:
        return False
    db.delete(c)
    db.commit()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# STATS ENGINE — Module 9: strict separation by commitment_type
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_timeframe_stats(all_commitments: list) -> TimeframeStats:
    """
    Module 9 separation:
    - Execution metrics: planned only
    - Time-allocation metrics: planned + retroactive
    """
    planned = [c for c in all_commitments if c.commitment_type == "planned"]
    total_p = len(planned)

    # ── Execution metrics (planned only) ────────────────────────────────────
    if total_p == 0:
        exec_stats = dict(
            total_planned=0,
            completed_count=0,
            missed_count=0,
            partial_count=0,
            completion_rate_percentage=0.0,
            procrastination_count=0,
            overconfidence_flag=False,
            underconfidence_flag=False,
            recovery_rate_percentage=0.0,
            best_time_slot=None,
            worst_time_slot=None,
            duration_stats=DurationStats(
                short_session_rate=0.0,
                medium_session_rate=0.0,
                long_session_rate=0.0,
            ),
        )
    else:
        completed = sum(1 for c in planned if c.status == "completed")
        missed    = sum(1 for c in planned if c.status == "missed")
        partial   = sum(1 for c in planned if c.status == "partial")
        proca_cnt = sum(1 for c in planned if c.procrastination_flag)

        completion_rate = (completed / total_p) * 100

        # Confidence calibration
        comp_conf = [c.confidence_level for c in planned
                     if c.status == "completed" and c.confidence_level is not None]
        miss_conf = [c.confidence_level for c in planned
                     if c.status == "missed" and c.confidence_level is not None]
        avg_comp_conf = sum(comp_conf) / len(comp_conf) if comp_conf else 0
        avg_miss_conf = sum(miss_conf) / len(miss_conf) if miss_conf else 0
        overconf  = (avg_miss_conf > 80) and (completion_rate < 50)
        underconf = (avg_comp_conf < 40) and (completion_rate > 80)

        # Recovery rate: of all missed blocks this week, what % were followed
        # by a completed block on the SAME OR NEXT day (not just next in list)
        sorted_p = sorted(planned, key=lambda c: _aware(c.start_time))
        missed_opps = recoveries = 0
        for i, c in enumerate(sorted_p):
            if c.status == "missed":
                missed_opps += 1
                # Check if any subsequent block on same or next day was completed
                c_date = _aware(c.start_time).date()
                for j in range(i + 1, len(sorted_p)):
                    nxt = sorted_p[j]
                    nxt_date = _aware(nxt.start_time).date()
                    if (nxt_date - c_date).days <= 1:
                        if nxt.status == "completed":
                            recoveries += 1
                            break
                    else:
                        break  # too far ahead, no recovery
        recovery_rate = (recoveries / missed_opps * 100) if missed_opps else 0.0

        # Time-slot efficiency
        slots = {"Morning": [0, 0], "Afternoon": [0, 0],
                 "Evening": [0, 0], "Night": [0, 0]}
        for c in planned:
            h = _aware(c.start_time).hour
            s = ("Morning" if 5 <= h < 12 else "Afternoon" if 12 <= h < 17
                 else "Evening" if 17 <= h < 21 else "Night")
            slots[s][0] += 1
            if c.status == "completed":
                slots[s][1] += 1

        best_slot = worst_slot = None
        hi, lo = -1.0, 101.0
        for sname, (tot, comp_s) in slots.items():
            if tot > 0:
                r = comp_s / tot
                if r > hi:
                    hi = r; best_slot = sname
                if r < lo:
                    lo = r; worst_slot = sname

        # Duration buckets
        dur = {"short": [0, 0], "medium": [0, 0], "long": [0, 0]}
        for c in planned:
            mins = _duration_minutes(c)
            b = "short" if mins < 60 else "medium" if mins <= 120 else "long"
            dur[b][0] += 1
            if c.status == "completed":
                dur[b][1] += 1

        def _r(bucket):
            return round(dur[bucket][1] / dur[bucket][0] * 100, 2) if dur[bucket][0] else 0.0

        exec_stats = dict(
            total_planned=total_p,
            completed_count=completed,
            missed_count=missed,
            partial_count=partial,
            completion_rate_percentage=round(completion_rate, 2),
            procrastination_count=proca_cnt,
            overconfidence_flag=overconf,
            underconfidence_flag=underconf,
            recovery_rate_percentage=round(recovery_rate, 2),
            best_time_slot=best_slot,
            worst_time_slot=worst_slot,
            duration_stats=DurationStats(
                short_session_rate=_r("short"),
                medium_session_rate=_r("medium"),
                long_session_rate=_r("long"),
            ),
        )

    # ── Time-allocation metrics (planned + retroactive) ──────────────────────
    total_work_minutes = 0
    retro_minutes = 0
    focus_breakdown: dict = {}

    for c in all_commitments:
        mins = _duration_minutes(c)
        total_work_minutes += int(mins)
        if c.commitment_type == "retroactive":
            retro_minutes += int(mins)
        if c.focus_area:
            focus_breakdown[c.focus_area] = (
                focus_breakdown.get(c.focus_area, 0) + int(mins)
            )

    return TimeframeStats(
        **exec_stats,
        total_work_minutes=total_work_minutes,
        retroactive_minutes=retro_minutes,
        focus_area_breakdown=focus_breakdown,
    )


def compute_dashboard_stats(db: Session, user_id: int) -> DashboardCommitmentStats:
    now = datetime.now(timezone.utc)
    one_week_ago   = now - timedelta(days=7)
    two_weeks_ago  = now - timedelta(days=14)
    sixty_days_ago = now - timedelta(days=60)
    thirty_days_ago = now - timedelta(days=30)

    def _fetch(start, end=None):
        q = db.query(Commitment).filter(
            Commitment.user_id == user_id,
            Commitment.created_at >= start,
        )
        if end:
            q = q.filter(Commitment.created_at < end)
        return q.all()

    return DashboardCommitmentStats(
        current_week=_calculate_timeframe_stats(_fetch(one_week_ago)),
        previous_week=_calculate_timeframe_stats(_fetch(two_weeks_ago, one_week_ago)),
        previous_month=_calculate_timeframe_stats(
            _fetch(sixty_days_ago, thirty_days_ago)
        ),
    )
