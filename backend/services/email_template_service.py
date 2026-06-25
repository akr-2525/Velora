"""
Velora email HTML templates.
All templates reference FRONTEND_URL from env so they work in any deployment.
"""

import os
import json
from google import genai as _genai
from dotenv import load_dotenv

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")
BACKEND_URL  = os.getenv("BACKEND_URL",  "http://127.0.0.1:8000")

_api_key = os.getenv("GEMINI_API_KEY")
_client  = _genai.Client(api_key=_api_key) if _api_key else None
_MODEL   = "gemini-2.5-flash-lite"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _bar(pct: float, color_start: str, color_end: str) -> str:
    """Render an inline progress bar (light-themed body)."""
    w = min(int(pct), 100)
    return (
        f'<div style="width:100%;background:#e5e7eb;border-radius:8px;height:14px;margin-bottom:6px;">'
        f'<div style="width:{w}%;background:linear-gradient(90deg,{color_start},{color_end});'
        f'height:100%;border-radius:8px;"></div></div>'
    )


def _stat_row(label: str, value: str, color: str = "#1a1a2e") -> str:
    return (
        f'<tr>'
        f'<td style="padding:5px 0;font-size:14px;color:#6b7280;">{label}</td>'
        f'<td style="text-align:right;font-weight:700;font-size:15px;color:{color};">{value}</td>'
        f'</tr>'
    )


def _section_header(title: str, emoji: str = "") -> str:
    return (
        f'<p style="margin:24px 0 10px;font-size:11px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:#9ca3af;">{emoji}&nbsp; {title}</p>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI WEEKLY SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def _generate_weekly_ai_summary(
    user_name: str,
    analytics: dict,
    commitment_stats: dict,
    reflection: dict,
    user_goal: str,
) -> dict:
    """
    Generate a 3-part AI weekly summary.
    Automatically adapts tone/content based on whether the user uses execution features.
    """
    first_name = user_name.split()[0]

    pct         = analytics.get("consistency_percentage", 0)
    days_active = analytics.get("days_logged", 0)
    avg_mood    = analytics.get("average_mood", 0)
    avg_energy  = analytics.get("average_energy", 0)
    avg_prod    = analytics.get("average_productivity", 0)
    total_mins  = analytics.get("total_work_minutes", 0)
    retro_mins  = analytics.get("retroactive_minutes", 0)
    focus_bd    = analytics.get("focus_area_breakdown", {})

    total_planned   = commitment_stats.get("total_planned", 0)   if commitment_stats else 0
    completed_count = commitment_stats.get("completed_count", 0) if commitment_stats else 0
    missed_count    = commitment_stats.get("missed_count", 0)    if commitment_stats else 0
    partial_count   = commitment_stats.get("partial_count", 0)   if commitment_stats else 0
    best_slot       = commitment_stats.get("best_time_slot", "—") if commitment_stats else "—"
    recovery_rate   = commitment_stats.get("recovery_rate_percentage", 0) if commitment_stats else 0
    procras_count   = commitment_stats.get("procrastination_count", 0)    if commitment_stats else 0
    hours_total     = round(total_mins / 60, 1)

    # Determine user type
    is_execution_user = total_planned > 0 or retro_mins > 0

    # Reflection block
    reflection_block = ""
    if reflection:
        ww = reflection.get("what_went_well", "")
        bd = reflection.get("biggest_distraction", "")
        pm = reflection.get("proud_moment", "")
        if any([ww, bd, pm]):
            reflection_block = (
                f"Weekly reflection (their own words):\n"
                f"  What went well: {ww or 'not filled'}\n"
                f"  Biggest distraction: {bd or 'not filled'}\n"
                f"  Proud moment: {pm or 'not filled'}"
            )

    focus_str = ", ".join(f"{k}: {v}min" for k, v in list(focus_bd.items())[:4]) if focus_bd else "none"

    # ── Build execution section only if relevant ─────────────────────────────
    if is_execution_user:
        execution_data_block = f"""
EXECUTION (use exact numbers):
  Total planned sessions: {total_planned}
  Completed: {completed_count} | Missed: {missed_count} | Partial: {partial_count}
  Completion rate: {analytics.get("commitment_completion_rate", 0)}%
  Total work logged: {hours_total} hours
  Retroactive work: {retro_mins} minutes
  Best time slot: {best_slot}
  Recovery rate: {recovery_rate}%
  Procrastination flags: {procras_count}
  Focus areas: {focus_str}"""
        user_mode_instruction = """
USER TYPE: execution_user — they plan and log time-blocked sessions.
  → week_summary: reference specific sessions completed, hours logged, patterns in execution.
  → key_insight: most important execution or habit pattern — specific, data-driven.
  → next_week_nudge: one execution or habit intention tied to their goal."""
    else:
        execution_data_block = f"""
EXECUTION: None — this user does NOT use the commitment/execution planner.
  They only track habits and wellness check-ins.
  Retroactive work logged: {retro_mins} minutes
  Focus areas tagged: {focus_str}"""
        user_mode_instruction = """
USER TYPE: wellness_only_user — they track habits and daily check-ins only.
  → week_summary: DO NOT mention sessions, commitments, planned work, or execution rate.
    Focus entirely on: habit consistency, how their mood/energy felt, check-in streak,
    and anything from their reflection.
  → key_insight: most important wellness/habit pattern — mood trend, energy pattern,
    habit they kept or neglected, something from their reflection.
  → next_week_nudge: one habit or wellness intention for next week. Warm, specific,
    NOT about planning sessions or execution."""

    prompt = f"""You are {first_name}'s personal AI coach at Velora writing their Sunday weekly summary email.

Write 3 short sections. Warm, human, specific to this person's actual week.
NOT generic. NOT corporate. Like a thoughtful friend who watched their week unfold.

{user_mode_instruction}

━━━ THIS WEEK'S DATA ━━━
User: {first_name} | Goal: {user_goal or "personal growth"}

HABIT & WELLNESS:
  Habit consistency: {pct}% ({days_active}/7 days)
  Average mood: {avg_mood}/10 (natural language only in email — no scores)
  Average energy: {avg_energy}/10 (natural language only)
  Average productivity: {avg_prod}/10 (natural language only)
{execution_data_block}

{reflection_block}

━━━ WRITE 3 FIELDS ━━━

"week_summary" (3–4 sentences):
  Warm, specific recap of what actually happened.
  Use exact numbers for: habit days, sessions completed (if execution user), hours logged, milestones.
  Use natural language for mood/energy.
  Weave in reflection data if available. Make them feel seen, not evaluated.

"key_insight" (2–3 sentences):
  The ONE most important observation from this week.
  Specific and insightful — not "you did great" but name the actual pattern.
  Natural language for mood/energy. Exact numbers for execution/habit facts.

"next_week_nudge" (2–3 sentences):
  One specific intention for next week. Named clearly.
  Forward momentum, not pressure. References their goal or top area.

━━━ RULES ━━━
EXACT NUMBERS: habit days, sessions, hours, streak days, rates
NATURAL LANGUAGE: mood, energy, focus, procrastination
NEVER: AI-speak | corporate clichés | fake praise | bullet points in fields | generic sentences
If wellness_only_user: NEVER mention sessions, commitments, execution rate, or planning.

Return ONLY valid JSON:
{{
    "week_summary": "",
    "key_insight": "",
    "next_week_nudge": ""
}}"""

    try:
        if not _client:
            raise RuntimeError("No Gemini client")
        import time as _time
        last_error = None
        for attempt in range(3):
            try:
                response = _client.models.generate_content(model=_MODEL, contents=prompt)
                raw = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(raw)
            except Exception as e:
                last_error = e
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    wait = (attempt + 1) * 8
                    print(f"[Velora] Weekly AI 503 attempt {attempt+1}, retry in {wait}s...")
                    _time.sleep(wait)
                else:
                    raise
        raise last_error
    except Exception as e:
        print(f"[Velora] Weekly AI summary failed: {e}")
        return _fallback_weekly_summary(
            first_name, analytics, commitment_stats,
            is_execution_user=is_execution_user
        )


def _fallback_weekly_summary(
    first_name: str,
    analytics: dict,
    commitment_stats: dict,
    is_execution_user: bool = True,
) -> dict:
    pct         = analytics.get("consistency_percentage", 0)
    days_active = analytics.get("days_logged", 0)
    total_mins  = analytics.get("total_work_minutes", 0)
    hours       = round(total_mins / 60, 1)
    avg_energy  = analytics.get("average_energy", 0)

    if is_execution_user:
        completed = commitment_stats.get("completed_count", 0) if commitment_stats else 0
        total     = commitment_stats.get("total_planned", 0)   if commitment_stats else 0
        exec_rate = analytics.get("commitment_completion_rate", 0)
        return {
            "week_summary": (
                f"This week you showed up {days_active} out of 7 days for your habits "
                f"and completed {completed} of {total} planned sessions, logging {hours} hours. "
                "There were strong moments and quieter ones — both are part of the process."
            ),
            "key_insight": (
                f"A {exec_rate}% completion rate this week. "
                "The gap between what you planned and what you did is information, not a verdict. "
                "Pay attention to which sessions you finished first — that's where your real energy lives."
            ),
            "next_week_nudge": (
                "Next week, pick one focus area and go deeper than usual. "
                "Fewer things, done better, compounds faster than spreading thin."
            ),
        }
    else:
        # Wellness-only: no execution language at all
        energy_desc = "steady" if 4 < avg_energy < 7 else ("strong" if avg_energy >= 7 else "quieter")
        return {
            "week_summary": (
                f"This week you checked in {days_active} out of 7 days — "
                f"a {pct}% habit consistency rate. "
                f"Your energy felt {energy_desc} through the week, and that quieter self-awareness "
                "you've been building is its own kind of progress."
            ),
            "key_insight": (
                "Showing up to check in every day, even when it's just a quick tap, "
                "is a form of accountability most people skip. "
                "That habit of noticing yourself is the foundation everything else builds on."
            ),
            "next_week_nudge": (
                "Next week, pick one habit you want to be non-negotiable — "
                "not because you have to, but because you've seen what consistency feels like. "
                "Even 5 minutes a day on the right thing adds up fast."
            ),
        }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WEEKLY EMAIL
# ─────────────────────────────────────────────────────────────────────────────

def generate_weekly_analytics_html(
    user_name: str,
    analytics: dict,
    user_token: str,
    commitment_stats: dict = None,
    reflection: dict = None,
    user_goal: str = "",
) -> str:
    first_name   = user_name.split()[0]
    pct          = analytics.get("consistency_percentage", 0)
    days_active  = analytics.get("days_logged", 0)
    avg_mood     = round(analytics.get("average_mood", 0), 1)
    avg_energy   = round(analytics.get("average_energy", 0), 1)
    avg_prod     = round(analytics.get("average_productivity", 0), 1)
    exec_rate    = analytics.get("commitment_completion_rate", 0)
    total_mins   = analytics.get("total_work_minutes", 0)
    retro_mins   = analytics.get("retroactive_minutes", 0)
    focus_bd     = analytics.get("focus_area_breakdown", {})
    hours_total  = round(total_mins / 60, 1)

    # Commitment stats — consistent source of truth
    total_planned   = commitment_stats.get("total_planned", 0)   if commitment_stats else 0
    completed_count = commitment_stats.get("completed_count", 0) if commitment_stats else 0
    missed_count    = commitment_stats.get("missed_count", 0)    if commitment_stats else 0
    partial_count   = commitment_stats.get("partial_count", 0)   if commitment_stats else 0
    best_slot       = commitment_stats.get("best_time_slot", "—") if commitment_stats else "—"
    recovery_rate   = commitment_stats.get("recovery_rate_percentage", 0) if commitment_stats else 0

    # Whether this user uses execution features at all
    is_execution_user = total_planned > 0 or retro_mins > 0

    reflection_url  = f"{FRONTEND_URL}/?view=reflection&token={user_token}"
    unsubscribe_url = f"{FRONTEND_URL}/?action=unsubscribe&token={user_token}"

    # ── AI summary ───────────────────────────────────────────────────────────
    ai = _generate_weekly_ai_summary(
        user_name=user_name,
        analytics=analytics,
        commitment_stats=commitment_stats or {},
        reflection=reflection or {},
        user_goal=user_goal,
    )
    week_summary    = ai.get("week_summary", "")
    key_insight     = ai.get("key_insight", "")
    next_week_nudge = ai.get("next_week_nudge", "")

    # ── Focus area bars ──────────────────────────────────────────────────────
    focus_bars_html = ""
    if focus_bd:
        total_focus_mins = sum(focus_bd.values()) or 1
        focus_bars_html = _section_header("Focus Area Breakdown", "🎯")
        for area, mins in sorted(focus_bd.items(), key=lambda x: -x[1])[:5]:
            area_pct = round(mins / total_focus_mins * 100)
            hrs  = mins // 60
            rem  = mins % 60
            t    = (f"{hrs}h " if hrs else "") + (f"{rem}m" if rem else "0m")
            focus_bars_html += (
                f'<div style="margin-bottom:12px;">'
                f'<div style="display:flex;justify-content:space-between;font-size:13px;'
                f'color:#6b7280;margin-bottom:4px;"><span>{area}</span>'
                f'<span style="color:#1a1a2e;font-weight:600;">{t} · {area_pct}%</span></div>'
                + _bar(area_pct, "#7c3aed", "#a78bfa") +
                f'</div>'
            )

    # ── Execution block (only if user has any planned data) ──────────────────
    exec_block_html = ""
    if total_planned > 0:
        exec_block_html = f"""
            {_section_header("Execution Intelligence", "⚡")}
            <table style="width:100%;border-spacing:0;">
                {_stat_row("Total Planned Sessions", str(total_planned))}
                {_stat_row("Completed", str(completed_count), "#059669")}
                {_stat_row("Partial", str(partial_count), "#d97706")}
                {_stat_row("Missed", str(missed_count), "#dc2626")}
                {_stat_row("Completion Rate", f"{exec_rate}%", "#7c3aed")}
                {_stat_row("Total Work Logged", f"{hours_total}h")}
                {_stat_row("Best Time Slot", best_slot)}
                {_stat_row("Recovery Rate", f"{recovery_rate}%", "#0891b2")}
            </table>
            <p style="font-size:11px;color:#9ca3af;margin:6px 0 0;">
                * Partial sessions are counted separately.
                Total Planned = Completed + Partial + Missed + any still-pending.
            </p>
        """

    # ── Reflection callout ────────────────────────────────────────────────────
    reflection_callout = ""
    if reflection:
        pm = reflection.get("proud_moment", "")
        ww = reflection.get("what_went_well", "")
        if pm and str(pm).strip() not in ("", "not filled", "None"):
            reflection_callout = f"""
            <div style="border-left:4px solid #7c3aed;padding:12px 16px;
                        background:#f5f3ff;border-radius:0 8px 8px 0;margin:0 0 24px;">
                <p style="margin:0 0 4px;font-size:10px;font-weight:700;letter-spacing:1.5px;
                           text-transform:uppercase;color:#7c3aed;">Your Proud Moment This Week</p>
                <p style="margin:0;font-size:14px;color:#374151;line-height:1.6;font-style:italic;">
                    "{pm}"
                </p>
            </div>"""
        elif ww and str(ww).strip() not in ("", "not filled", "None"):
            reflection_callout = f"""
            <div style="border-left:4px solid #059669;padding:12px 16px;
                        background:#f0fdf4;border-radius:0 8px 8px 0;margin:0 0 24px;">
                <p style="margin:0 0 4px;font-size:10px;font-weight:700;letter-spacing:1.5px;
                           text-transform:uppercase;color:#059669;">What Went Well</p>
                <p style="margin:0;font-size:14px;color:#374151;line-height:1.6;font-style:italic;">
                    "{ww}"
                </p>
            </div>"""

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>Your Weekly Report — Velora</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
<table width="100%" border="0" cellpadding="0" cellspacing="0"
       style="background:#f4f4f8;padding:32px 0;">
    <tr><td align="center" style="padding:0 16px;">
    <table width="100%" border="0" cellpadding="0" cellspacing="0"
           style="max-width:560px;background:#ffffff;border-radius:14px;
                  overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.07);">

        <!-- ── HEADER (dark — safe because it's a table cell, not full body) ── -->
        <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
                        padding:28px 36px 24px;">
                <p style="margin:0 0 6px;color:#a78bfa;font-size:11px;font-weight:700;
                           letter-spacing:2.5px;text-transform:uppercase;
                           font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">Velora</p>
                <p style="margin:0 0 6px;color:#ffffff;font-size:22px;font-weight:700;
                            line-height:1.3;
                            font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
                    Your Weekly Report ✨
                </p>
                <p style="margin:0;color:#9ca3af;font-size:13px;
                           font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
                    7-day snapshot &nbsp;·&nbsp; {days_active} of 7 days active
                </p>
            </td>
        </tr>

        <!-- ── BODY (light — universally safe) ───────────────────────────── -->
        <tr>
            <td style="padding:32px 36px;background:#ffffff;">

                <!-- AI week summary -->
                <p style="font-size:15px;color:#374151;line-height:1.8;margin:0 0 4px;">
                    Hey {first_name},
                </p>
                <p style="font-size:15px;color:#374151;line-height:1.8;margin:0 0 24px;">
                    {week_summary}
                </p>

                <!-- Reflection callout (if available) -->
                {reflection_callout}

                <!-- ── Habit Consistency ── -->
                {_section_header("Habit Consistency", "🌱")}
                {_bar(pct, "#7c3aed", "#a78bfa")}
                <p style="margin:4px 0 20px;font-size:13px;color:#6b7280;">
                    {pct}% &mdash; showed up {days_active} out of 7 days
                </p>

                <!-- ── Execution Rate (only for execution users) ── -->
                {(_section_header("Commitment Execution Rate", "🎯") +
                  _bar(exec_rate, "#059669", "#34d399") +
                  f'<p style="margin:4px 0 20px;font-size:13px;color:#6b7280;">'
                  f'{exec_rate}% of planned sessions completed</p>') if is_execution_user else ""}

                <!-- ── Mental State ── -->
                {_section_header("Mental State Averages", "🧠")}
                <table style="width:100%;border-spacing:0;">
                    {_stat_row("😊 Mood", f"{avg_mood} / 10")}
                    {_stat_row("⚡ Energy", f"{avg_energy} / 10")}
                    {_stat_row("🎯 Productivity", f"{avg_prod} / 10")}
                </table>

                <!-- ── Execution Detail (only for execution users) ── -->
                {('<hr style="border:0;border-top:1px solid #f3f4f6;margin:20px 0;">' + exec_block_html) if is_execution_user and exec_block_html else ""}

                <!-- ── Focus Areas ── -->
                {focus_bars_html}

                <!-- ── AI Key Insight ── -->
                <hr style="border:0;border-top:1px solid #f3f4f6;margin:20px 0;">
                {_section_header("What I Noticed This Week", "🔍")}
                <p style="font-size:15px;color:#374151;line-height:1.8;margin:0 0 20px;">
                    {key_insight}
                </p>

                <!-- ── Next Week intention ── -->
                <div style="background:#f5f3ff;border-radius:10px;padding:18px 20px;
                            border-left:4px solid #7c3aed;margin-bottom:28px;">
                    <p style="margin:0 0 6px;font-size:10px;font-weight:700;
                               letter-spacing:1.5px;text-transform:uppercase;
                               color:#7c3aed;">One Intention For Next Week</p>
                    <p style="margin:0;font-size:15px;color:#1a1a2e;line-height:1.7;">
                        {next_week_nudge}
                    </p>
                </div>

                <!-- ── Reflection CTA ── -->
                <hr style="border:0;border-top:1px solid #f3f4f6;margin:0 0 24px;">
                <p style="font-size:14px;color:#374151;text-align:center;
                           font-weight:600;margin:0 0 6px;">✍️ Lock In Your Weekly Reflection</p>
                <p style="font-size:13px;color:#6b7280;text-align:center;margin:0 0 20px;">
                    60 seconds. Tell your coach what shaped this week
                    so the emails get even better next week.
                </p>
                <div style="text-align:center;">
                    <a href="{reflection_url}"
                       style="background:linear-gradient(135deg,#7c3aed,#5b21b6);
                              color:#ffffff;padding:14px 32px;text-decoration:none;
                              font-weight:700;border-radius:8px;display:inline-block;
                              font-size:15px;">
                        Complete My Weekly Reflection →
                    </a>
                </div>

            </td>
        </tr>

        <!-- ── FOOTER ─────────────────────────────────────────── -->
        <tr>
            <td style="padding:16px 36px;background:#f9fafb;
                        border-top:1px solid #f3f4f6;text-align:center;">
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


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def generate_password_reset_html(user_name: str, reset_link: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f8;
             font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
    <div style="max-width:500px;margin:60px auto;background:#fff;border-radius:12px;
                padding:40px;box-shadow:0 4px 20px rgba(0,0,0,0.06);">
        <p style="margin:0 0 4px;color:#a78bfa;font-size:12px;font-weight:600;
                   letter-spacing:2px;text-transform:uppercase;">Velora</p>
        <h2 style="color:#1a1a2e;margin:8px 0 20px;">Password Reset Request</h2>
        <p style="color:#374151;font-size:15px;line-height:1.6;">
            Hey {user_name}, we received a request to reset your Velora password.
            Click the button below — this link expires in 30 minutes.
        </p>
        <div style="text-align:center;margin:32px 0;">
            <a href="{reset_link}"
               style="background:#7c3aed;color:white;padding:14px 32px;
                      text-decoration:none;font-weight:700;border-radius:8px;
                      display:inline-block;">
                Reset My Password
            </a>
        </div>
        <p style="color:#9ca3af;font-size:13px;">
            If you did not request this, you can safely ignore this email.
        </p>
    </div>
</body>
</html>"""
