from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.db.database import Base


# ==========================================
# 1. CORE USER TABLE
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    primary_goal = Column(String, nullable=True)
    focus_areas = Column(ARRAY(String), default=[])
    struggles = Column(ARRAY(String), default=[])
    habits = Column(ARRAY(String), default=[])

    preferred_tone = Column(String, default="motivating")
    daily_time_minutes = Column(Integer, default=30)

    # Timezone for correct local time display (e.g. "Asia/Kolkata", "America/New_York")
    timezone = Column(String, default="UTC", nullable=False)

    is_admin = Column(Boolean, default=False, nullable=False)
    is_subscribed = Column(Boolean, default=True, nullable=False)
    reset_token = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)

    # Relationships
    streak = relationship(
        "UserStreak", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    habit_logs = relationship(
        "HabitLog", back_populates="user", cascade="all, delete-orphan"
    )
    checkins = relationship(
        "DailyCheckIn", back_populates="user", cascade="all, delete-orphan"
    )
    email_events = relationship(
        "EmailEvent", back_populates="user", cascade="all, delete-orphan"
    )
    goals = relationship(
        "Goal", back_populates="user", cascade="all, delete-orphan"
    )
    digest_logs = relationship(
        "DigestSentLog", back_populates="user", cascade="all, delete-orphan"
    )


# ==========================================
# 2. STREAK TRACKING
# ==========================================
class UserStreak(Base):
    __tablename__ = "user_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_completed_date = Column(Date, nullable=True)

    # Execution streak — days with at least one completed planned commitment
    execution_streak = Column(Integer, default=0)
    longest_execution_streak = Column(Integer, default=0)
    last_execution_date = Column(Date, nullable=True)

    # MODULE 7: Streak freeze system
    # One freeze earned per 14 consecutive days; max 3 stored; auto-consumed on miss
    freeze_count = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="streak")


# ==========================================
# 3. HABIT LOGS
# ==========================================
class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    habit_name = Column(String, nullable=False)
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="habit_logs")


# ==========================================
# 4. DAILY CHECK-INS
# Primary write path: one-click email buttons (GET /analytics/email-checkin)
# Secondary: dashboard Daily Note form and /checkins/ override
# ==========================================
class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    date = Column(Date, default=lambda: datetime.now(timezone.utc).date())

    mood_score = Column(Integer, nullable=False)
    energy_score = Column(Integer, nullable=False)
    productivity_score = Column(Integer, nullable=False)

    notes = Column(String, nullable=True)

    user = relationship("User", back_populates="checkins")


# ==========================================
# 5. EMAIL ENGAGEMENT EVENTS
# ==========================================
class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    event_type = Column(String, nullable=False)  # "clicked", "habit_complete"
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="email_events")


# ==========================================
# 6. WEEKLY REFLECTIONS
# ==========================================
class WeeklyReflection(Base):
    __tablename__ = "weekly_reflections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    week_ending_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())

    what_went_well = Column(String, nullable=False)
    biggest_distraction = Column(String, nullable=False)
    proud_moment = Column(String, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


# ==========================================
# 7. CONTENT LIBRARY
# ==========================================
class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True, nullable=False)
    content_type = Column(String, nullable=False)  # Tip, Quote, Micro-Habit
    text = Column(String, nullable=False)
    author = Column(String, nullable=True)


# ==========================================
# 8. GOALS
# ==========================================
class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    target_date = Column(Date, nullable=True)
    status = Column(String, default="active", nullable=False)  # active, completed, archived

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="goals")


# ==========================================
# 9. DIGEST SENT LOG (prevents duplicate emails)
# ==========================================
class DigestSentLog(Base):
    __tablename__ = "digest_sent_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sent_date = Column(Date, nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="digest_logs")


# ==========================================
# 10. DAILY PRIORITY  ("What would make today successful?")
# ==========================================
class DailyPriority(Base):
    __tablename__ = "daily_priorities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    priority_text = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
