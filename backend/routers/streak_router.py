"""
Velora Streak Router

Module 2: Email-first habit system
  - POST /streaks/complete     — JWT required (sidebar button)
  - GET  /streaks/email-complete — NO JWT (email CTA button, plain <a href>)

Both paths call the same update_user_streak() service so all freeze/streak
logic is shared.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.dependencies import get_current_user, get_db
from backend.models.user_model import User
from backend.services.streak_service import update_user_streak

router = APIRouter(prefix="/streaks", tags=["Streaks"])


# ── Authenticated path (sidebar button) ────────────────────────────────────

@router.post("/complete")
def mark_habit_complete(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark habit done for today — called from the Habits & Wellness tab."""
    streak, message = update_user_streak(db, current_user.id)
    return {
        "message":                  message,
        "current_streak":           streak.current_streak,
        "longest_streak":           streak.longest_streak,
        "execution_streak":         streak.execution_streak or 0,
        "longest_execution_streak": streak.longest_execution_streak or 0,
        "freeze_count":             streak.freeze_count or 0,
    }


# ── Email CTA path — NO JWT required (Module 2) ─────────────────────────────

@router.get("/email-complete")
def email_habit_complete(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Called when a user taps the primary CTA in their daily email:
    '✅ I completed my core habit today'

    No login required. Returns a branded HTML confirmation page.
    Idempotent — safe to call multiple times on the same day.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return HTMLResponse(
            content="<h2>User not found.</h2>", status_code=404
        )

    streak, message = update_user_streak(db, user_id)
    first_name = user.name.split()[0]

    already_done = "already logged" in message.lower()

    freeze_html = ""
    if (streak.freeze_count or 0) > 0:
        freeze_html = (
            f'<p style="color:#a78bfa;font-size:13px;margin-top:8px;">'
            f'{streak.freeze_count} streak freeze{"s" if streak.freeze_count != 1 else ""} available</p>'
        )

    if already_done:
        emoji = "✅"
        headline = f"Already logged today, {first_name}!"
        sub = "You're on it. Your streak is safe."
    else:
        emoji = "🔥"
        headline = f"{streak.current_streak} day streak, {first_name}!"
        sub = "Core habit logged. Your AI coach sees this."

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Velora — Habit Logged</title>
  <style>
    body {{
      margin:0; padding:0;
      font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
      background:#1a1a2e;
      display:flex; align-items:center; justify-content:center;
      min-height:100vh;
    }}
    .card {{
      background:#fff; border-radius:16px;
      padding:48px 40px; max-width:420px; width:90%;
      text-align:center; box-shadow:0 20px 60px rgba(0,0,0,0.3);
    }}
    .brand {{ color:#a78bfa; font-size:11px; font-weight:700;
              letter-spacing:2px; text-transform:uppercase; margin-bottom:12px; }}
    .emoji {{ font-size:56px; margin-bottom:16px; }}
    h2 {{ color:#1a1a2e; font-size:22px; margin:0 0 10px; }}
    p {{ color:#6b7280; font-size:15px; line-height:1.6; margin:0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="brand">Velora</div>
    <div class="emoji">{emoji}</div>
    <h2>{headline}</h2>
    <p>{sub}</p>
    {freeze_html}
  </div>
</body>
</html>"""

    return HTMLResponse(content=html)
