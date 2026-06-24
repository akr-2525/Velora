"""
Velora — Execution Intelligence Platform
FastAPI application entry point.
"""

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel

# Database
from backend.db.database import engine, SessionLocal
from backend.models.user_model import Base, User, DigestSentLog, UserSession
from backend.models.commitment_model import Commitment

# Services
from backend.services.ai_coach_service import PersonalizedDigestEngine
from backend.services.email_service import send_email
from backend.services.scheduler_service import send_all_weekly_reports
from backend.services.auth_service import (
    get_password_hash, verify_password, create_access_token
)
from backend.services.commitment_service import auto_finalize_expired_commitments

# Dependencies
from backend.dependencies import get_db, get_current_user

# Routers
from backend.routers import (
    user_router, streak_router, telemetry_router,
    analytics_router, commitment_router,
)

# Create all tables on startup (use Alembic for schema migrations in production)
try:
    Base.metadata.create_all(bind=engine)
    print("[Velora] Database tables verified/created.")
except Exception as e:
    print(f"[Velora] DB init warning: {e}")


# =========================================================
# BACKEND_URL for use in templates
# =========================================================
BACKEND_URL  = os.getenv("BACKEND_URL",  "http://127.0.0.1:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")


def _make_unsub_token(email: str) -> str:
    """Generate a 7-day JWT used as the one-click unsubscribe token in emails."""
    from datetime import timedelta
    return create_access_token(data={"sub": email}, expires_delta=timedelta(days=7))


# =========================================================
# SCHEDULER JOBS
# =========================================================

def _already_sent_today(db: Session, user_id: int) -> bool:
    """Guard: prevent duplicate daily digests."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    return db.query(DigestSentLog).filter(
        DigestSentLog.user_id == user_id,
        DigestSentLog.sent_date == today,
    ).first() is not None


def run_daily_digest():
    """
    Personalized AI morning digest — fires once per day per user.
    Deduplication guard prevents re-sending on scheduler restarts.
    """
    from datetime import datetime, timezone
    print("[Velora] Starting daily AI digest pipeline...")
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_subscribed == True).all()
        sent = 0
        skipped = 0

        for user in users:
            if _already_sent_today(db, user.id):
                skipped += 1
                continue

            try:
                engine_instance = PersonalizedDigestEngine(db, user)
                ai_advice = engine_instance.generate_digest()

                if isinstance(ai_advice, str):
                    try:
                        ai_advice = json.loads(ai_advice)
                    except Exception:
                        ai_advice = engine_instance._fallback_digest()

                html_content = _build_digest_html(ai_advice, user)
                subject = ai_advice.get("subject", "Your Morning Brief — Velora")

                send_email(user.email, subject, html_content)

                # Record so we never double-send
                db.add(DigestSentLog(
                    user_id=user.id,
                    sent_date=datetime.now(timezone.utc).date(),
                ))
                db.commit()
                sent += 1
                print(f"[Velora] Digest sent to {user.email}")

            except Exception as e:
                print(f"[Velora] Digest failed for {user.email}: {e}")

        print(f"[Velora] Daily digest complete — sent: {sent}, skipped (already sent): {skipped}")

    except Exception as e:
        print(f"[Velora] Scheduler error: {e}")
    finally:
        db.close()


def _build_digest_html(ai_advice: dict, user) -> str:
    """Build the branded daily digest HTML email — light theme, matches weekly email."""
    first_name = user.name.split()[0]

    checkin_base    = f"{BACKEND_URL}/analytics/email-checkin?user_id={user.id}"
    habit_url       = f"{BACKEND_URL}/streaks/email-complete?user_id={user.id}"
    plan_url        = f"{FRONTEND_URL}/?tab=Daily+Protocol"
    unsubscribe_url = f"{BACKEND_URL}/users/unsubscribe?token={_make_unsub_token(user.email)}"

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>Your Morning Brief — Velora</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f8;
             font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

<table width="100%" border="0" cellpadding="0" cellspacing="0"
       style="background:#f4f4f8;padding:32px 0;">
  <tr><td align="center" style="padding:0 16px;">

  <table width="100%" border="0" cellpadding="0" cellspacing="0"
         style="max-width:560px;background:#ffffff;border-radius:14px;
                overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.07);">

    <!-- HEADER -->
    <tr>
      <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
                  padding:28px 36px 24px;">
        <p style="margin:0 0 6px;color:#a78bfa;font-size:11px;font-weight:700;
                   letter-spacing:2.5px;text-transform:uppercase;
                   font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">Velora</p>
        <p style="margin:0;color:#e5e7eb;font-size:13px;
                   font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
            Your Morning Brief
        </p>
      </td>
    </tr>

    <!-- BODY -->
    <tr>
      <td style="padding:32px 36px;background:#ffffff;
                  font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

        <!-- Greeting -->
        <p style="color:#1a1a2e;font-size:21px;font-weight:700;
                    margin:0 0 20px;line-height:1.4;
                    font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
          {ai_advice.get('greeting', f'Good morning, {first_name}.')}
        </p>

        <!-- Pillar 1: What happened -->
        <p style="font-size:15px;color:#374151;line-height:1.9;margin:0 0 18px;">
          {ai_advice.get('what_happened', '')}
        </p>

        <!-- Pillar 2+3: Pattern + Meaning -->
        <p style="font-size:15px;color:#374151;line-height:1.9;margin:0 0 22px;">
          {ai_advice.get('pattern_and_meaning', '')}
        </p>

        <!-- Pillar 4: Recommendation -->
        <div style="border-left:4px solid #7c3aed;padding:14px 18px;
                    background:#f5f3ff;border-radius:0 8px 8px 0;margin-bottom:22px;">
          <p style="margin:0 0 6px;color:#7c3aed;font-size:10px;font-weight:700;
                     letter-spacing:1.5px;text-transform:uppercase;">One Thing For Today</p>
          <p style="margin:0;color:#1a1a2e;font-size:15px;line-height:1.7;">
            {ai_advice.get('recommendation', 'Pick the smallest possible first step and start there.')}
          </p>
        </div>

        <!-- Pillar 5: Encouragement -->
        <p style="font-size:15px;color:#374151;line-height:1.9;margin:0 0 24px;">
          {ai_advice.get('encouragement', '')}
        </p>

        <!-- Quote -->
        <div style="border-top:1px solid #f3f4f6;padding-top:20px;text-align:center;">
          <p style="font-style:italic;color:#6b7280;font-size:14px;
                     line-height:1.7;margin:0 0 6px;">
            &ldquo;{ai_advice.get('quote', 'The first step does not have to be impressive. It just has to happen.')}&rdquo;
          </p>
          <p style="margin:0;color:#9ca3af;font-size:12px;font-weight:600;">
            &mdash; {ai_advice.get('author', 'Velora')}
          </p>
        </div>

      </td>
    </tr>

    <!-- HABIT BUTTON -->
    <tr>
      <td style="padding:20px 36px 0;text-align:center;background:#ffffff;
                  font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
        <a href="{habit_url}"
           style="display:inline-block;background:#059669;color:#ffffff;
                  text-decoration:none;font-size:15px;font-weight:700;
                  padding:14px 28px;border-radius:50px;">
          ✅ I completed my core habit
        </a>
        <p style="margin:8px 0 0;font-size:11px;color:#9ca3af;">
          Tap to log your habit and keep your streak alive
        </p>
      </td>
    </tr>

    <!-- PLAN BUTTON -->
    <tr>
      <td style="padding:12px 36px 0;text-align:center;background:#ffffff;
                  font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
        <a href="{plan_url}"
           style="display:inline-block;background:#f5f3ff;color:#7c3aed;
                  text-decoration:none;font-size:14px;font-weight:600;
                  padding:12px 28px;border-radius:50px;border:1px solid #ddd6fe;">
          📋 Plan Today's Execution Blocks
        </a>
        <p style="margin:6px 0 0;font-size:11px;color:#9ca3af;">
          Open Velora and lock in your focus windows for today
        </p>
      </td>
    </tr>

    <!-- ENERGY CHECK-IN -->
    <tr>
      <td style="background:#f9fafb;padding:22px 36px;
                  border-top:1px solid #f3f4f6;margin-top:20px;
                  font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                  text-align:center;">
        <p style="margin:0 0 12px;color:#6b7280;font-size:11px;font-weight:700;
                   letter-spacing:1.5px;text-transform:uppercase;">
          How's your energy today?
        </p>
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
          <tr>
            <td align="center">
              <a href="{checkin_base}&energy=3&focus=3"
                 style="text-decoration:none;display:inline-block;
                        padding:12px 20px;background:#f3f4f6;
                        border:1px solid #e5e7eb;border-radius:50px;
                        font-size:20px;margin:0 6px;">😴</a>
              <a href="{checkin_base}&energy=6&focus=6"
                 style="text-decoration:none;display:inline-block;
                        padding:12px 20px;background:#f3f4f6;
                        border:1px solid #e5e7eb;border-radius:50px;
                        font-size:20px;margin:0 6px;">😐</a>
              <a href="{checkin_base}&energy=9&focus=9"
                 style="text-decoration:none;display:inline-block;
                        padding:12px 20px;background:#f3f4f6;
                        border:1px solid #e5e7eb;border-radius:50px;
                        font-size:20px;margin:0 6px;">⚡</a>
            </td>
          </tr>
        </table>
        <p style="margin:10px 0 0;font-size:12px;color:#9ca3af;">
          Tap once — it only takes a second
        </p>
      </td>
    </tr>

    <!-- FOOTER -->
    <tr>
      <td style="padding:16px 36px;background:#f9fafb;
                  border-top:1px solid #f3f4f6;text-align:center;
                  font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
        <p style="margin:0 0 4px;font-size:11px;color:#9ca3af;">
          Velora · Execution Intelligence Platform
        </p>
        <p style="margin:0;font-size:11px;">
          <a href="{unsubscribe_url}"
             style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
        </p>
      </td>
    </tr>

  </table>
  </td></tr>
</table>
</body>
</html>"""


def run_weekly_analytics():
    print("[Velora] Starting weekly analytics email pipeline...")
    db = SessionLocal()
    try:
        result = send_all_weekly_reports(db)
        print(f"[Velora] Weekly report result: {result}")
    except Exception as e:
        print(f"[Velora] Weekly scheduler error: {e}")
    finally:
        db.close()


def run_commitment_cleanup_job():
    print("[Velora] Running commitment auto-finalize job...")
    db = SessionLocal()
    try:
        auto_finalize_expired_commitments(db)
    except Exception as e:
        print(f"[Velora] Cleanup job error: {e}")
    finally:
        db.close()


# =========================================================
# LIFESPAN — scheduler setup
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Velora] Starting scheduler...")
    scheduler = BackgroundScheduler(timezone="UTC")

    # Daily digest — 7:00 AM IST = 01:30 UTC
    digest_hour   = int(os.getenv("DIGEST_HOUR_UTC",   "1"))
    digest_minute = int(os.getenv("DIGEST_MINUTE_UTC", "30"))
    scheduler.add_job(
        run_daily_digest,
        CronTrigger(hour=digest_hour, minute=digest_minute),
        id="daily_digest",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    # Weekly report — Sunday 6:00 PM IST = Sunday 12:30 UTC
    scheduler.add_job(
        run_weekly_analytics,
        CronTrigger(day_of_week="sun", hour=12, minute=30),
        id="weekly_analytics",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    # Commitment cleanup — every 30 minutes
    scheduler.add_job(
        run_commitment_cleanup_job,
        "interval",
        minutes=30,
        id="commitment_cleanup",
        replace_existing=True,
        misfire_grace_time=1800,
    )

    scheduler.start()

    # ── Startup catch-up: if server was sleeping at send time, send now ──────
    # Check if today's digest window has passed but email wasn't sent yet.
    # This fires immediately on cold start after the cron job wakes the server.
    import threading as _threading
    def _startup_catchup():
        import time as _time
        _time.sleep(5)  # wait for app to fully initialize
        now_utc = datetime.now(timezone.utc)
        scheduled_today = now_utc.replace(
            hour=digest_hour, minute=digest_minute, second=0, microsecond=0
        )
        # Fire if: scheduled time has passed today AND it's within 3 hours of it
        minutes_since = (now_utc - scheduled_today).total_seconds() / 60
        if 0 < minutes_since < 180:
            print(f"[Velora] Startup catch-up: digest window passed {int(minutes_since)} min ago — sending now")
            run_daily_digest()
        else:
            print(f"[Velora] Startup catch-up: no catch-up needed (minutes_since={int(minutes_since)})")

    _threading.Thread(target=_startup_catchup, daemon=True).start()

    yield
    print("[Velora] Shutting down scheduler...")
    scheduler.shutdown()


# =========================================================
# APP SETUP
# =========================================================

app = FastAPI(
    title="Velora API",
    description="Execution Intelligence Platform — Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — restricted to the deployed frontend URL in production
_allowed_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(user_router.router)
app.include_router(streak_router.router)
app.include_router(telemetry_router.router)
app.include_router(analytics_router.router)
app.include_router(commitment_router.router)


# =========================================================
# AUTH ENDPOINTS
# =========================================================

class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/login", tags=["Auth"])
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    access_token = create_access_token(data={"sub": user.email})

    # Create a short opaque session key — this goes in the URL, not the JWT
    import secrets as _secrets
    from datetime import timedelta as _td
    session_key = _secrets.token_urlsafe(16)  # 22-char URL-safe random string
    expires = datetime.now(timezone.utc) + _td(days=30)
    db.add(UserSession(
        user_id=user.id,
        session_key=session_key,
        jwt_token=access_token,
        expires_at=expires,
    ))
    # Clean up old sessions for this user (keep last 5 only)
    old_sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id)
        .order_by(UserSession.created_at.desc())
        .offset(5)
        .all()
    )
    for s in old_sessions:
        db.delete(s)
    db.commit()

    return {
        "access_token": access_token,
        "session_key":  session_key,   # short opaque key — safe to put in URL
        "token_type": "bearer",
        "user": {
            "id":           user.id,
            "name":         user.name,
            "email":        user.email,
            "focus_areas":  user.focus_areas,
            "primary_goal": user.primary_goal,
            "is_admin":     user.is_admin,
            "timezone":     user.timezone,
        },
    }


@app.get("/session/{session_key}", tags=["Auth"])
def resolve_session(session_key: str, db: Session = Depends(get_db)):
    """
    Resolve a short session key back to a JWT and user profile.
    Called on every page refresh — replaces cookie/localStorage approach.
    """
    from datetime import datetime, timezone
    sess = db.query(UserSession).filter(
        UserSession.session_key == session_key
    ).first()

    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    if sess.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db.delete(sess)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired.")

    user = db.query(User).filter(User.id == sess.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return {
        "access_token": sess.jwt_token,
        "session_key":  session_key,
        "token_type": "bearer",
        "user": {
            "id":           user.id,
            "name":         user.name,
            "email":        user.email,
            "focus_areas":  user.focus_areas,
            "primary_goal": user.primary_goal,
            "is_admin":     user.is_admin,
            "timezone":     user.timezone,
        },
    }


@app.delete("/session/{session_key}", tags=["Auth"])
def delete_session(session_key: str, db: Session = Depends(get_db)):
    """Sign out — delete the session from DB so the key becomes invalid."""
    sess = db.query(UserSession).filter(
        UserSession.session_key == session_key
    ).first()
    if sess:
        db.delete(sess)
        db.commit()
    return {"message": "Signed out."}


# =========================================================
# REGISTRATION
# =========================================================

from backend.schemas.user_schema import UserCreate, UserResponse


@app.post("/users/", response_model=UserResponse, tags=["Auth"])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    new_user = User(
        name=user.name,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        primary_goal=user.primary_goal,
        focus_areas=user.focus_areas,
        struggles=user.struggles,
        habits=user.habits,
        preferred_tone=user.preferred_tone,
        daily_time_minutes=user.daily_time_minutes,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# =========================================================
# ACCOUNT DELETION
# =========================================================

@app.delete("/users/me", tags=["Auth"])
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted."}


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "operational",
        "product": "Velora",
        "version": "1.0.0",
    }


@app.get("/ping", tags=["Health"])
def ping():
    """Lightweight keep-alive endpoint for cron jobs."""
    return {"ok": True}


# =========================================================
# MANUAL DIGEST TRIGGER (dev/admin testbed)
# =========================================================

@app.get("/generate-digest", tags=["Dev"])
def get_daily_digest_testbed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger and preview the AI digest for the authenticated user."""
    try:
        engine_instance = PersonalizedDigestEngine(db, current_user)
        digest = engine_instance.generate_digest()
        if not digest:
            raise HTTPException(status_code=500, detail="Digest generation returned empty.")
        return digest
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Engine error: {str(err)}")


@app.post("/send-test-email", tags=["Dev"])
def send_test_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send the actual daily email to the current user RIGHT NOW.
    Use this to test email delivery without waiting for the scheduler.
    """
    try:
        engine_instance = PersonalizedDigestEngine(db, current_user)
        ai_advice = engine_instance.generate_digest()
        if isinstance(ai_advice, str):
            import json as _json
            ai_advice = _json.loads(ai_advice)
        html_content = _build_digest_html(ai_advice, current_user)
        subject = ai_advice.get("subject", "Your Morning Brief — Velora")
        send_email(current_user.email, subject, html_content)
        return {"message": f"Test email sent to {current_user.email}", "subject": subject}
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Email error: {str(err)}")


@app.get("/preview-digest-html", tags=["Dev"])
def preview_digest_html(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the exact HTML that will be sent in the daily email.
    Used by the Email Preview tab — single source of truth.
    """
    from fastapi.responses import HTMLResponse
    try:
        engine_instance = PersonalizedDigestEngine(db, current_user)
        digest = engine_instance.generate_digest()
        if not digest:
            raise HTTPException(status_code=500, detail="Digest generation returned empty.")
        html = _build_digest_html(digest, current_user)
        return HTMLResponse(content=html)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Engine error: {str(err)}")


@app.get("/preview-weekly-html", tags=["Dev"])
def preview_weekly_html(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the exact HTML that will be sent in the weekly Sunday email.
    Used by the Email Preview tab — single source of truth.
    """
    from fastapi.responses import HTMLResponse
    from backend.services.analytics_service import get_weekly_analytics
    from backend.services.commitment_service import compute_dashboard_stats
    from backend.services.auth_service import create_access_token
    from backend.services.email_template_service import generate_weekly_analytics_html
    from backend.services.scheduler_service import _get_latest_reflection
    from datetime import timedelta
    try:
        analytics  = get_weekly_analytics(db, current_user.id)
        reflection = _get_latest_reflection(db, current_user.id)
        token = create_access_token(
            data={"sub": current_user.email},
            expires_delta=timedelta(days=7),
        )
        try:
            dash_stats = compute_dashboard_stats(db, current_user.id)
            cw = dash_stats.current_week.model_dump()
        except Exception:
            cw = None
        html = generate_weekly_analytics_html(
            user_name        = current_user.name,
            analytics        = analytics,
            user_token       = token,
            commitment_stats = cw,
            reflection       = reflection,
            user_goal        = current_user.primary_goal or "",
        )
        return HTMLResponse(content=html)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Engine error: {str(err)}")
