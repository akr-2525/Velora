"""
Velora AI Coach — PersonalizedDigestEngine
Generates deeply personalized daily morning emails using Gemini 2.5 Flash.
"""

import json
import random
import os
from google import genai as _genai
from google.genai import types as _genai_types
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.user_model import (
    User,
    DailyCheckIn,
    HabitLog,
    UserStreak,
    WeeklyReflection,
    ContentItem,
    EmailEvent,
    Goal,
    DailyPriority,
)
from backend.models.commitment_model import Commitment

load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    print("[Velora] WARNING: GEMINI_API_KEY not set — AI features will use fallback responses.")
    _client = None
else:
    _client = _genai.Client(api_key=_api_key)
_MODEL  = "gemini-2.5-flash-lite"


def _generate(prompt: str) -> str:
    """Single helper — call Gemini with retry on 503."""
    if not _client:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    import time as _time
    last_error = None
    for attempt in range(3):  # try up to 3 times
        try:
            response = _client.models.generate_content(
                model=_MODEL,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            last_error = e
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str:
                wait = (attempt + 1) * 8  # 8s, 16s, 24s
                print(f"[Velora AI] Gemini 503 on attempt {attempt+1}, retrying in {wait}s...")
                _time.sleep(wait)
            else:
                raise  # non-503 error — don't retry
    raise last_error

# =========================================================
# WRITING STYLES
# =========================================================

WRITING_STYLES = [
    "soft and comforting",
    "warm and gently hopeful",
    "quietly encouraging",
    "emotionally intelligent and observant",
    "slightly poetic and cozy",
    "cute and calming",
    "deeply supportive but grounded",
    "gentle and reflective",
]

# =========================================================
# BEHAVIORAL ANALYZER
# =========================================================


class BehavioralAnalyzer:

    @staticmethod
    def analyze(
        avg_energy: float,
        avg_focus: float,
        avg_mood: float,
        current_streak: int,
        longest_streak: int,
        neglected_count: int,
    ) -> Dict[str, str]:

        state = "steady_growth"
        emotional_state = "balanced"

        if avg_energy <= 3.5:
            state = "burnout_risk"
            emotional_state = "mentally tired"
        elif avg_focus <= 4:
            state = "distracted"
            emotional_state = "scattered"
        elif current_streak == 0 and longest_streak >= 5:
            state = "rebuilding"
            emotional_state = "trying to regain rhythm"
        elif current_streak >= 7 and avg_energy >= 7:
            state = "high_momentum"
            emotional_state = "locked in"
        elif neglected_count >= 2:
            state = "inconsistency"
            emotional_state = "slightly disconnected"

        mood_style = "neutral"
        if avg_mood <= 4:
            mood_style = "extra_gentle"
        elif avg_mood >= 7:
            mood_style = "uplifting"

        return {
            "state": state,
            "emotional_state": emotional_state,
            "mood_style": mood_style,
        }


# =========================================================
# MEMORY ENGINE
# =========================================================


class MemoryEngine:

    @staticmethod
    def get_daily_note(db: Session, user_id: int) -> Optional[str]:
        """Pull today's or yesterday's daily note — user's own words about their day."""
        from backend.models.user_model import DailyCheckIn
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        for target_date in [yesterday, today]:
            ci = (
                db.query(DailyCheckIn)
                .filter(
                    DailyCheckIn.user_id == user_id,
                    DailyCheckIn.date == target_date,
                    DailyCheckIn.notes.isnot(None),
                )
                .first()
            )
            if ci and ci.notes and len(ci.notes.strip()) > 5:
                return ci.notes.strip()
        return None

    @staticmethod
    def get_recent_outcome_notes(db: Session, user_id: int) -> List[str]:
        """Pull outcome notes from commitments in the last 3 days — user's own words."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=3)
        commits = (
            db.query(Commitment)
            .filter(
                Commitment.user_id == user_id,
                Commitment.outcome_note.isnot(None),
                Commitment.created_at >= cutoff,
            )
            .order_by(desc(Commitment.created_at))
            .limit(3)
            .all()
        )
        return [c.outcome_note for c in commits if c.outcome_note and len(c.outcome_note.strip()) > 3]

    @staticmethod
    def get_recent_reflection(
        db: Session, user_id: int
    ) -> Optional[WeeklyReflection]:
        one_week_ago = datetime.now(timezone.utc).date() - timedelta(days=7)
        return (
            db.query(WeeklyReflection)
            .filter(
                WeeklyReflection.user_id == user_id,
                WeeklyReflection.week_ending_date >= one_week_ago,
            )
            .order_by(desc(WeeklyReflection.created_at))
            .first()
        )

    @staticmethod
    def get_neglected_habits(
        db: Session, user: User, days: int = 4
    ) -> List[str]:
        if not user.habits:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        logs = (
            db.query(HabitLog)
            .filter(
                HabitLog.user_id == user.id,
                HabitLog.completed_at >= cutoff,
            )
            .all()
        )

        completed = {log.habit_name for log in logs}
        return [h for h in user.habits if h not in completed]

    @staticmethod
    def get_yesterday_commitment_summary(
        db: Session, user_id: int
    ) -> Dict[str, Any]:
        """
        Summarise yesterday's commitment execution so the email can
        feel like a morning briefing, not a generic motivational note.
        """
        now = datetime.now(timezone.utc)
        yesterday_start = (now - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0)

        yesterday_commits = (
            db.query(Commitment)
            .filter(
                Commitment.user_id == user_id,
                Commitment.start_time >= yesterday_start,
                Commitment.start_time < yesterday_end,
            )
            .all()
        )

        total = len(yesterday_commits)
        completed = sum(1 for c in yesterday_commits if c.status == "completed")
        missed = sum(1 for c in yesterday_commits if c.status == "missed")

        return {
            "total": total,
            "completed": completed,
            "missed": missed,
            "had_data": total > 0,
        }

    @staticmethod
    def get_todays_commitments(
        db: Session, user_id: int
    ) -> List[str]:
        """Return 'Title (HH:MM AM/PM)' strings for today's planned commitments (up to 4)."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        today_commits = (
            db.query(Commitment)
            .filter(
                Commitment.user_id == user_id,
                Commitment.start_time >= today_start,
                Commitment.start_time < today_end,
                Commitment.status.in_(["pending", "active"]),
            )
            .order_by(Commitment.start_time)
            .limit(4)
            .all()
        )

        result = []
        for c in today_commits:
            # start_time is stored as naive local time — format directly
            try:
                time_str = c.start_time.strftime("%I:%M %p")
            except Exception:
                time_str = "scheduled"
            result.append(f"{c.title} at {time_str}")
        return result

    @staticmethod
    def get_retroactive_summary(db: Session, user_id: int) -> str:
        """
        Module 15: Summarise yesterday's retroactive logs so the AI
        can distinguish productive-but-unplanned work from planned execution.
        """
        now = datetime.now(timezone.utc)
        yesterday_start = (now - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0)

        retro = (
            db.query(Commitment)
            .filter(
                Commitment.user_id == user_id,
                Commitment.commitment_type == "retroactive",
                Commitment.start_time >= yesterday_start,
                Commitment.start_time < yesterday_end,
            )
            .all()
        )

        if not retro:
            return "no retroactive work logged yesterday"

        total_mins = sum(
            int((
                (c.end_time.replace(tzinfo=timezone.utc) if c.end_time.tzinfo is None else c.end_time) -
                (c.start_time.replace(tzinfo=timezone.utc) if c.start_time.tzinfo is None else c.start_time)
            ).total_seconds() / 60)
            for c in retro
        )
        titles = [c.title for c in retro[:3]]
        suffix = f" (+{len(retro) - 3} more)" if len(retro) > 3 else ""
        return f"{len(retro)} retroactive sessions ({total_mins} min total): {', '.join(titles)}{suffix}"

    # ----------------------------------------------------------------
    # EMAIL AUDIT ADDITIONS — use all available stored behavioral data
    # ----------------------------------------------------------------

    @staticmethod
    def get_active_goals(db: Session, user_id: int) -> List[str]:
        """Return titles of the user's active goals (up to 2)."""
        goals = (
            db.query(Goal)
            .filter(Goal.user_id == user_id, Goal.status == "active")
            .order_by(Goal.created_at.desc())
            .limit(2)
            .all()
        )
        return [g.title for g in goals]

    @staticmethod
    def get_today_priority(db: Session, user_id: int) -> Optional[str]:
        """Return today's stated priority if one was set."""
        today = datetime.now(timezone.utc).date()
        p = (
            db.query(DailyPriority)
            .filter(
                DailyPriority.user_id == user_id,
                DailyPriority.date == today,
            )
            .first()
        )
        return p.priority_text if p else None

    @staticmethod
    def get_mood_trend(db: Session, user_id: int) -> str:
        """
        Compare today's / yesterday's mood to 3 days ago.
        Returns "improving", "declining", or "stable".
        """
        checkins = (
            db.query(DailyCheckIn)
            .filter(
                DailyCheckIn.user_id == user_id,
                DailyCheckIn.date >= (
                    datetime.now(timezone.utc).date() - timedelta(days=4)
                ),
            )
            .order_by(DailyCheckIn.date)
            .all()
        )
        if len(checkins) < 2:
            return "stable"

        older = checkins[0].energy_score
        recent = checkins[-1].energy_score
        if recent - older >= 2:
            return "improving"
        if older - recent >= 2:
            return "declining"
        return "stable"

    @staticmethod
    def get_failure_pattern(db: Session, user_id: int) -> Optional[str]:
        """
        Check if the user has a consistent failure reason in the last 7 days.
        Returns the dominant reason if it appeared 2+ times, else None.
        """
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        missed = (
            db.query(Commitment)
            .filter(
                Commitment.user_id == user_id,
                Commitment.commitment_type == "planned",
                Commitment.status.in_(["missed", "partial"]),
                Commitment.failure_reason.isnot(None),
                Commitment.created_at >= seven_days_ago,
            )
            .all()
        )
        if not missed:
            return None

        counts: Dict[str, int] = {}
        for c in missed:
            counts[c.failure_reason] = counts.get(c.failure_reason, 0) + 1

        dominant = max(counts, key=lambda k: counts[k])
        if counts[dominant] >= 2:
            label_map = {
                "distraction_avoidance": "distraction or avoidance",
                "underestimated_time":   "underestimating how long tasks take",
                "external_blocker":      "external blockers outside their control",
            }
            return label_map.get(dominant, dominant)
        return None

    @staticmethod
    def get_top_focus_area(db: Session, user_id: int) -> Optional[str]:
        """Return the focus area the user spent the most time on this week."""
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        commits = (
            db.query(Commitment)
            .filter(
                Commitment.user_id == user_id,
                Commitment.focus_area.isnot(None),
                Commitment.created_at >= seven_days_ago,
            )
            .all()
        )
        if not commits:
            return None

        allocation: Dict[str, int] = {}
        for c in commits:
            mins = int((
                (c.end_time.replace(tzinfo=timezone.utc) if c.end_time.tzinfo is None else c.end_time) -
                (c.start_time.replace(tzinfo=timezone.utc) if c.start_time.tzinfo is None else c.start_time)
            ).total_seconds() / 60)
            allocation[c.focus_area] = allocation.get(c.focus_area, 0) + mins

        return max(allocation, key=lambda k: allocation[k]) if allocation else None

    @staticmethod
    def get_procrastination_signal(db: Session, user_id: int) -> bool:
        """True if the user has rescheduled 2+ commitments in the last 7 days."""
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        count = (
            db.query(Commitment)
            .filter(
                Commitment.user_id == user_id,
                Commitment.commitment_type == "planned",
                Commitment.procrastination_flag == True,
                Commitment.created_at >= seven_days_ago,
            )
            .count()
        )
        return count >= 2


# =========================================================
# EMAIL ENGAGEMENT ENGINE
# =========================================================


class EngagementEngine:

    @staticmethod
    def analyze_email_behavior(
        db: Session, user_id: int
    ) -> Dict[str, str]:
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        events = (
            db.query(EmailEvent)
            .filter(
                EmailEvent.user_id == user_id,
                EmailEvent.timestamp >= seven_days_ago,
            )
            .all()
        )

        if not events:
            return {"email_length": "standard", "engagement_level": "new_user"}

        clicks = len([e for e in events if e.event_type == "clicked"])
        total = len(events)

        click_rate = clicks / total if total else 0

        engagement_level = "passive"
        if click_rate > 0.4:
            engagement_level = "highly_engaged"
        elif click_rate > 0.15:
            engagement_level = "consistent_reader"

        # Users with many clicks get a richer email; low engagement gets concise
        email_length = "brief" if click_rate < 0.1 and total >= 5 else "standard"

        return {
            "email_length": email_length,
            "engagement_level": engagement_level,
        }


# =========================================================
# CONTENT ENGINE
# =========================================================


class ContentEngine:

    STATE_CONTENT_MAP = {
        "burnout_risk": ["Recovery", "Mindfulness", "Rest", "Self Compassion"],
        "distracted": ["Focus", "Deep Work", "Attention"],
        "rebuilding": ["Restarting", "Small Wins", "Consistency"],
        "high_momentum": ["Growth", "Momentum", "Advanced Learning"],
        "inconsistency": ["Discipline", "Consistency", "Habits"],
        "steady_growth": ["Growth", "Consistency"],
    }

    @classmethod
    def get_contextual_content(
        cls, db: Session, state: str
    ) -> Dict[str, Any]:
        categories = cls.STATE_CONTENT_MAP.get(state, ["Growth"])
        content = []

        for category in categories:
            rows = (
                db.query(ContentItem)
                .filter(ContentItem.category.ilike(f"%{category}%"))
                .all()
            )
            content.extend(rows)

        tips = [c for c in content if c.content_type == "Tip"]
        habits = [c for c in content if c.content_type == "Micro-Habit"]
        quotes = [c for c in content if c.content_type == "Quote"]

        selected_tip = random.choice(tips).text if tips else "Take today slowly and intentionally."
        selected_habit = random.choice(habits).text if habits else "Protect one small routine today."
        selected_quote = random.choice(quotes) if quotes else None

        return {
            "tip": selected_tip,
            "habit": selected_habit,
            "quote": selected_quote.text if selected_quote else None,
            "author": selected_quote.author if selected_quote else "Velora",
        }


# =========================================================
# GREETING ENGINE
# =========================================================


class GreetingEngine:

    MORNING_OPENERS = [
        "The day is still unwritten, and that's a beautiful thing 🌅",
        "A fresh morning has arrived with room for new choices 🌱",
        "Today's progress doesn't need to be perfect to matter ✨",
        "The sun rose again, and so did another opportunity ☀️",
        "A new morning gently places possibility back in your hands 🌿",
        "Even small steps can carry you somewhere meaningful today 🌸",
        "The quiet moments of a morning often hold the most promise 🌤️",
        "Today doesn't ask you to do everything, only the next right thing 🌱",
        "Another sunrise, another chance to keep building your future ☀️",
        "The path ahead may be long, but today only asks for one step 🚶",

        "Yesterday is finished. Today belongs entirely to you 🌅",
        "Some progress is invisible while it's happening—keep going 🌿",
        "This morning is proof that beginnings are never truly exhausted ✨",
        "A calm start can create a powerful day 🌤️",
        "The world woke up quietly. You can too 🌸",
        "There is no rush to become everything at once 🌱",
        "A steady effort today can become tomorrow's confidence 🌄",
        "Every meaningful journey is built from ordinary mornings ☀️",
        "The future often changes because of small decisions made today 🌿",
        "A new page is waiting patiently for your story 📖",

        "You don't need motivation for every step—consistency can carry you 🌱",
        "The morning air feels like it's gently telling you to begin again 🍃",
        "Growth rarely announces itself while it's happening 🌿",
        "Today's effort may quietly become tomorrow's breakthrough ✨",
        "A quieter day can still feel like a good day 🌤️",
        "There is soft strength in showing up again 🌱",
        "The best progress is often built slowly and kindly 🌸",
        "This morning carries more softness than it first appears ☀️",
        "Small actions have a sweet habit of becoming big outcomes 🌿",
        "Another day to move a little closer to who you're becoming 🌅",

        "The sky changes a little every morning… just like you ☁️",
        "Take today's challenges one gentle step at a time 🌱",
        "The version of you from a year ago would be quietly proud ✨",
        "You don't need a perfect plan to do something meaningful 🌤️",
        "A new morning is a fresh little agreement with your goals 🌸",
        "Momentum often starts with just one small win 🚀",
        "The day ahead doesn't need to be conquered, just lived softly 🌿",
        "There is quiet magic in keeping promises to yourself ☀️",
        "A gentle start still counts as a strong start 🌅",
        "Sometimes resilience just means trying again softly 🌱",

        "The morning arrived carrying tiny invisible possibilities ✨",
        "Today's success may begin with one small focused moment 🎯",
        "Another sunrise gently reminds us that growth takes time 🌄",
        "What feels heavy now may someday feel like strength 🌱",
        "The world keeps moving, and you're moving with it 🌿",
        "A little consistency can quietly beat a lot of motivation 📈",
        "The day ahead is not a test… it's just a chance 🌤️",
        "Trust your becoming, even when it feels slow 🌸",
        "Every morning softly asks: what matters to you today? ☀️",
        "You get another gentle chance to practice being you 🌱",

        # extra cute additions
        "Good morning… your day is already rooting for you 🌱✨",
        "Hey you, the morning brought you a soft new beginning ☀️",
        "Today is quietly cheering for you from the sidelines 🌸",
        "A new morning just checked in on you… hope you're okay 🌤️",
        "The sun showed up again, and so did your chance 🌅",
        "You don’t have to rush—this morning isn’t going anywhere 🌿",
        "A tiny spark of today is already waiting for you ✨",
        "Somewhere inside this morning is a gentle win for you 🌱",
        "The day is softly unfolding… no pressure to force it 🌸",
        "Even the morning is being gentle with you today ☁️",
    ]

    @staticmethod
    def generate() -> str:
        return random.choice(GreetingEngine.MORNING_OPENERS)


# =========================================================
# MAIN ORCHESTRATOR
# =========================================================

class PersonalizedDigestEngine:

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    # ------------------------------------------------------------------
    def _days_since(self, dt_or_date) -> int:
        """Return days between today (UTC) and a date/datetime value."""
        today = datetime.now(timezone.utc).date()
        try:
            d = dt_or_date.date() if hasattr(dt_or_date, "date") else dt_or_date
            return (today - d).days
        except Exception:
            return 999

    # ------------------------------------------------------------------
    def generate_digest(self) -> Dict[str, Any]:

        today_utc = datetime.now(timezone.utc).date()

        # ── Check-in data (last 3 days) ──────────────────────────────────
        recent_checkins = (
            self.db.query(DailyCheckIn)
            .filter(
                DailyCheckIn.user_id == self.user.id,
                DailyCheckIn.date >= today_utc - timedelta(days=3),
            )
            .order_by(desc(DailyCheckIn.date))
            .all()
        )
        avg_energy = (sum(c.energy_score for c in recent_checkins) / len(recent_checkins)) if recent_checkins else 5
        avg_focus  = (sum(c.productivity_score for c in recent_checkins) / len(recent_checkins)) if recent_checkins else 5
        avg_mood   = (sum(c.mood_score for c in recent_checkins) / len(recent_checkins)) if recent_checkins else 5

        # ── Streak data ──────────────────────────────────────────────────
        streak_data      = self.db.query(UserStreak).filter(UserStreak.user_id == self.user.id).first()
        current_streak   = streak_data.current_streak   if streak_data else 0
        longest_streak   = streak_data.longest_streak   if streak_data else 0
        execution_streak = streak_data.execution_streak if streak_data else 0
        freeze_count     = streak_data.freeze_count     if streak_data else 0

        # ── Habit analysis ───────────────────────────────────────────────
        neglected_habits = MemoryEngine.get_neglected_habits(self.db, self.user)
        neglected_habit  = random.choice(neglected_habits) if neglected_habits else None

        # ── Reflection ───────────────────────────────────────────────────
        reflection     = MemoryEngine.get_recent_reflection(self.db, self.user.id)
        distraction    = reflection.biggest_distraction if reflection else None
        proud_moment   = reflection.proud_moment        if reflection else None
        what_went_well = reflection.what_went_well      if reflection else None

        # ── Execution data ───────────────────────────────────────────────
        yesterday_summary  = MemoryEngine.get_yesterday_commitment_summary(self.db, self.user.id)
        todays_commitments = MemoryEngine.get_todays_commitments(self.db, self.user.id)
        retro_summary      = MemoryEngine.get_retroactive_summary(self.db, self.user.id)

        # ── Supporting data ──────────────────────────────────────────────
        active_goals       = MemoryEngine.get_active_goals(self.db, self.user.id)
        today_priority     = MemoryEngine.get_today_priority(self.db, self.user.id)
        mood_trend         = MemoryEngine.get_mood_trend(self.db, self.user.id)
        failure_pattern    = MemoryEngine.get_failure_pattern(self.db, self.user.id)
        top_focus_area     = MemoryEngine.get_top_focus_area(self.db, self.user.id)
        procrastination_on = MemoryEngine.get_procrastination_signal(self.db, self.user.id)
        daily_note         = MemoryEngine.get_daily_note(self.db, self.user.id)

        # ── DATA FRESHNESS — core fix ────────────────────────────────────
        # Find how many days since the user last had ANY commitment activity
        last_commit = (
            self.db.query(Commitment)
            .filter(Commitment.user_id == self.user.id)
            .order_by(Commitment.start_time.desc())
            .first()
        )
        days_since_commit = self._days_since(last_commit.start_time) if last_commit else 999

        # Find how many days since last check-in
        last_checkin = (
            self.db.query(DailyCheckIn)
            .filter(DailyCheckIn.user_id == self.user.id)
            .order_by(DailyCheckIn.date.desc())
            .first()
        )
        days_since_checkin = self._days_since(last_checkin.date) if last_checkin else 999

        # Fresh outcome notes = only last 2 days (not the stale 3-day window)
        fresh_outcome_notes = (
            self.db.query(Commitment)
            .filter(
                Commitment.user_id == self.user.id,
                Commitment.outcome_note.isnot(None),
                Commitment.created_at >= datetime.now(timezone.utc) - timedelta(days=2),
            )
            .order_by(desc(Commitment.created_at))
            .limit(2)
            .all()
        )
        fresh_notes = [
            c.outcome_note for c in fresh_outcome_notes
            if c.outcome_note and len(c.outcome_note.strip()) > 3
        ]

        # ── USER MODE — based on current (not stale) activity only ───────
        currently_active = (
            yesterday_summary["had_data"]          # did something yesterday
            or len(todays_commitments) > 0         # planned something today
            or days_since_commit <= 1              # committed today or yesterday
        )
        user_mode = "execution_user" if currently_active else "wellness_only_user"

        # ── Behavioral state ─────────────────────────────────────────────
        behavior = BehavioralAnalyzer.analyze(
            avg_energy, avg_focus, avg_mood,
            current_streak, longest_streak, len(neglected_habits),
        )
        state = behavior["state"]

        # ── Prompt meta ──────────────────────────────────────────────────
        goals_context     = ", ".join(active_goals) if active_goals else "no active goals set"
        tone_label        = self.user.preferred_tone or "supportive"
        struggles_context = ", ".join(self.user.struggles) if self.user.struggles else "none specified"
        available_time    = self.user.daily_time_minutes or 60
        writing_style     = random.choice(WRITING_STYLES)
        poetic_greeting   = GreetingEngine.generate()
        first_name        = self.user.name.split()[0]

        # ── Bake greeting in Python — Gemini cannot change it ────────────
        import re as _re
        _et = _re.search(r'[\U0001F300-\U0001FFFF\u2600-\u27BF\U0001FA00-\U0001FFFF]+\s*$', poetic_greeting)
        if _et:
            _base  = poetic_greeting[:_et.start()].rstrip()
            _emoji = _et.group().strip()
            greeting_line = (
                f"{_base} {first_name} {_emoji}"
                if _base.endswith((',', '.', '!', '?', '\u2014', '\u2013'))
                else f"{_base}, {first_name} {_emoji}"
            )
        else:
            greeting_line = f"{poetic_greeting}, {first_name}"

        # ════════════════════════════════════════════════════════════════
        # PILLAR 1 — WHAT HAPPENED  (fresh data only)
        # ════════════════════════════════════════════════════════════════
        if daily_note and len(daily_note.strip()) > 5:
            # MemoryEngine already restricts this to yesterday/today
            p1 = f'User wrote about yesterday in their own words: "{daily_note.strip()}"'

        elif fresh_notes:
            # Only last 2 days — prevents stale 3-day-old notes repeating
            p1 = f"Fresh session notes (last 2 days): {'; '.join(fresh_notes)}"

        elif yesterday_summary["had_data"]:
            c, t = yesterday_summary['completed'], yesterday_summary['total']
            if c == t and t > 0:
                p1 = f"Completed all {t} planned sessions yesterday. Perfect execution day."
            elif c > 0:
                p1 = f"Completed {c} of {t} planned sessions yesterday."
            else:
                p1 = f"Missed all {t} planned sessions yesterday. Be kind — no lecture."

        elif retro_summary and retro_summary != "no retroactive work logged yesterday":
            p1 = f"No planned sessions yesterday but logged retroactive work: {retro_summary}"

        elif days_since_commit == 0:
            p1 = "Sessions planned for today — nothing logged from yesterday yet."

        elif 1 <= days_since_commit <= 3:
            # User was active 1-3 days ago but quiet since — DON'T repeat old data
            p1 = (
                f"No commitment activity for {days_since_commit} day(s). "
                "Do NOT reference their old sessions. "
                "Anchor on check-in data, habit streak, or how they're feeling today."
            )

        elif days_since_checkin <= 1:
            p1 = (
                "No commitment activity recently, but they checked in today/yesterday. "
                "Anchor on their energy/mood and habit streak."
            )

        else:
            # Truly quiet — no data at all
            p1 = (
                "No recent activity of any kind. "
                "Keep email gentle and forward-looking. "
                "Don't fabricate or reference old data."
            )

        # ════════════════════════════════════════════════════════════════
        # STREAK CONTEXT (exact numbers)
        # ════════════════════════════════════════════════════════════════
        if current_streak == 0:
            streak_ctx = f"Habit streak at 0 (personal best was {longest_streak} days). Be gentle."
        elif current_streak >= 30:
            streak_ctx = f"Habit streak: {current_streak} days. Personal best: {longest_streak}. Exceptional — name the number."
        elif current_streak >= 14:
            streak_ctx = f"Habit streak: {current_streak} days. Personal best: {longest_streak}. Two weeks — name it."
        elif current_streak >= 7:
            streak_ctx = f"Habit streak: {current_streak} days. Personal best: {longest_streak}. Full week — mention naturally."
        else:
            streak_ctx = f"Habit streak: {current_streak} days. Personal best: {longest_streak}."
        exec_streak_ctx = (
            f"Execution streak: {execution_streak} days."
            if execution_streak > 0 else "No active execution streak."
        )

        # ════════════════════════════════════════════════════════════════
        # PILLAR 2+3 — PATTERN + MEANING
        # ════════════════════════════════════════════════════════════════
        patterns_found = []
        # Only reference failure/procrastination patterns if user was recently active
        if days_since_commit <= 7:
            if failure_pattern:
                patterns_found.append(f"recurring failure reason: {failure_pattern}")
            if procrastination_on:
                patterns_found.append("rescheduling/avoiding commitments repeatedly")
        # Mood and check-in patterns are always valid
        if mood_trend == "declining":
            patterns_found.append("energy and mood declining over last few days")
        elif mood_trend == "improving":
            patterns_found.append("energy and mood picking up over last few days")
        if neglected_habit:
            patterns_found.append(f"habit '{neglected_habit}' neglected 4+ days")
        if proud_moment and str(proud_moment).strip() not in ("", "not filled", "None"):
            patterns_found.append(f"recent proud moment: '{proud_moment}'")
        if what_went_well and str(what_went_well).strip() not in ("", "not filled", "None"):
            patterns_found.append(f"what went well: '{what_went_well}'")
        if distraction and str(distraction).strip() not in ("", "not filled", "None"):
            patterns_found.append(f"biggest distraction: '{distraction}'")
        if top_focus_area and days_since_commit <= 7:
            patterns_found.append(f"most time invested in: {top_focus_area}")
        pattern_ctx = "; ".join(patterns_found) if patterns_found else "no strong patterns this week"

        state_labels = {
            "burnout_risk":  "burnout risk — be extra gentle, no productivity push",
            "distracted":    "scattered focus — acknowledge gently, no guilt",
            "rebuilding":    "rebuilding — encouraging but no pressure",
            "high_momentum": "strong momentum — match the energy, acknowledge specifically",
            "inconsistency": "inconsistent — acknowledge effort, not just the gaps",
            "steady_growth": "steady consistent effort, building quietly",
        }
        state_ctx = state_labels.get(state, "steady progress")

        meaning_hints = []
        if (failure_pattern == "distraction or avoidance" or procrastination_on) and days_since_commit <= 7:
            meaning_hints.append("barrier is starting, not sustaining — fine once begun")
        if failure_pattern == "underestimating how long tasks take" and days_since_commit <= 7:
            meaning_hints.append("planning gaps, not motivation gaps")
        if failure_pattern == "external blockers outside their control" and days_since_commit <= 7:
            meaning_hints.append("external circumstances, not personal failure")
        if mood_trend == "declining" and avg_energy < 5:
            meaning_hints.append("energy depletion may be the real bottleneck, not discipline")
        if current_streak >= 7 and yesterday_summary.get("completed", 0) > 0:
            meaning_hints.append("sustained consistency proves they follow through when they start")
        if days_since_commit > 3 and days_since_commit <= 7:
            meaning_hints.append(
                f"they've been quiet for {days_since_commit} days — "
                "this is a natural rest/drift, not failure"
            )
        if not meaning_hints:
            meaning_hints.append("steady effort — keep building on what's working")
        meaning_ctx = "; ".join(meaning_hints)

        # ════════════════════════════════════════════════════════════════
        # PILLAR 4 — RECOMMENDATION
        # ════════════════════════════════════════════════════════════════
        # PILLAR 4 — RECOMMENDATION
        # ════════════════════════════════════════════════════════════════

        # ── Derive a suggested work topic when nothing is planned ────────
        # This gives Gemini something specific to name even with no sessions
        _goal       = self.user.primary_goal or "their goals"
        fa_list     = self.user.focus_areas or []
        fa_str      = ", ".join(fa_list) if fa_list else "their focus areas"
        habits_str  = ", ".join(self.user.habits) if self.user.habits else "their habits"
        struggles_list = self.user.struggles or []

        # What work topic should be suggested? Priority: today's data > yesterday's > goal > focus area
        if today_priority and today_priority.strip() not in ("", "no priority set for today"):
            today_work = f'Stated priority: "{today_priority.strip()}". Reference it directly.'
            suggested_work = today_priority.strip()

        elif todays_commitments:
            today_work = (
                f"Planned today: {', '.join(todays_commitments)} ({len(todays_commitments)} total). "
                "Name the actual work."
            )
            suggested_work = todays_commitments[0].split(" at ")[0]

        elif user_mode == "wellness_only_user":
            if state == "burnout_risk":
                today_work    = f"Wellness-only. Habits: {habits_str}. Goal: {_goal}. Burnout — rest or ONE gentle thing."
                suggested_work = "rest or a single gentle habit"
            elif neglected_habit:
                today_work    = f"Wellness-only. Habit '{neglected_habit}' quiet 4+ days. Goal: {_goal}. Make re-entry easy."
                suggested_work = neglected_habit
            else:
                fa_pick = fa_list[0] if fa_list else "their main habit"
                today_work    = f"Wellness-only. Habits: {habits_str}. Areas: {fa_str}. Goal: {_goal}. One habit → goal."
                suggested_work = fa_pick

        else:
            # Execution user — nothing planned yet before 7am
            # Derive a specific suggestion from yesterday + goal + focus areas
            if yesterday_summary["had_data"] and yesterday_summary["completed"] > 0:
                # They worked yesterday — suggest continuing on the same track
                yesterday_topic = fresh_notes[0] if fresh_notes else (top_focus_area or fa_str)
                today_work = (
                    f"Nothing planned yet today. Yesterday they completed {yesterday_summary['completed']} session(s). "
                    f"Yesterday's topic/area: {yesterday_topic}. Goal: {_goal}. "
                    "Suggest they continue from where they left off — name that specific work."
                )
                suggested_work = yesterday_topic
            elif top_focus_area:
                # Use their biggest focus area this week as anchor
                today_work = (
                    f"Nothing planned yet today. Top focus area this week: {top_focus_area}. "
                    f"Goal: {_goal}. Suggest one specific session in {top_focus_area}."
                )
                suggested_work = top_focus_area
            elif fa_list:
                # Fall back to their registered focus areas
                fa_pick = fa_list[0]
                today_work = (
                    f"Nothing planned yet today. Goal: {_goal}. Focus areas: {fa_str}. "
                    f"Suggest starting with {fa_pick} — name a specific type of session."
                )
                suggested_work = fa_pick
            elif days_since_commit > 3:
                today_work = (
                    f"Away {days_since_commit} days. Goal: {_goal}. Areas: {fa_str}. "
                    "Suggest one very small re-entry action — easy enough to feel silly not doing."
                )
                suggested_work = _goal
            else:
                today_work    = f"Nothing planned. Goal: {_goal}. Areas: {fa_str}. Suggest one clear session."
                suggested_work = _goal

        # ── Recommendation logic (uses suggested_work for specificity) ───
        if days_since_commit > 3:
            rec_ctx = (
                f"Away {days_since_commit} days. Suggest: {suggested_work}. "
                "Make re-entry feel ridiculously easy — one tiny action, no pressure, no guilt."
            )
        elif (failure_pattern == "distraction or avoidance" or procrastination_on) and days_since_commit <= 7:
            rec_ctx = (
                f"Pattern: avoidance/procrastination. Work to do: {suggested_work}. "
                "Make first action tiny — name the absolute smallest step inside that work. "
                "E.g., 'open the problem and read it for 30 seconds'. Starting beats planning."
            )
        elif not todays_commitments and not (today_priority and today_priority.strip() not in ("", "no priority set for today")):
            # Nothing planned — email IS the plan
            rec_ctx = (
                f"Nothing planned yet today. Suggest: {suggested_work}. "
                "Write the recommendation as if you're giving them their plan for the morning. "
                "Name the specific work, the approximate time it takes, and why it matters today. "
                "Make it feel like a clear invitation, not a generic nudge."
            )
        elif state == "burnout_risk":
            rec_ctx = f"Burnout risk. Suggest: {suggested_work}. Recovery, not productivity."
        elif neglected_habit and user_mode == "wellness_only_user":
            rec_ctx = f"Return to '{neglected_habit}' — 5-minute version only. Lower the bar."
        elif mood_trend == "declining":
            rec_ctx = f"Declining energy. Suggest: {suggested_work}. One gentle action. Small. No pressure."
        elif (yesterday_summary.get("had_data") and
              yesterday_summary.get("completed", 0) == yesterday_summary.get("total", 1) and
              yesterday_summary.get("total", 0) > 0):
            rec_ctx = f"Yesterday was perfect. Build on it: {suggested_work}. Go slightly deeper."
        else:
            rec_ctx = f"Natural next step: {suggested_work}. One specific action tied to their primary goal."

        # ════════════════════════════════════════════════════════════════
        # PILLAR 5 — ENCOURAGEMENT (real evidence only)
        # ════════════════════════════════════════════════════════════════
        evidence_parts = []
        if proud_moment and str(proud_moment).strip() not in ("", "not filled", "None"):
            evidence_parts.append(f"proud of: '{proud_moment}'")
        if fresh_notes:
            evidence_parts.append(f"wrote about their work: '{fresh_notes[0]}'")
        if current_streak >= 7:
            evidence_parts.append(f"{current_streak}-day habit streak")
        if yesterday_summary.get("had_data") and yesterday_summary.get("completed", 0) > 0:
            evidence_parts.append(f"completed {yesterday_summary['completed']} session(s) yesterday")
        if execution_streak >= 3 and days_since_commit <= 3:
            evidence_parts.append(f"{execution_streak}-day execution streak")
        if not evidence_parts:
            evidence_parts.append("keeps returning even after quiet days — that itself is commitment")
        evidence_ctx = "; ".join(evidence_parts)

        # ════════════════════════════════════════════════════════════════
        # PROMPT
        # ════════════════════════════════════════════════════════════════
        prompt = f"""You are {first_name}'s personal AI coach at Velora.
Write their morning email. Must feel like a message from a trusted friend who actually read their last few days.
Style: {writing_style} | Voice: {tone_label} | User type: {user_mode}
Days since last commitment: {days_since_commit} | Days since last check-in: {days_since_checkin}

━━━ DATA (use this — don't make things up) ━━━

PILLAR 1 — WHAT HAPPENED (exact numbers only for real recent events):
  {p1}
  Retroactive work yesterday: {retro_summary}
  {streak_ctx}
  {exec_streak_ctx}
  Streak freezes: {freeze_count}

PILLAR 2 — PATTERN (natural language, no scores):
  {pattern_ctx}
  State: {state_ctx}

PILLAR 3 — WHAT IT MEANS:
  {meaning_ctx}

PILLAR 4 — ONE RECOMMENDATION:
  {rec_ctx}
  Today's work: {today_work}
  Top focus area: {top_focus_area or "not tagged"}

PILLAR 5 — EVIDENCE (real, specific):
  {evidence_ctx}

USER:
  Goal: {self.user.primary_goal} | Active goals: {goals_context}
  Focus areas: {self.user.focus_areas} | Struggles: {struggles_context}
  Available: {available_time} min/day

━━━ WRITE THESE 6 FIELDS ━━━

"subject" — Under 9 words, specific to today.
  Use exact numbers when earned: "{current_streak} days straight 🌿" | "Back after a few quiet days" | "One small thing today"
  NEVER: "Your Morning Brief" / "Good Morning" / "Daily Digest"

"greeting" — USE EXACTLY, no changes:
  "{greeting_line}"

"what_happened" — Pillar 1 (2–3 sentences):
  Warm, factual recap. Exact numbers for real recent events.
  If no recent execution data: anchor on check-in streak, habit, or how they're feeling.
  If they've been away 3+ days: acknowledge the quiet gap warmly — no guilt.
  Wellness-only: no execution language at all.

"pattern_and_meaning" — Pillars 2+3 (3–5 sentences):
  Name the pattern (natural language). Then one interpretation — thoughtful, not clinical.
  If away 3+ days: "Sometimes a few quiet days is the mind resetting, not the person giving up."
  If avoidance: "The challenge seems to be starting, not sustaining."
  If declining energy: "This might not be a discipline issue — the tank might need refilling."
  Be specific to {first_name}.

"recommendation" — Pillar 4 (2–3 sentences):
  ONE action only. Specific and micro.
  IMPORTANT: If the user has nothing planned for today (no sessions, no priority set):
    The "One Thing For Today" box IS their plan — treat it that way.
    Don't say "plan your day" or "open Velora". Instead, give them the actual work:
    Name the specific thing they should do, roughly how long it takes, and why it matters now.
    Example: "Spend 45 minutes on LeetCode DP problems this morning — you've been building toward
    this all week and your energy is best before noon."
  If avoidance/procrastination: name the smallest first step by its actual name.
  If away 3+ days: make re-entry feel ridiculously easy — one tiny thing, no guilt.
  FORBIDDEN: "protect time" / "schedule blocks" / "plan your day" / "open Velora" / "be productive"

"encouragement" — Pillar 5 (2–3 sentences):
  Real evidence only. Exact numbers. Something specific they did or said.
  If quiet period: coming back after a gap is its own kind of strength.
  End warm, no pressure.

"quote" — Original, under 18 words, for state: {state}. Feels written for this moment.

━━━ HARD RULES ━━━
EXACT NUMBERS for: streaks, sessions, hours, milestones
NATURAL LANGUAGE for: mood, energy, focus, procrastination patterns
NEVER: AI-speak | corporate language | fake praise | generic sentences | bullet points in fields | rewrite greeting | 2+ recommendations
If days_since_commit > 3: do NOT reference old specific sessions — only streak and feelings.

━━━ RETURN ONLY VALID JSON ━━━
{{
    "subject": "",
    "greeting": "{greeting_line}",
    "what_happened": "",
    "pattern_and_meaning": "",
    "recommendation": "",
    "encouragement": "",
    "quote": "",
    "author": "Velora"
}}"""

        try:
            raw_text = (
                _generate(prompt)
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            result = json.loads(raw_text)
            result["greeting"] = greeting_line  # always enforce
            return result
        except Exception as e:
            print(f"[Velora AI] Digest generation failed: {e}")
            return self._fallback_digest()

    # ------------------------------------------------------------------
    def _fallback_digest(self) -> Dict[str, Any]:
        first_name = self.user.name.split()[0]
        opener     = GreetingEngine.generate()
        import re as _re
        _et = _re.search(r'[\U0001F300-\U0001FFFF\u2600-\u27BF\U0001FA00-\U0001FFFF]+\s*$', opener)
        if _et:
            _b = opener[:_et.start()].rstrip()
            gl = f"{_b}, {first_name} {_et.group().strip()}"
        else:
            gl = f"{opener}, {first_name}"
        return {
            "subject":             f"A quiet morning is waiting, {first_name} 🌤️",
            "greeting":            gl,
            "what_happened":       (
                "Yesterday had its own rhythm — some things moved forward, others waited. "
                "That's just how days go sometimes."
            ),
            "pattern_and_meaning": (
                "There's often a quiet push-pull between intention and action. "
                "That usually means the challenge isn't capability — it's the energy cost of starting. "
                "Most people who struggle with consistency just haven't made the first step small enough."
            ),
            "recommendation":      (
                "Today, pick the single smallest version of your most important task. "
                "Not the full session — just the first five minutes. Start there."
            ),
            "encouragement":       (
                "The fact that you keep showing up, even after quiet days, is its own kind of proof. "
                "Not everyone does that."
            ),
            "quote":   "The first step doesn't have to be impressive. It just has to happen.",
            "author":  "Velora",
        }

