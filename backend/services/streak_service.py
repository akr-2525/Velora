"""
Velora Streak Service
Handles both habit streak and streak freeze logic (Module 7).

HABIT STREAK RULES:
- Increments when user marks habit done (from email button or sidebar)
- If a day is missed and freeze_count > 0: consume one freeze, preserve streak
- If a day is missed and freeze_count == 0: streak resets to 1 (new start)
- Every 14 consecutive days earns +1 freeze (max 3 stored)

EXECUTION STREAK:
- Separate counter for days with at least one completed *planned* commitment
- Updated automatically inside commitment_service when status → completed
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.models.user_model import UserStreak, HabitLog


def update_user_streak(db: Session, user_id: int):
    """
    Core habit streak update.
    Called from:
      - POST /streaks/complete  (sidebar button, JWT required)
      - GET  /streaks/email-complete  (email button, no JWT)
    """
    streak = db.query(UserStreak).filter(UserStreak.user_id == user_id).first()

    if not streak:
        streak = UserStreak(
            user_id=user_id,
            current_streak=0,
            longest_streak=0,
            execution_streak=0,
            longest_execution_streak=0,
            freeze_count=0,
        )
        db.add(streak)

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    # Already logged today — idempotent
    if streak.last_completed_date == today:
        return streak, "Already logged today. Keep it up!"

    # ── Consecutive day: extend streak ──
    if streak.last_completed_date == yesterday:
        streak.current_streak = (streak.current_streak or 0) + 1

    # ── Gap detected: check for freeze ──
    elif streak.last_completed_date is not None:
        if (streak.freeze_count or 0) > 0:
            # Consume one freeze — streak is preserved
            streak.freeze_count -= 1
            streak.current_streak = (streak.current_streak or 0) + 1
            # We'll still log the habit and update the date
        else:
            # Hard reset
            streak.current_streak = 1

    # ── First ever log ──
    else:
        streak.current_streak = 1

    # Update longest streak
    if (streak.current_streak or 0) > (streak.longest_streak or 0):
        streak.longest_streak = streak.current_streak

    # ── Freeze accumulation: earn 1 freeze per 14 consecutive days ──
    if (streak.current_streak or 0) > 0 and (streak.current_streak % 14) == 0:
        if (streak.freeze_count or 0) < 3:
            streak.freeze_count = (streak.freeze_count or 0) + 1

    streak.last_completed_date = today

    # Log the habit name
    from backend.models.user_model import User
    user = db.query(User).filter(User.id == user_id).first()
    habit_name = (
        user.habits[0] if user and user.habits else "Daily Core Habits"
    )

    db.add(HabitLog(
        user_id=user_id,
        habit_name=habit_name,
        completed_at=datetime.now(timezone.utc),
    ))

    db.commit()
    db.refresh(streak)

    freeze_msg = ""
    if streak.freeze_count and streak.freeze_count > 0:
        freeze_msg = f" ({streak.freeze_count} freeze{'s' if streak.freeze_count != 1 else ''} available)"

    msg = f"Streak updated! {streak.current_streak} day streak{freeze_msg} 🔥"
    return streak, msg
