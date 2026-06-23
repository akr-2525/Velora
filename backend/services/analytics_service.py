"""
Velora Analytics Service
Module 9: Analytics separation — execution vs time-allocation
Module 10: Actionable AI insight generation via Gemini
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.models.user_model import HabitLog, DailyCheckIn
from backend.models.commitment_model import Commitment


def get_weekly_analytics(db: Session, user_id: int) -> dict:
    """
    7-day performance snapshot.
    Used in the weekly email and the dashboard wellness section.
    """
    today = datetime.now(timezone.utc).date()
    seven_days_ago = today - timedelta(days=7)
    seven_days_ago_dt = datetime.combine(
        seven_days_ago, datetime.min.time()
    ).replace(tzinfo=timezone.utc)

    # ── Habit consistency ───────────────────────────────────────────────────
    logs = db.query(HabitLog).filter(
        HabitLog.user_id == user_id,
        HabitLog.completed_at >= seven_days_ago_dt,
    ).all()
    unique_days = {log.completed_at.date() for log in logs}
    days_logged = len(unique_days)
    # Cap display at 7 — boundary logs can push count to 8
    days_logged_display = min(7, days_logged)
    consistency_pct = min(100, int((days_logged_display / 7) * 100))

    # ── Mental state averages (email check-ins) ─────────────────────────────
    checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.date >= seven_days_ago,
    ).all()
    if checkins:
        avg_mood  = round(sum(c.mood_score for c in checkins) / len(checkins), 1)
        avg_energy = round(sum(c.energy_score for c in checkins) / len(checkins), 1)
        avg_prod  = round(sum(c.productivity_score for c in checkins) / len(checkins), 1)
    else:
        avg_mood = avg_energy = avg_prod = 0.0

    # ── Module 9: Execution rate — planned only ─────────────────────────────
    all_commits = db.query(Commitment).filter(
        Commitment.user_id == user_id,
        Commitment.created_at >= seven_days_ago_dt,
    ).all()

    planned = [c for c in all_commits if c.commitment_type == "planned"]
    retro   = [c for c in all_commits if c.commitment_type == "retroactive"]

    total_planned   = len(planned)
    completed_planned = sum(1 for c in planned if c.status == "completed")
    exec_rate = round((completed_planned / total_planned * 100) if total_planned else 0.0, 1)

    # ── Time-allocation (planned + retroactive) ─────────────────────────────
    def _mins(c):
        s = c.start_time.replace(tzinfo=timezone.utc) if c.start_time.tzinfo is None else c.start_time
        e = c.end_time.replace(tzinfo=timezone.utc) if c.end_time.tzinfo is None else c.end_time
        return max(0, int((e - s).total_seconds() / 60))

    total_work_minutes = sum(_mins(c) for c in all_commits)
    retro_minutes = sum(_mins(c) for c in retro)
    focus_breakdown: dict = {}
    for c in all_commits:
        if c.focus_area:
            focus_breakdown[c.focus_area] = (
                focus_breakdown.get(c.focus_area, 0) + _mins(c)
            )

    # ── Energy vs execution correlation (planned only) ──────────────────────
    energy_execution_pairs = []
    for ci in checkins:
        day_p = [c for c in planned if c.start_time.date() == ci.date]
        if day_p:
            day_rate = sum(1 for c in day_p if c.status == "completed") / len(day_p) * 100
            energy_execution_pairs.append({
                "date":            ci.date.isoformat(),
                "energy":          ci.energy_score,
                "completion_rate": round(day_rate, 1),
            })

    return {
        "consistency_percentage":       consistency_pct,
        "days_logged":                  days_logged_display,
        "average_mood":                 avg_mood,
        "average_energy":               avg_energy,
        "average_productivity":         avg_prod,
        "commitment_completion_rate":   exec_rate,
        "total_planned":                total_planned,
        "completed_planned":            completed_planned,
        "total_work_minutes":           total_work_minutes,
        "retroactive_minutes":          retro_minutes,
        "focus_area_breakdown":         focus_breakdown,
        "energy_execution_correlation": energy_execution_pairs,
    }


def generate_weekly_behavioral_insight(analytics: dict) -> str:
    """
    Module 10: Generate one concise, actionable AI insight.
    Uses Gemini to produce at most 2 sentences.
    Falls back to a rule-based insight if AI is unavailable.
    """
    import os
    import json
    try:
        from google import genai as _ga
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("No GEMINI_API_KEY")
        _ga_client = _ga.Client(api_key=api_key)

        pairs = analytics.get("energy_execution_correlation", [])
        avg_energy = analytics.get("average_energy", 0)
        exec_rate  = analytics.get("commitment_completion_rate", 0)
        retro_mins = analytics.get("retroactive_minutes", 0)
        total_mins = analytics.get("total_work_minutes", 0)
        focus_bd   = analytics.get("focus_area_breakdown", {})

        prompt = f"""
You are a behavioral analytics engine for Velora, an execution intelligence platform.

Based on the following 7-day user data, generate ONE specific, actionable recommendation.
Maximum 2 sentences. No bullet points. No headers. Plain text only.
Do not mention "Velora". Do not use generic advice.
Make it feel like a data-driven coaching observation.

DATA:
- Average energy score: {avg_energy}/10
- Planned commitment completion rate: {exec_rate}%
- Retroactive (already-done) minutes logged: {retro_mins} min
- Total work minutes logged: {total_mins} min
- Focus area breakdown: {json.dumps(focus_bd)}
- Energy vs completion pairs (last 7 days): {json.dumps(pairs[:7])}

RETURN ONLY THE 1-2 SENTENCE INSIGHT. NO EXTRA TEXT.
"""
        response = _ga_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        insight = response.text.strip()
        sentences = insight.split(". ")
        return ". ".join(sentences[:2]).strip()

    except Exception as e:
        print(f"[Velora] Insight generation failed: {e}")
        return _rule_based_insight(analytics)


def _rule_based_insight(analytics: dict) -> str:
    """Deterministic fallback insight when AI is unavailable."""
    exec_rate  = analytics.get("commitment_completion_rate", 0)
    avg_energy = analytics.get("average_energy", 0)
    retro_mins = analytics.get("retroactive_minutes", 0)
    total_mins = analytics.get("total_work_minutes", 0)
    pairs      = analytics.get("energy_execution_correlation", [])
    focus_bd   = analytics.get("focus_area_breakdown", {})

    # High energy — low execution
    if avg_energy >= 7 and exec_rate < 50:
        return (
            "Your energy levels have been high this week, but planned commitment "
            "completion is below 50%. Consider whether your planned blocks are "
            "realistically scoped."
        )

    # Strong correlation signal
    if len(pairs) >= 3:
        high_e = [p for p in pairs if p["energy"] >= 7]
        low_e  = [p for p in pairs if p["energy"] <= 4]
        if high_e and low_e:
            hi_rate = sum(p["completion_rate"] for p in high_e) / len(high_e)
            lo_rate = sum(p["completion_rate"] for p in low_e) / len(low_e)
            if hi_rate - lo_rate >= 30:
                return (
                    f"You complete {int(hi_rate)}% of commitments on high-energy days "
                    f"versus {int(lo_rate)}% on low-energy days. "
                    "Move your hardest planned blocks to your highest-energy windows."
                )

    # Heavy retroactive logging
    if total_mins > 0 and retro_mins / total_mins > 0.6:
        return (
            "More than 60% of your logged work this week was retroactive. "
            "Your execution instincts are good — try planning blocks in advance "
            "to improve your forecasting accuracy."
        )

    # Top focus area
    if focus_bd:
        top_area = max(focus_bd, key=focus_bd.get)
        top_mins = focus_bd[top_area]
        return (
            f"You invested {top_mins} minutes in '{top_area}' this week — "
            "your dominant focus area. Make sure your planned commitments "
            "reflect this intentionally."
        )

    # Generic fallback
    return (
        "Start each day by locking in your one highest-priority planned commitment. "
        "Consistency on the most important block compounds faster than finishing many smaller ones."
    )
