from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.user_model import User
from backend.schemas.user_schema import (
    UserResponse,
    UserUpdate,
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from backend.dependencies import get_current_user, get_db
from backend.models.user_model import Goal
from backend.services.auth_service import generate_reset_token, get_password_hash
from backend.services.email_service import send_email
from backend.services.email_template_service import generate_password_reset_html
from typing import List
from datetime import datetime, timezone, timedelta
import os

router = APIRouter(prefix="/users", tags=["Users"])

BACKEND_URL  = os.getenv("BACKEND_URL",  "http://127.0.0.1:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")


# ------------------------------------------------------------------
# PROFILE
# ------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Fetch the current user's profile, streaks, and settings."""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile — name, goal, focus areas, habits, tone, time budget."""
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user


# ------------------------------------------------------------------
# GOALS
# ------------------------------------------------------------------

@router.post("/goals", response_model=GoalResponse)
def create_goal(
    schema: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new long-term goal that commitments can be linked to."""
    goal = Goal(
        user_id=current_user.id,
        title=schema.title,
        description=schema.description,
        target_date=schema.target_date,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/goals", response_model=List[GoalResponse])
def list_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all goals for the current user."""
    return (
        db.query(Goal)
        .filter(Goal.user_id == current_user.id)
        .order_by(Goal.created_at.desc())
        .all()
    )


@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    schema: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a goal's details or mark it completed/archived."""
    goal = db.query(Goal).filter(
        Goal.id == goal_id, Goal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    update_data = schema.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}")
def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a goal (commitments linked to it will have goal unlinked)."""
    goal = db.query(Goal).filter(
        Goal.id == goal_id, Goal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")
    db.delete(goal)
    db.commit()
    return {"message": "Goal deleted."}


# ------------------------------------------------------------------
# PASSWORD RESET
# ------------------------------------------------------------------

@router.post("/forgot-password")
def forgot_password(
    req: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset email.
    Always returns 200 regardless of whether the email exists
    (prevents user enumeration).
    """
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        token = generate_reset_token()
        user.reset_token = token
        user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.commit()

        reset_link = f"{FRONTEND_URL}/?action=reset-password&token={token}"
        html = generate_password_reset_html(user.name, reset_link)
        try:
            send_email(user.email, "Reset your Velora password", html)
        except Exception as e:
            print(f"[Velora] Password reset email failed: {e}")

    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(
    req: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """Confirm password reset with the token from the email link."""
    user = db.query(User).filter(User.reset_token == req.token).first()

    if not user or not user.reset_token_expiry:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    if datetime.now(timezone.utc) > user.reset_token_expiry.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired.")

    user.hashed_password = get_password_hash(req.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.commit()

    return {"message": "Password updated successfully. You can now log in."}


# ------------------------------------------------------------------
# UNSUBSCRIBE (email link target)
# ------------------------------------------------------------------

@router.get("/unsubscribe")
def unsubscribe(
    token: str,
    db: Session = Depends(get_db),
):
    """
    One-click unsubscribe from all Velora emails.
    Accepts the same JWT used in weekly emails so no separate login is needed.
    """
    import jwt as pyjwt
    from backend.services.auth_service import SECRET_KEY, ALGORITHM

    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired unsubscribe link.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_subscribed = False
    db.commit()

    return {"message": "You have been unsubscribed from all Velora emails."}
