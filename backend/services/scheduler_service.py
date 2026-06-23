"""
Velora scheduler service.
Handles weekly report emails and related batch operations.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.models.user_model import User, WeeklyReflection
from backend.services.analytics_service import get_weekly_analytics
from backend.services.email_template_service import generate_weekly_analytics_html
from backend.services.email_service import send_email
from backend.services.auth_service import create_access_token
from backend.services.commitment_service import compute_dashboard_stats


def _get_latest_reflection(db: Session, user_id: int) -> dict:
    """Fetch the most recent weekly reflection (within last 14 days)."""
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=14)
    ref = (
        db.query(WeeklyReflection)
        .filter(
            WeeklyReflection.user_id == user_id,
            WeeklyReflection.week_ending_date >= cutoff,
        )
        .order_by(WeeklyReflection.created_at.desc())
        .first()
    )
    if not ref:
        return {}
    return {
        "what_went_well":      ref.what_went_well      or "",
        "biggest_distraction": ref.biggest_distraction or "",
        "proud_moment":        ref.proud_moment         or "",
    }


def send_all_weekly_reports(db: Session) -> dict:
    """
    Send the weekly analytics + AI summary email to every subscribed user.
    """
    users = db.query(User).filter(User.is_subscribed == True).all()

    if not users:
        return {"status": "success", "emails_sent": 0, "message": "No subscribed users found."}

    emails_sent = 0
    errors      = []

    for user in users:
        try:
            analytics  = get_weekly_analytics(db, user.id)
            reflection = _get_latest_reflection(db, user.id)

            access_token = create_access_token(
                data={"sub": user.email},
                expires_delta=timedelta(days=7),
            )

            try:
                dash_stats          = compute_dashboard_stats(db, user.id)
                current_week_stats  = dash_stats.current_week.model_dump()
            except Exception:
                current_week_stats = None

            html_body = generate_weekly_analytics_html(
                user_name        = user.name,
                analytics        = analytics,
                user_token       = access_token,
                commitment_stats = current_week_stats,
                reflection       = reflection,
                user_goal        = user.primary_goal or "",
            )

            send_email(
                to_email     = user.email,
                subject      = f"Your week in review, {user.name.split()[0]} 📈",
                html_content = html_body,
            )

            print(f"[Velora] Weekly report sent to {user.email}")
            emails_sent += 1

        except Exception as e:
            msg = f"Failed for {user.email}: {e}"
            print(f"[Velora] ❌ {msg}")
            errors.append(msg)

    return {"status": "success", "emails_sent": emails_sent, "errors": errors}
