from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from backend.dependencies import get_current_user, get_db
from backend.models.user_model import (
    User, WeeklyReflection, ContentItem, DailyCheckIn, EmailEvent
)
from backend.schemas.user_schema import (
    WeeklyReflectionPayload,
    DailyNotePayload,
    WellnessCheckInPayload,
    DailyPriorityPayload,
    DailyPriorityResponse,
    ContentItemCreate,
)
from backend.models.user_model import DailyPriority
from backend.services.analytics_service import get_weekly_analytics, generate_weekly_behavioral_insight
from backend.services.scheduler_service import send_all_weekly_reports
router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ------------------------------------------------------------------
# WEEKLY SUMMARY
# ------------------------------------------------------------------

@router.get("/weekly")
def get_weekly_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """7-day performance analytics for the dashboard."""
    return get_weekly_analytics(db, current_user.id)


# ------------------------------------------------------------------
# EMAIL CHECK-IN (one-click from daily email)
# PRODUCTION FIX: This endpoint was missing — it's the core telemetry path.
# ------------------------------------------------------------------

@router.get("/email-checkin")
def email_checkin(
    user_id: int,
    energy: int,
    focus: int,
    db: Session = Depends(get_db),
):
    """
    Called when a user clicks an energy button in their daily email.
    Upserts a DailyCheckIn and logs an EmailEvent (clicked) for engagement tracking.
    Returns a friendly HTML confirmation page — no login required.
    """
    if not (1 <= energy <= 10) or not (1 <= focus <= 10):
        raise HTTPException(status_code=400, detail="Energy and focus must be between 1 and 10.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    today = datetime.now(timezone.utc).date()

    # Upsert DailyCheckIn
    existing = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.date == today,
    ).first()

    if existing:
        existing.energy_score = energy
        existing.productivity_score = focus
        # Only update mood if not already set at a better resolution
        if existing.mood_score == 5:  # default neutral — override it
            existing.mood_score = energy
    else:
        new_checkin = DailyCheckIn(
            user_id=user_id,
            date=today,
            mood_score=energy,
            energy_score=energy,
            productivity_score=focus,
        )
        db.add(new_checkin)

    # Log email click event for engagement engine
    db.add(EmailEvent(user_id=user_id, event_type="clicked"))

    db.commit()

    # Return a branded HTML confirmation page
    first_name = user.name.split()[0]
    label_map = {
        range(1, 4): ("😴", "Low energy logged"),
        range(4, 7): ("😐", "Steady energy logged"),
        range(7, 11): ("⚡", "High energy logged"),
    }
    label = "Energy logged"
    emoji = "✅"
    for r, (e, l) in label_map.items():
        if energy in r:
            emoji, label = e, l
            break

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1.0">
        <title>Velora — Logged</title>
        <style>
            body {{
                margin: 0; padding: 0;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                background: #1a1a2e;
                display: flex; align-items: center; justify-content: center;
                min-height: 100vh;
            }}
            .card {{
                background: #ffffff; border-radius: 16px;
                padding: 48px 40px; max-width: 420px; width: 90%;
                text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .emoji {{ font-size: 52px; margin-bottom: 16px; }}
            .brand {{ color: #a78bfa; font-size: 11px; font-weight: 700;
                      letter-spacing: 2px; text-transform: uppercase; margin-bottom: 12px; }}
            h2 {{ color: #1a1a2e; font-size: 22px; margin: 0 0 10px; }}
            p {{ color: #6b7280; font-size: 15px; line-height: 1.6; margin: 0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="brand">Velora</div>
            <div class="emoji">{emoji}</div>
            <h2>{label}, {first_name}</h2>
            <p>Your energy has been noted for today.<br>
               Your AI coach will use this to personalize tomorrow's morning brief.</p>
        </div>
    </body>
    </html>
    """

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


# ------------------------------------------------------------------
# WEEKLY REFLECTION
# ------------------------------------------------------------------

@router.post("/reflections")
def save_deep_weekly_reflection(
    payload: WeeklyReflectionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save or overwrite this week's reflection. Upserts on the current week's end date."""
    today = datetime.now(timezone.utc).date()
    days_ahead = 6 - today.weekday()
    if days_ahead < 0:
        days_ahead += 7
    week_end = today + timedelta(days=days_ahead)

    ref = db.query(WeeklyReflection).filter(
        WeeklyReflection.user_id == current_user.id,
        WeeklyReflection.week_ending_date == week_end,
    ).first()

    if not ref:
        ref = WeeklyReflection(
            user_id=current_user.id,
            week_ending_date=week_end,
            what_went_well=payload.what_went_well,
            biggest_distraction=payload.biggest_distraction,
            proud_moment=payload.proud_moment,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ref)
    else:
        ref.what_went_well = payload.what_went_well
        ref.biggest_distraction = payload.biggest_distraction
        ref.proud_moment = payload.proud_moment

    db.commit()
    return {"message": "Weekly reflection saved."}


# ------------------------------------------------------------------
# DAILY NOTE
# ------------------------------------------------------------------

@router.put("/daily-note")
def save_daily_note(
    payload: DailyNotePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save or update today's free-text note (overrides the email check-in note)."""
    today = datetime.now(timezone.utc).date()
    log = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == current_user.id,
        DailyCheckIn.date == today,
    ).first()

    if log:
        log.notes = payload.notes
    else:
        new_log = DailyCheckIn(
            user_id=current_user.id,
            date=today,
            mood_score=5,
            energy_score=5,
            productivity_score=5,
            notes=payload.notes,
        )
        db.add(new_log)

    db.commit()
    return {"message": "Daily note saved."}


# ------------------------------------------------------------------
# WELLNESS CHECK-IN  (in-app sliders — Priority Fix #1)
# Upserts today's DailyCheckIn with all three scores + optional note.
# This is the full-resolution write path; email buttons only capture energy.
# ------------------------------------------------------------------

@router.post("/wellness-checkin")
def save_wellness_checkin(
    payload: WellnessCheckInPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called from the Habits & Wellness tab sliders.
    Upserts today's DailyCheckIn with mood, energy, productivity, and notes.
    Overwrites any partial data previously set by the email one-click buttons.
    """
    today = datetime.now(timezone.utc).date()
    existing = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == current_user.id,
        DailyCheckIn.date == today,
    ).first()

    if existing:
        existing.mood_score         = payload.mood_score
        existing.energy_score       = payload.energy_score
        existing.productivity_score = payload.productivity_score
        if payload.notes is not None:
            existing.notes = payload.notes
    else:
        db.add(DailyCheckIn(
            user_id=current_user.id,
            date=today,
            mood_score=payload.mood_score,
            energy_score=payload.energy_score,
            productivity_score=payload.productivity_score,
            notes=payload.notes,
        ))

    db.commit()
    return {"message": "Wellness check-in saved."}


# ------------------------------------------------------------------
# DAILY PRIORITY  ("What would make today successful?")
# ------------------------------------------------------------------

@router.post("/daily-priority")
def save_daily_priority(
    payload: DailyPriorityPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upsert today's single most important priority."""
    today = datetime.now(timezone.utc).date()
    existing = db.query(DailyPriority).filter(
        DailyPriority.user_id == current_user.id,
        DailyPriority.date == today,
    ).first()

    if existing:
        existing.priority_text = payload.priority_text
    else:
        db.add(DailyPriority(
            user_id=current_user.id,
            date=today,
            priority_text=payload.priority_text,
        ))
    db.commit()
    return {"message": "Priority saved."}


@router.get("/daily-priority", response_model=DailyPriorityResponse)
def get_daily_priority(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch today's priority if set."""
    today = datetime.now(timezone.utc).date()
    p = db.query(DailyPriority).filter(
        DailyPriority.user_id == current_user.id,
        DailyPriority.date == today,
    ).first()
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No priority set for today.")
    return p


# ------------------------------------------------------------------
# ADMIN — TRIGGER WEEKLY EMAILS (now protected with a secret header)
# ------------------------------------------------------------------

@router.post("/trigger-weekly-emails")
def trigger_emails_manually(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Manually trigger weekly report emails.
    Protected by a shared secret header (X-Internal-Secret) to prevent
    unauthenticated mass email triggers.
    """
    import os
    internal_secret = os.getenv("INTERNAL_SECRET", "")
    provided = request.headers.get("X-Internal-Secret", "")

    if not internal_secret or provided != internal_secret:
        raise HTTPException(status_code=403, detail="Unauthorized.")

    return send_all_weekly_reports(db)


# ------------------------------------------------------------------
# ADMIN — CONTENT MANAGEMENT
# ------------------------------------------------------------------

@router.post("/admin/content")
def add_admin_content(
    item: ContentItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add content to the AI knowledge base. Requires admin role."""
    # PRODUCTION FIX: is_admin column now exists on User model
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")

    new_content = ContentItem(
        category=item.category,
        content_type=item.content_type,
        text=item.text,
        author=item.author,
    )
    db.add(new_content)
    db.commit()
    return {"message": f"Content added to knowledge base."}


@router.get("/admin/content")
def list_admin_content(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all content items. Admin only."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")

    items = db.query(ContentItem).order_by(ContentItem.category).all()
    return [
        {
            "id": i.id,
            "category": i.category,
            "content_type": i.content_type,
            "text": i.text,
            "author": i.author,
        }
        for i in items
    ]


@router.delete("/admin/content/{content_id}")
def delete_admin_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a content item. Admin only."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")

    item = db.query(ContentItem).filter(ContentItem.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found.")

    db.delete(item)
    db.commit()
    return {"message": "Content deleted."}


# ------------------------------------------------------------------
# WEEKLY INSIGHT  (Fix 7 — called by frontend, no direct backend import)
# Returns one actionable AI-generated or rule-based insight sentence.
# ------------------------------------------------------------------

@router.get("/weekly-insight")
def get_weekly_insight(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate and return a single actionable behavioral insight for the current week.
    Used by the Execution Dashboard to show coaching recommendations.
    Falls back to a rule-based insight when Gemini is unavailable.
    """
    analytics = get_weekly_analytics(db, current_user.id)
    insight   = generate_weekly_behavioral_insight(analytics)
    return {"insight": insight}
