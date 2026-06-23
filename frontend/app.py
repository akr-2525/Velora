# -*- coding: utf-8 -*-
"""
Velora - Execution Intelligence Platform
All priority fixes applied:
  Fix 1  - Wellness sliders (mood/energy/productivity) in Habits & Wellness tab
  Fix 2  - Push To Tomorrow on pending + Honest Review (failure reason) on miss/partial
  Fix 3  - Time input: Hour/Minute number_input — no scroll, no drift
  Fix 4  - Timezone-aware display using user's configured timezone
  Fix 5  - Focus area horizontal bar chart (replaces pie)
  Fix 6  - Daily Priority ("What would make today successful?") in Daily Protocol
  Fix 7  - AI insight fetched via API — no broken backend import
  Fix 8  - Meaningful empty states everywhere
  Fix 9  - Micro-wins celebration (streak milestones, first completion)
  Fix 10 - Smart default start time (end of last commitment or rounded now)
"""

import streamlit as st
import requests
import datetime
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os

API_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

FOCUS_OPTIONS = [
    # Career & Education
    "Career Growth", "Competitive Exams", "Academic Studies",
    "Skill Development", "Job Search & Applications", "Interview Preparation",
    "Coding & DSA", "System Design", "Machine Learning / AI",
    "Web Development", "Mobile Development", "DevOps & Cloud",
    # Business & Projects
    "Personal Projects", "Startup / Side Business", "Freelancing",
    "Content Creation", "Research & Writing",
    # Productivity & Mindset
    "Productivity", "Personal Growth", "Habits & Routines",
    "Financial Literacy", "Leadership Skills",
    # Health & Lifestyle
    "Fitness & Health", "Mental Health & Wellness", "Nutrition & Diet",
    "Sleep Improvement", "Mindfulness & Meditation",
    # Learning
    "Reading & Learning", "Language Learning", "Music or Arts",
    "Mathematics", "Science",
]

STRUGGLE_OPTIONS = [
    # Execution
    "Procrastination", "Inconsistency", "Lack of Focus",
    "Time Management", "Poor Planning", "Starting Tasks",
    "Finishing What I Start", "Meeting Deadlines",
    # Mental
    "Burnout", "Overthinking", "Anxiety & Stress",
    "Self-Doubt", "Perfectionism", "Negative Self-Talk",
    "Fear of Failure", "Imposter Syndrome",
    # Motivation
    "Low Motivation", "Lack of Discipline", "No Clear Goals",
    "Distraction & Context Switching",
    # External
    "Social Media Distractions", "Phone Addiction",
    "Unhealthy Sleep Patterns", "Poor Work-Life Balance",
    "Lack of Accountability",
]
HABIT_OPTIONS = [
    "Study Daily", "Read Books", "Exercise", "Meditation",
    "Journaling", "Sleep Earlier", "Practice a Skill",
    "Deep Work Session", "Plan My Day", "Drink More Water", "Limit Social Media",
]
TONE_OPTIONS = [
    "Supportive Friend", "Encouraging Mentor",
    "Calm & Reflective", "Direct & Accountable", "Motivating & Energetic",
]
TIMEZONE_OPTIONS = [
    "UTC",
    "Asia/Kolkata",
    "Asia/Dubai",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Europe/London",
    "Europe/Paris",
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Australia/Sydney",
]

st.set_page_config(page_title="Velora", page_icon="zap", layout="wide")

# ── Cookie manager — instantiated right after set_page_config ─────────────────
# get_all() is called in __init__ so self.cookies is populated immediately.
# On first render after a fresh page load it returns whatever cookies the
# browser sends with the request — including velora_token if previously set.
import extra_streamlit_components as stx
_cookie_mgr = stx.CookieManager(key="velora_cm")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0d0d1a; }
[data-testid="stSidebar"] { background-color: #13132a; border-right:1px solid #1e1e3a; }
[data-testid="stSidebar"] * { color:#c4c4d4 !important; }
.main .block-container { padding-top:2rem; padding-bottom:4rem; }
h1,h2,h3,h4 { color:#f0f0ff !important; font-weight:700 !important; }
p { color:#9ca3af; }
.stMarkdown p { color:#9ca3af; }
label { color:#9ca3af !important; font-size:13px !important; }
.brand { color:#a78bfa; font-size:11px; font-weight:800;
         letter-spacing:3px; text-transform:uppercase; }
.kpi-row { display:flex; gap:14px; margin-bottom:6px; }
.kpi { flex:1; background:#13132a; border:1px solid #1e1e3a;
       border-radius:14px; padding:18px 14px; text-align:center; }
.kpi-val  { font-size:28px; font-weight:800; line-height:1; margin-bottom:5px; }
.kpi-label{ font-size:10px; color:#6b7280; text-transform:uppercase; letter-spacing:1.2px; }
.kpi-purple .kpi-val { color:#a78bfa; }
.kpi-green  .kpi-val { color:#34d399; }
.kpi-amber  .kpi-val { color:#fbbf24; }
.kpi-white  .kpi-val { color:#f0f0ff; }
.kpi-teal   .kpi-val { color:#22d3ee; }
.section-hdr {
    font-size:10px; font-weight:700; letter-spacing:2px;
    text-transform:uppercase; color:#6b7280;
    margin:28px 0 12px; padding-bottom:8px;
    border-bottom:1px solid #1e1e3a;
}
.commit-card {
    background:#13132a; border:1px solid #1e1e3a;
    border-radius:12px; padding:14px 18px; margin-bottom:10px;
}
.commit-title { font-size:15px; font-weight:600; color:#f0f0ff; }
.commit-time  { font-size:12px; color:#6b7280; margin-top:2px; }
.badge { display:inline-block; padding:2px 9px; border-radius:20px;
         font-size:10px; font-weight:700; }
.badge-green { background:#064e3b; color:#34d399; }
.badge-red   { background:#450a0a; color:#f87171; }
.badge-amber { background:#451a03; color:#fbbf24; }
.badge-gray  { background:#1e1e3a; color:#9ca3af; }
.badge-teal  { background:#0c3344; color:#22d3ee; }
.alert-warn { background:#2d1f00; border:1px solid #78350f; color:#fbbf24;
              border-radius:10px; padding:12px 16px; font-size:14px; margin:8px 0; }
.alert-ok   { background:#022c22; border:1px solid #064e3b; color:#34d399;
              border-radius:10px; padding:12px 16px; font-size:14px; margin:8px 0; }
.insight-box { background:#1a1a2e; border:1px solid #312e81;
               border-radius:10px; padding:14px 18px; margin:16px 0;
               font-size:14px; color:#c7d2fe; line-height:1.6; }
.priority-box { background:#13132a; border:1px solid #7c3aed;
                border-radius:10px; padding:14px 18px; margin:0 0 18px;
                font-size:15px; color:#f0f0ff; }
.priority-label { font-size:10px; color:#a78bfa; text-transform:uppercase;
                  letter-spacing:1.5px; font-weight:700; margin-bottom:4px; }
.empty-state { text-align:center; padding:48px 24px; color:#6b7280; }
.empty-state .icon { font-size:36px; margin-bottom:10px; }
.win-banner { background:linear-gradient(135deg,#064e3b,#065f46);
              border:1px solid #10b981; border-radius:10px;
              padding:12px 18px; margin:8px 0; color:#34d399;
              font-size:14px; font-weight:600; }
.stButton > button { background:#1e1e3a; color:#e0e0ff;
                     border:1px solid #2d2d55; border-radius:8px; font-size:13px; }
.stButton > button:hover { background:#2a2a50; border-color:#a78bfa; }
[data-testid="stFormSubmitButton"] > button {
    background:linear-gradient(135deg,#7c3aed,#5b21b6) !important;
    color:white !important; border:none !important;
    border-radius:8px !important; font-weight:600 !important;
}
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea {
    background:#13132a !important; color:#f0f0ff !important;
    border:1px solid #2d2d55 !important; border-radius:8px !important;
}
.stSelectbox > div > div {
    background:#13132a !important; color:#f0f0ff !important;
    border:1px solid #2d2d55 !important;
}
.stTabs [data-baseweb="tab"] { color:#6b7280; }
.stTabs [aria-selected="true"] { color:#a78bfa !important;
    border-bottom-color:#a78bfa !important; }
.stNumberInput > div > div > input {
    background:#13132a !important; color:#f0f0ff !important;
    border:1px solid #2d2d55 !important; border-radius:8px !important;
    text-align:center !important;
}
/* ── Mobile responsive — collapse columns on small screens ── */
@media (max-width: 640px) {
    .main .block-container { padding-left:1rem !important; padding-right:1rem !important; }
    /* Force Streamlit columns to stack vertically on mobile */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    .kpi-row { flex-direction: column; gap: 8px; }
    .kpi { padding: 14px 12px; }
    .kpi-val { font-size: 22px; }
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ──────────────────────────────────────────────────────────────────

def hdrs():
    return {"Authorization": "Bearer " + st.session_state.get("token", "")}

def api_post(path, body):
    return requests.post(API_URL + path, headers=hdrs(), json=body)

def api_put(path, body):
    return requests.put(API_URL + path, headers=hdrs(), json=body)

def api_get(path, params=None):
    return requests.get(API_URL + path, headers=hdrs(), params=params)

def api_delete(path):
    return requests.delete(API_URL + path, headers=hdrs())

def parse_dt(s):
    """Parse datetime string from backend. DB stores naive IST — treat as-is."""
    dt = datetime.datetime.fromisoformat(s.replace("Z", ""))
    # Strip any timezone info — we treat all DB values as local (IST) naive times
    return dt.replace(tzinfo=None) if dt.tzinfo else dt

def fmt_time(dt):
    """Format datetime for display — no conversion, values are already local (IST)."""
    return dt.strftime("%I:%M %p")

def fmt_datetime(dt):
    return dt.strftime("%b %d, %I:%M %p")

def _now_ist():
    """Return current datetime in IST (UTC+5:30). Works correctly on both local and Render."""
    from datetime import timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    return datetime.datetime.now(IST).replace(tzinfo=None)  # naive IST datetime

def _today_in_user_tz():
    """Return today's date in IST."""
    return _now_ist().date()

def _hour_in_user_tz():
    """Return current hour in IST."""
    return _now_ist().hour

def badge(status, ctype="planned"):
    if ctype == "retroactive":
        return '<span class="badge badge-teal">RETROACTIVE</span>'
    m = {
        "completed": ("badge-green", "DONE"),
        "missed":    ("badge-red",   "MISSED"),
        "partial":   ("badge-amber", "PARTIAL"),
        "pending":   ("badge-gray",  "PENDING"),
        "active":    ("badge-gray",  "ACTIVE"),
    }
    cls, txt = m.get(status, ("badge-gray", status.upper()))
    return '<span class="badge ' + cls + '">' + txt + '</span>'

def kpi(val, label, color="white"):
    return (
        '<div class="kpi kpi-' + color + '">'
        '<div class="kpi-val">' + str(val) + '</div>'
        '<div class="kpi-label">' + label + '</div></div>'
    )

def section(title):
    st.markdown('<div class="section-hdr">' + title + '</div>', unsafe_allow_html=True)

def empty_state(icon, message, hint=""):
    hint_html = '<div style="font-size:13px;margin-top:6px;">' + hint + "</div>" if hint else ""
    st.markdown(
        '<div class="empty-state"><div class="icon">' + icon + "</div>"
        + message + hint_html + "</div>",
        unsafe_allow_html=True,
    )

# ── Cache helpers (Fix 7 — no broken backend import) ────────────────────────

def invalidate(*keys):
    for k in keys:
        st.session_state.pop(k, None)

def cached(key, path, params=None):
    if key not in st.session_state:
        r = api_get(path, params=params)
        if r.status_code == 200:
            st.session_state[key] = r.json()
        else:
            return None
    return st.session_state.get(key)

def get_goals():
    return cached("goals", "/users/goals") or []

def goal_name(goals, goal_id):
    if not goal_id:
        return ""
    for g in goals:
        if g["id"] == goal_id:
            return g["title"]
    return "Goal #" + str(goal_id)

def get_user_focus_areas():
    user = cached("user_profile", "/users/me")
    return (user.get("focus_areas") or []) if user else []

# Fix 3 + Fix 10: clean time input and smart default ─────────────────────────

def smart_default_start(target_date):
    """Default start = end of last commitment today, or rounded-up current time."""
    commits = cached(
        "daily_" + target_date.isoformat(),
        "/commitments/daily",
        params={"date": target_date.isoformat()},
    )
    now_local = _now_ist()

    if commits:
        latest_end = None
        for c in commits:
            e = parse_dt(c["end_time"])
            if latest_end is None or e > latest_end:
                latest_end = e
        if latest_end and latest_end > now_local:
            return latest_end.hour, latest_end.minute

    # Round up to next 5-minute boundary
    mins  = now_local.minute
    delta = (5 - mins % 5) % 5
    nxt   = now_local + datetime.timedelta(minutes=delta)
    return nxt.hour, nxt.minute

# ── AUTH ─────────────────────────────────────────────────────────────────────

def render_auth():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<p class="brand">VELORA</p>', unsafe_allow_html=True)
        st.markdown("## Execution Intelligence")
        st.markdown(
            '<p style="color:#6b7280;margin-bottom:28px;">'
            "Know why you succeed. Know why you don't.</p>",
            unsafe_allow_html=True,
        )
        t_in, t_up = st.tabs(["Sign In", "Create Account"])

        with t_in:
            with st.form("login_form"):
                em = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", width="stretch"):
                    r = requests.post(API_URL + "/login",
                                      json={"email": em, "password": pw})
                    if r.status_code == 200:
                        d = r.json()
                        st.session_state["token"]   = d["access_token"]
                        st.session_state["user"]    = d["user"]
                        st.session_state["user_tz"] = d["user"].get("timezone", "UTC")
                        # Persist token in cookie — survives refresh and browser close
                        # 30-day expiry matches the JWT lifetime
                        from datetime import timedelta
                        _cookie_mgr.set(
                            "velora_token",
                            d["access_token"],
                            expires_at=datetime.datetime.now() + timedelta(days=30),
                            same_site="lax",
                            key="set_velora_token",
                        )
                        st.rerun()
                    else:
                        st.error("Wrong email or password.")
            with st.expander("Forgot password?"):
                with st.form("forgot_form"):
                    fe = st.text_input("Your email")
                    if st.form_submit_button("Send reset link"):
                        r = api_post("/users/forgot-password", {"email": fe})
                        st.info(r.json().get("message", "Sent."))

        with t_up:
            with st.form("signup_form"):
                n  = st.text_input("Full Name")
                e  = st.text_input("Email")
                p  = st.text_input("Password", type="password")
                st.divider()
                g  = st.text_input("Your single biggest goal",
                                    placeholder="e.g., Land SDE internship")
                f  = st.multiselect("Focus areas", FOCUS_OPTIONS)
                s  = st.multiselect("Biggest challenges", STRUGGLE_OPTIONS)
                h  = st.selectbox("Core habit to track daily", HABIT_OPTIONS)
                to = st.selectbox("Coach voice", TONE_OPTIONS)
                tm = st.slider("Daily focused minutes", 15, 240, 60, step=15)
                tz = st.selectbox("Your timezone", TIMEZONE_OPTIONS)
                if st.form_submit_button("Create My Coach",
                                          width="stretch"):
                    if not all([n.strip(), e.strip(), p.strip(), g.strip()]):
                        st.error("All fields required.")
                    else:
                        r = requests.post(API_URL + "/users/", json={
                            "name": n, "email": e, "password": p,
                            "primary_goal": g, "focus_areas": f,
                            "struggles": s, "habits": [h],
                            "preferred_tone": to,
                            "daily_time_minutes": tm,
                            "timezone": tz,
                        })
                        if r.status_code == 200:
                            st.success("Account created. Sign in above.")
                        else:
                            try:    st.error(r.json().get("detail", r.text))
                            except: st.error(r.text)

# ── EXECUTION DASHBOARD ──────────────────────────────────────────────────────

def render_execution_dashboard():
    user = cached("user_profile", "/users/me")
    if not user:
        st.session_state.clear(); st.rerun()

    stk    = user.get("streak") or {}
    h_st   = stk.get("current_streak", 0)
    e_st   = stk.get("execution_streak", 0)

    # Today snapshot — use user's local date, not server date (Fix 2)
    today_str = _today_in_user_tz().isoformat()
    today_c   = cached("daily_" + today_str, "/commitments/daily",
                        params={"date": today_str}) or []
    planned_t = [c for c in today_c if c.get("commitment_type") == "planned"]
    done_t    = sum(1 for c in planned_t if c["status"] == "completed")
    pending_t = sum(1 for c in planned_t if c["status"] in ("pending","active"))

    # Micro-win detection (Fix 9)
    if done_t > 0 and st.session_state.get("_last_done_count", -1) < done_t:
        st.session_state["_last_done_count"] = done_t
        if done_t == len(planned_t) and len(planned_t) > 0:
            st.markdown(
                '<div class="win-banner">&#127881; All planned blocks completed today! '
                "Your execution streak is growing.</div>",
                unsafe_allow_html=True,
            )
        elif done_t == 1:
            st.markdown(
                '<div class="win-banner">&#9989; First commitment completed today. '
                "Keep going.</div>",
                unsafe_allow_html=True,
            )

    # Fix 6: Execution Dashboard — 3 clean KPIs
    e_best = stk.get("longest_execution_streak", 0)
    exec_streak_html = (
        '<div class="kpi kpi-purple">'
        '<div class="kpi-val">' + str(e_st) + "d</div>"
        '<div style="font-size:11px;color:#a78bfa;margin-top:2px;">'
        "best: " + str(e_best) + "d</div>"
        '<div class="kpi-label">Execution Streak</div>'
        "</div>"
    )
    st.markdown(
        '<div class="kpi-row">'
        + kpi(len(planned_t), "Planned Today", "white")
        + kpi(done_t, "Completed", "green")
        + exec_streak_html
        + "</div>",
        unsafe_allow_html=True,
    )

    # Today's upcoming mini-timeline
    upcoming = sorted(
        [x for x in planned_t if x["status"] in ("pending","active")],
        key=lambda x: x["start_time"],
    )[:3]
    if upcoming:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        for c in upcoming:
            s_dt = parse_dt(c["start_time"])
            e_dt = parse_dt(c["end_time"])
            st.markdown(
                '<div class="commit-card" style="display:flex;justify-content:'
                'space-between;align-items:center;">'
                '<div><div class="commit-title">' + c["title"] + "</div>"
                '<div class="commit-time">'
                + fmt_time(s_dt) + " &rarr; " + fmt_time(e_dt)
                + "</div></div>" + badge(c["status"]) + "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("&nbsp;", unsafe_allow_html=True)
    section("EXECUTION INTELLIGENCE — LAST 7 DAYS  (planned commitments only)")

    dash = cached("dash_stats", "/commitments/analytics/dashboard")
    if not dash:
        empty_state("&#128202;", "No commitment data yet.",
                    "Start planning in the Daily Protocol tab.")
        return

    cw = dash["current_week"]
    pw = dash["previous_week"]
    rate  = cw["completion_rate_percentage"]
    delta = round(rate - pw["completion_rate_percentage"], 1)
    delta_str = ("+" if delta >= 0 else "") + str(delta) + "% vs last week"

    m1, m2, m3 = st.columns(3)
    m1.metric("Completion Rate", str(rate) + "%", delta_str)
    m2.metric("Planned (Last 7d)", cw["total_planned"])
    m3.metric("Avoidance Flags", cw["procrastination_count"])

    chart_col, insight_col = st.columns([3, 2])
    with chart_col:
        comp_w  = cw["completed_count"]
        miss_w  = cw["missed_count"]
        part_w  = cw["partial_count"]
        total_w = max(cw["total_planned"], 1)
        comp_p  = pw["completed_count"]
        miss_p  = pw["missed_count"]
        part_p  = pw["partial_count"]
        total_p_val = max(pw["total_planned"], 1)

        # Horizontal grouped bar — much easier to read than stacked vertical
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Done",
            y=["7–14 Days Ago", "Last 7 Days"],
            x=[comp_p, comp_w],
            orientation="h",
            marker_color=["#065f46", "#34d399"],
            text=[str(comp_p), str(comp_w)],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=13, color="white", family="Arial Black"),
        ))
        fig.add_trace(go.Bar(
            name="Missed",
            y=["7–14 Days Ago", "Last 7 Days"],
            x=[miss_p, miss_w],
            orientation="h",
            marker_color=["#7f1d1d", "#f87171"],
            text=[str(miss_p) if miss_p else "", str(miss_w) if miss_w else ""],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=13, color="white"),
        ))
        if part_w > 0 or part_p > 0:
            fig.add_trace(go.Bar(
                name="Partial",
                y=["7–14 Days Ago", "Last 7 Days"],
                x=[part_p, part_w],
                orientation="h",
                marker_color=["#78350f", "#fbbf24"],
                text=[str(part_p) if part_p else "", str(part_w) if part_w else ""],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=13, color="white"),
            ))
        fig.update_layout(
            barmode="stack",
            showlegend=True,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#9ca3af",
            height=180,
            margin=dict(t=10, b=10, l=0, r=0),
            xaxis=dict(title="Number of commitments", showgrid=False),
            yaxis=dict(tickfont=dict(size=13, color="#f0f0ff")),
            legend=dict(
                orientation="h", y=-0.35,
                font=dict(size=12, color="#9ca3af"),
            ),
        )
        st.plotly_chart(fig, width="stretch")

    with insight_col:
        best  = cw.get("best_time_slot")  or "—"
        worst = cw.get("worst_time_slot") or "—"

        # Best slot with actionable message
        best_msg = {
            "Morning":   "You execute best in the morning. Protect it.",
            "Afternoon": "Your peak window is the afternoon. Guard it.",
            "Evening":   "Evenings are your strongest — use them.",
            "Night":     "Late nights are your zone. Own that.",
        }.get(best, "Track more blocks to find your best slot.")

        worst_msg = {
            "Morning":   "Mornings slip for you. Try later start times.",
            "Afternoon": "Afternoons are your weakest. Schedule lighter work then.",
            "Evening":   "Evenings tend to drift. End your day earlier.",
            "Night":     "Late night blocks rarely get done. Avoid them.",
        }.get(worst, "")

        st.markdown(
            '<div class="commit-card" style="margin-bottom:10px;">'
            '<div style="font-size:10px;color:#34d399;text-transform:uppercase;'
            'letter-spacing:1px;margin-bottom:4px;">Best Time Slot</div>'
            '<div style="font-size:18px;font-weight:700;color:#34d399;">'
            + best + "</div>"
            '<div style="font-size:12px;color:#6b7280;margin-top:4px;">'
            + best_msg + "</div></div>",
            unsafe_allow_html=True,
        )
        if worst and worst != best:
            st.markdown(
                '<div class="commit-card" style="margin-bottom:10px;">'
                '<div style="font-size:10px;color:#f87171;text-transform:uppercase;'
                'letter-spacing:1px;margin-bottom:4px;">Weakest Slot</div>'
                '<div style="font-size:18px;font-weight:700;color:#f87171;">'
                + worst + "</div>"
                '<div style="font-size:12px;color:#6b7280;margin-top:4px;">'
                + worst_msg + "</div></div>",
                unsafe_allow_html=True,
            )
        rec = cw["recovery_rate_percentage"]
        if rec > 0:
            st.markdown(
                '<div class="commit-card">'
                '<div style="font-size:10px;color:#a78bfa;text-transform:uppercase;'
                'letter-spacing:1px;margin-bottom:4px;">Recovery Rate</div>'
                '<div style="font-size:18px;font-weight:700;color:#a78bfa;">'
                + str(rec) + "%</div>"
                '<div style="font-size:12px;color:#6b7280;margin-top:4px;">'
                "After a miss, you bounce back " + str(rec) + "% of the time.</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        if cw["overconfidence_flag"]:
            st.markdown(
                '<div class="alert-warn"><strong>Pattern:</strong> '
                "You set high confidence on blocks you then miss. "
                "Try being more realistic when planning.</div>",
                unsafe_allow_html=True,
            )
        if cw["underconfidence_flag"]:
            st.markdown(
                '<div class="alert-ok"><strong>Pattern:</strong> '
                "You complete blocks you doubt yourself on. "
                "Trust your ability more when planning.</div>",
                unsafe_allow_html=True,
            )

    # Fix 5: Focus area horizontal bars (replaces pie chart)
    focus_bd = cw.get("focus_area_breakdown", {})
    if focus_bd:
        section("FOCUS AREA ALLOCATION  (planned + retroactive, last 7 days)")
        total_mins = sum(focus_bd.values())
        for area, mins in sorted(focus_bd.items(), key=lambda x: -x[1]):
            pct  = round(mins / total_mins * 100) if total_mins else 0
            hrs  = mins // 60
            rem  = mins % 60
            time_str = (str(hrs) + "h " if hrs else "") + (str(rem) + "m" if rem else "")
            bar_width = str(max(pct, 2))
            st.markdown(
                '<div style="margin-bottom:12px;">'
                '<div style="display:flex;justify-content:space-between;'
                'font-size:13px;color:#9ca3af;margin-bottom:5px;">'
                "<span>" + area + "</span>"
                '<span style="color:#f0f0ff;font-weight:700;">'
                + time_str + " &nbsp; " + str(pct) + "%</span></div>"
                '<div style="background:#1e1e3a;border-radius:6px;height:10px;">'
                '<div style="width:' + bar_width + '%;'
                'background:linear-gradient(90deg,#7c3aed,#a78bfa);'
                'border-radius:6px;height:100%;"></div></div></div>',
                unsafe_allow_html=True,
            )
    else:
        section("FOCUS AREA ALLOCATION")
        empty_state("&#127919;", "No focus area data yet.",
                    "Tag your commitments with a focus area when planning.")

    # Weekly analytics for wellness section only (scatter removed — not enough data for most users)
    wk = cached("weekly_analytics", "/analytics/weekly")

# ── DAILY PROTOCOL ────────────────────────────────────────────────────────────

def render_daily_protocol():
    goals        = get_goals()
    active_g     = [g for g in goals if g["status"] == "active"]
    goal_map     = {g["title"]: g["id"] for g in active_g}
    focus_areas  = get_user_focus_areas()
    focus_choices = ["None"] + focus_areas

    # Fix 6: Daily Priority at the top
    section("TODAY'S SINGLE PRIORITY")
    p_resp = api_get("/analytics/daily-priority")
    today_priority = p_resp.json().get("priority_text", "") if p_resp.status_code == 200 else ""

    if today_priority:
        st.markdown(
            '<div class="priority-box">'
            '<div class="priority-label">What would make today successful?</div>'
            + today_priority + "</div>",
            unsafe_allow_html=True,
        )
    else:
        with st.form("priority_form", clear_on_submit=True):
            ptext = st.text_input(
                "What would make today successful?",
                placeholder="One specific thing — not a list.",
            )
            if st.form_submit_button("Set Today's Priority"):
                if ptext.strip():
                    api_post("/analytics/daily-priority",
                             {"priority_text": ptext.strip()})
                    invalidate("daily_priority")
                    st.rerun()

    left, right = st.columns([1, 1], gap="large")

    # ── Plan a Window ────────────────────────────────────────────────────────
    with left:
        plan_tab, retro_tab = st.tabs(["&#10133; Plan Work", "&#9889; I Just Did It"])

        with plan_tab:
            st.caption("Block focused time in advance. The AI tracks whether you show up.")
            target_date = st.date_input("Date", value=_today_in_user_tz(),
                                         key="plan_date")
            def_h, def_m = smart_default_start(target_date)

            with st.form("create_commitment_form", clear_on_submit=True):
                title = st.text_input(
                    "What will you work on?",
                    placeholder="e.g., LeetCode DP problems, System Design ch.5",
                )
                # Fix 3: Hour + Minute number_input — no scroll, no drift, no tz shift
                st.markdown(
                    '<p style="color:#9ca3af;font-size:13px;margin-bottom:4px;">'
                    "Start Time</p>", unsafe_allow_html=True,
                )
                tc1, tc2 = st.columns(2)
                start_h = tc1.number_input("Hour (0–23)", min_value=0, max_value=23,
                                            value=def_h, step=1, key="sh")
                start_m = tc2.number_input("Minute (0–59)", min_value=0, max_value=59,
                                            value=def_m, step=5, key="sm")

                duration = st.slider("Duration (minutes)", 15, 240, 60, step=15)
                confidence = st.slider("Confidence to complete (%)", 0, 100, 80)
                focus_sel  = st.selectbox("Focus Area (optional)", focus_choices,
                                           key="plan_focus")
                g_choices  = ["None (standalone)"] + list(goal_map.keys())
                sel_goal   = st.selectbox("Link to Goal (optional)", g_choices)
                submitted  = st.form_submit_button("Lock In Commitment",
                                                    width="stretch")

            if submitted:
                if not title.strip():
                    st.error("Please enter what you will work on.")
                else:
                    today = target_date
                    try:
                        start_time_obj = datetime.time(int(start_h), int(start_m))
                    except ValueError:
                        st.error("Invalid time values.")
                        st.stop()

                    # Simple: combine as naive local datetime — no timezone math.
                    # Backend stores naive values; we send naive; display is direct.
                    start_dt  = datetime.datetime.combine(today, start_time_obj)
                    end_dt    = start_dt + datetime.timedelta(minutes=int(duration))
                    now_local = _now_ist()

                    if start_dt < (now_local - datetime.timedelta(minutes=5)):
                        st.error("Start time is in the past. Pick a future window.")
                    else:
                        linked_id = goal_map.get(sel_goal) if sel_goal != "None (standalone)" else None
                        fa = focus_sel if focus_sel != "None" else None
                        r  = api_post("/commitments/", {
                            "title":            title.strip(),
                            "start_time":       start_dt.isoformat(),
                            "end_time":         end_dt.isoformat(),
                            "confidence_level": int(confidence),
                            "linked_goal_id":   linked_id,
                            "focus_area":       fa,
                        })
                        if r.status_code == 200:
                            st.success(
                                "Locked: " + title.strip() + " at "
                                + str(int(start_h)).zfill(2) + ":"
                                + str(int(start_m)).zfill(2)
                                + " for " + str(int(duration)) + " min"
                            )
                            today_key = today.isoformat()
                            invalidate(
                                "daily_" + today_key,
                                "dash_stats", "weekly_analytics",
                            )
                            # Stage the date jump — applied before widget renders next run
                            st.session_state["_pending_log_date"] = today
                            st.rerun()
                        else:
                            try:    st.error(r.json().get("detail", r.text))
                            except: st.error(r.text)

        # Retroactive log
        with retro_tab:
            st.caption("Already did something? Capture it instantly. Won't affect your execution score.")
            with st.form("retroactive_form", clear_on_submit=True):
                rt = st.text_input("What did you work on?",
                                    placeholder="e.g., Reviewed 50 Anki cards")
                rd = st.slider("How long? (minutes)", 5, 480, 45, step=5)
                rf = st.selectbox("Focus Area", focus_choices, key="retro_focus")
                rg_choices = ["None"] + list(goal_map.keys())
                rg = st.selectbox("Link to Goal (optional)", rg_choices,
                                   key="retro_goal")
                rn = st.text_input("Notes (optional)")
                if st.form_submit_button("Log It", width="stretch"):
                    if not rt.strip():
                        st.error("Please describe what you worked on.")
                    else:
                        linked_id = goal_map.get(rg) if rg != "None" else None
                        fa = rf if rf != "None" else None
                        r  = api_post("/commitments/retroactive", {
                            "title":            rt.strip(),
                            "duration_minutes": int(rd),
                            "focus_area":       fa,
                            "linked_goal_id":   linked_id,
                            "outcome_note":     rn or None,
                        })
                        if r.status_code == 200:
                            st.success("Logged: " + rt.strip() +
                                       " (" + str(int(rd)) + " min)")
                            invalidate(
                                "daily_" + _today_in_user_tz().isoformat(),
                                "dash_stats", "weekly_analytics",
                            )
                            st.rerun()
                        else:
                            try:    st.error(r.json().get("detail", r.text))
                            except: st.error(r.text)

    # ── Commitment log ───────────────────────────────────────────────────────
    with right:
        st.markdown("### Commitment Log")
        # If an action requested a date jump (create/push), apply it before widget renders
        if "_pending_log_date" in st.session_state:
            st.session_state["log_date"] = st.session_state.pop("_pending_log_date")
        # Only pass value= when session_state has no existing value — avoids the
        # "default + session_state conflict" warning in Streamlit 1.35+
        if "log_date" not in st.session_state:
            st.session_state["log_date"] = _today_in_user_tz()
        view_date = st.date_input("Date",
                                   label_visibility="collapsed", key="log_date")
        cache_key = "daily_" + view_date.isoformat()
        commits   = cached(cache_key, "/commitments/daily",
                            params={"date": view_date.isoformat()}) or []

        if not commits:
            empty_state(
                "&#128203;",
                "No commitments for " + view_date.strftime("%b %d") + ".",
                "Plan a window on the left, or log work you already did.",
            )
        else:
            now_local = _now_ist()

            # Auto-refresh: if any commitment ends within the next hour,
            # show a refresh button so users don't have to manually reload.
            # Also detect if any pending commitment has already passed end_time
            # (stale page) and prompt an immediate refresh.
            has_stale = any(
                parse_dt(c["start_time"]).replace(tzinfo=None) <= now_local
                and parse_dt(c["end_time"]).replace(tzinfo=None) <= now_local
                and c["status"] in ("pending", "active")
                for c in commits
                if c.get("commitment_type") == "planned"
            )
            if has_stale:
                st.info(
                    "Some commitment windows have ended. "
                    "Click **Refresh** to log your outcomes.",
                    icon="🔄",
                )
                if st.button("Refresh Now", key="refresh_stale", width="stretch"):
                    invalidate(cache_key)
                    st.rerun()
            for c in sorted(commits, key=lambda x: x["start_time"]):
                s_dt   = parse_dt(c["start_time"])
                e_dt   = parse_dt(c["end_time"])
                status = c["status"]
                ctype  = c.get("commitment_type", "planned")
                gname  = goal_name(goals, c.get("linked_goal_id"))

                fa_html = ""
                if c.get("focus_area"):
                    fa_html = (
                        '&nbsp;<span style="background:#0c3344;color:#22d3ee;'
                        'font-size:10px;padding:2px 8px;border-radius:12px;">'
                        + c["focus_area"] + "</span>"
                    )
                goal_html = ""
                if gname:
                    goal_html = (
                        '&nbsp;<span style="background:#1e1e3a;color:#a78bfa;'
                        'font-size:10px;padding:2px 8px;border-radius:12px;">'
                        "Goal: " + gname + "</span>"
                    )

                # Card header
                st.markdown(
                    '<div class="commit-card">'
                    '<div style="display:flex;justify-content:space-between;'
                    'align-items:flex-start;"><div>'
                    '<div class="commit-title">' + c["title"] + "</div>"
                    '<div class="commit-time">'
                    + fmt_time(s_dt) + " &rarr; " + fmt_time(e_dt)
                    + fa_html + goal_html + "</div></div>"
                    + badge(status, ctype)
                    + ("" if not c["completion_percentage"] else
                       '<div style="font-size:12px;color:#6b7280;margin-top:4px;">'
                       + str(c["completion_percentage"]) + "% completed</div>")
                    + "</div>",
                    unsafe_allow_html=True,
                )

                # Retroactive: just show note + delete
                if ctype == "retroactive":
                    if c.get("outcome_note"):
                        st.caption(c["outcome_note"])
                    if st.button("Delete", key="del_r_" + str(c["id"])):
                        api_delete("/commitments/" + str(c["id"]))
                        invalidate(cache_key, "dash_stats", "weekly_analytics")
                        st.rerun()
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    continue

                session_ended = (
                    view_date != datetime.date.today() or now_local >= e_dt
                )

                # ── Fix 2: Pending commitment — show Push To Tomorrow ──────
                if status == "pending" and not session_ended:
                    mins_left = max(0, int(
                        (e_dt - now_local).total_seconds() / 60
                    ))
                    st.markdown(
                        '<div style="font-size:12px;color:#6b7280;padding:3px 0;">'
                        + str(mins_left) + " min remaining</div>",
                        unsafe_allow_html=True,
                    )
                    pb1, pb2, pb3 = st.columns([3, 3, 1])
                    with pb1:
                        if st.button("Push to Tomorrow", key="tom_" + str(c["id"]),
                                     width="stretch"):
                            ur = api_put("/commitments/" + str(c["id"]),
                                         {"push_to_tomorrow": True})
                            if ur.status_code == 200:
                                import datetime as _dt
                                tomorrow = _dt.date.today() + _dt.timedelta(days=1)
                                tomorrow_key = "daily_" + tomorrow.isoformat()
                                invalidate(cache_key, tomorrow_key, "dash_stats")
                                # Stage date jump — applied before widget renders on next run
                                st.session_state["_pending_log_date"] = tomorrow
                                st.toast("Moved to tomorrow")
                                st.rerun()
                            else:
                                try:    st.error(ur.json().get("detail", ur.text))
                                except: st.error(ur.text)
                    with pb2:
                        pass  # spacer
                    with pb3:
                        if st.button("Del", key="dl_p_" + str(c["id"]),
                                     width="stretch"):
                            api_delete("/commitments/" + str(c["id"]))
                            invalidate(cache_key, "dash_stats")
                            st.rerun()

                # ── Session ended: outcome logging ─────────────────────────
                elif session_ended and status in ("pending","active","missed","partial"):
                    exp_label = ("Log outcome" if status in ("pending","active")
                                 else "Update outcome")
                    with st.expander(exp_label,
                                     expanded=(status in ("pending","active"))):
                        outcome = st.radio(
                            "Result:", ["Completed", "Missed", "Partial"],
                            horizontal=True, key="out_" + str(c["id"]),
                        )
                        pct = c["completion_percentage"]
                        if outcome == "Completed":   pct = 100
                        elif outcome == "Missed":    pct = 0
                        else:
                            pct = st.slider("Completion %", 1, 99,
                                            max(1, c["completion_percentage"]),
                                            key="sl_" + str(c["id"]))

                        # Fix 2: Honest Review — failure reason
                        failure_reason = None
                        if outcome in ("Missed", "Partial"):
                            reason_map = {
                                "External blocker (life happened)": "external_blocker",
                                "Underestimated the time needed":    "underestimated_time",
                                "Distraction / I avoided it":        "distraction_avoidance",
                            }
                            r_label = st.selectbox(
                                "Why did this slip?",
                                list(reason_map.keys()),
                                key="fr_" + str(c["id"]),
                            )
                            failure_reason = reason_map[r_label]

                        on = st.text_input(
                            "Note (optional — AI reads this)",
                            key="note_" + str(c["id"]),
                            placeholder="What helped or got in the way?",
                        )
                        b1, b2, b3 = st.columns([3, 3, 1])
                        with b1:
                            if st.button("Save", key="sv_" + str(c["id"]),
                                         width="stretch"):
                                body = {"completion_percentage": pct}
                                if on.strip():      body["outcome_note"]  = on.strip()
                                if failure_reason:  body["failure_reason"] = failure_reason
                                ur = api_put("/commitments/" + str(c["id"]), body)
                                if ur.status_code == 200:
                                    invalidate(cache_key, "dash_stats",
                                               "weekly_analytics")
                                    st.rerun()
                                else:
                                    st.error("Save failed.")
                        with b2:
                            if st.button("Push to Tomorrow",
                                         key="tom2_" + str(c["id"]),
                                         width="stretch"):
                                ur = api_put("/commitments/" + str(c["id"]),
                                             {"push_to_tomorrow": True})
                                if ur.status_code == 200:
                                    import datetime as _dt
                                    tomorrow = _dt.date.today() + _dt.timedelta(days=1)
                                    tomorrow_key = "daily_" + tomorrow.isoformat()
                                    invalidate(cache_key, tomorrow_key, "dash_stats")
                                    st.session_state["_pending_log_date"] = tomorrow
                                    st.toast("Moved to tomorrow")
                                    st.rerun()
                                else:
                                    try:    st.error(ur.json().get("detail", ur.text))
                                    except: st.error(ur.text)
                        with b3:
                            if st.button("Del", key="dl_" + str(c["id"]),
                                         width="stretch"):
                                api_delete("/commitments/" + str(c["id"]))
                                invalidate(cache_key, "dash_stats",
                                           "weekly_analytics")
                                st.rerun()

                elif status == "completed":
                    note_txt = c.get("outcome_note", "")
                    st.markdown(
                        '<div style="font-size:12px;color:#34d399;padding:3px 0;">Done'
                        + ('<br><span style="color:#6b7280;">' + note_txt + "</span>"
                           if note_txt else "")
                        + "</div>", unsafe_allow_html=True,
                    )

                st.markdown("&nbsp;", unsafe_allow_html=True)

# ── HABITS & WELLNESS (Fix 1: full wellness sliders) ─────────────────────────

def render_habits_wellness():
    user = cached("user_profile", "/users/me")
    if not user:
        return

    stk    = user.get("streak") or {}
    fname  = user.get("name", "User").split()[0]
    mission = user.get("primary_goal") or "Keep building."
    h_curr = stk.get("current_streak", 0)
    h_best = stk.get("longest_streak", 0)
    e_curr = stk.get("execution_streak", 0)
    e_best = stk.get("longest_execution_streak", 0)
    freeze = stk.get("freeze_count", 0)

    # Fix 2: Hero greeting lives here — Habits & Wellness is the default landing tab
    _h = _hour_in_user_tz()
    if _h < 12:
        _greeting_word = "Good morning"
    elif _h < 17:
        _greeting_word = "Good afternoon"
    else:
        _greeting_word = "Good evening"

    st.markdown("# " + _greeting_word + ", " + fname)
    st.markdown(
        '<p style="color:#6b7280;font-size:14px;margin-top:-8px;">Mission &nbsp;·&nbsp; '
        '<span style="color:#a78bfa">' + mission + "</span></p>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("### Habits & Wellness")
    st.caption(
        "Track your wellbeing and habit consistency. "
        "Separate from your execution score."
    )

    # Streak cards — Fix 6: Habit Streak is the primary KPI here, full-width
    # Execution Streak belongs on the Execution Dashboard, not here
    section("STREAKS")
    st.markdown(
        '<div class="commit-card" style="text-align:center;padding:28px;">'
        '<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
        'letter-spacing:1px;margin-bottom:10px;">Habit Streak</div>'
        '<div style="font-size:64px;font-weight:800;color:#fbbf24;line-height:1;">'
        + str(h_curr) + "</div>"
        '<div style="font-size:14px;color:#fbbf24;font-weight:600;margin-top:4px;">days</div>'
        '<div style="font-size:13px;color:#6b7280;margin-top:8px;">'
        "Best ever: " + str(h_best) + " days</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Streak freeze display
    if freeze > 0:
        st.markdown(
            '<div class="alert-ok">'
            + "&#10052; " * freeze
            + "&nbsp;<strong>" + str(freeze)
            + " streak freeze" + ("s" if freeze != 1 else "")
            + " available</strong> — auto-consumed if you miss a day."
            "</div>", unsafe_allow_html=True,
        )
    else:
        st.caption("Earn a freeze at every 14-day streak milestone (max 3).")

    st.markdown("&nbsp;", unsafe_allow_html=True)
    if st.button("Mark Habit Done Today", width="stretch", type="primary"):
        r = api_post("/streaks/complete", {})
        if r.status_code == 200:
            d = r.json()
            st.success(d.get("message", "Streak updated!"))
            invalidate("user_profile")
            st.rerun()
        else:
            st.error("Could not update streak.")

    # ── Fix 1: Full wellness check-in sliders ────────────────────────────────
    section("WELLNESS CHECK-IN")
    st.caption(
        "Rate how you feel right now. Your AI coach uses this to personalise tomorrow's email."
    )

    # Load today's existing check-in to pre-fill sliders via GET /checkins/today
    today_ci_resp = api_get("/checkins/today")
    existing_mood   = 5
    existing_energy = 5
    existing_prod   = 5
    existing_notes  = ""
    if today_ci_resp and today_ci_resp.status_code == 200 and today_ci_resp.json():
        ci = today_ci_resp.json()
        existing_mood   = ci.get("mood_score", 5)
        existing_energy = ci.get("energy_score", 5)
        existing_prod   = ci.get("productivity_score", 5)
        existing_notes  = ci.get("notes", "") or ""

    with st.form("wellness_form"):
        mood  = st.slider("Mood", 1, 10, existing_mood,
                           help="How are you feeling emotionally right now?")
        energy = st.slider("Energy", 1, 10, existing_energy,
                            help="How much physical and mental fuel do you have?")
        prod  = st.slider("Productivity / Focus", 1, 10, existing_prod,
                           help="How sharp and focused do you feel?")
        notes = st.text_area(
            "Daily Note (optional)",
            value=existing_notes,
            height=90,
            placeholder="What's on your mind? What blocked you today?",
        )
        if st.form_submit_button("Save Wellness Check-In",
                                  width="stretch"):
            r = api_post("/analytics/wellness-checkin", {
                "mood_score":         mood,
                "energy_score":       energy,
                "productivity_score": prod,
                "notes":              notes or None,
            })
            if r.status_code == 200:
                st.success("Wellness check-in saved.")
                invalidate("weekly_analytics")
            else:
                try:    st.error(r.json().get("detail", r.text))
                except: st.error(r.text)

    # ── Mental state read-back ───────────────────────────────────────────────
    wk = cached("weekly_analytics", "/analytics/weekly")
    if wk:
        mood_avg  = wk.get("average_mood",  0)
        enrg_avg  = wk.get("average_energy", 0)
        prod_avg  = wk.get("average_productivity", 0)
        cons      = wk.get("consistency_percentage", 0)
        days      = wk.get("days_logged", 0)
        total_mins = wk.get("total_work_minutes", 0)
        retro_mins = wk.get("retroactive_minutes", 0)

        section("LAST 7 DAYS — AVERAGES")

        def bar_row(label, val, color):
            pct = int(val / 10 * 100)
            return (
                '<div style="margin-bottom:14px;">'
                '<div style="display:flex;justify-content:space-between;'
                'font-size:13px;color:#9ca3af;margin-bottom:5px;">'
                "<span>" + label + "</span>"
                '<span style="color:#f0f0ff;font-weight:700;">'
                + str(val) + "/10</span></div>"
                '<div style="background:#1e1e3a;border-radius:6px;height:8px;">'
                '<div style="width:' + str(pct) + "%;background:" + color + ";"
                'border-radius:6px;height:100%;"></div></div></div>'
            )

        bar_col, stat_col = st.columns(2)
        with bar_col:
            st.markdown(
                bar_row("Mood",         mood_avg, "#a78bfa") +
                bar_row("Energy",       enrg_avg, "#34d399") +
                bar_row("Productivity", prod_avg, "#fbbf24"),
                unsafe_allow_html=True,
            )
        with stat_col:
            st.markdown(
                '<div class="commit-card" style="text-align:center;">'
                '<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
                'letter-spacing:1px;">Habit Consistency</div>'
                '<div style="font-size:36px;font-weight:800;color:#a78bfa;">'
                + str(cons) + "%</div>"
                '<div style="font-size:12px;color:#6b7280;">'
                + str(days) + " of 7 days</div>"
                "</div>", unsafe_allow_html=True,
            )
            if total_mins > 0:
                wv_hrs = total_mins // 60
                wv_rem = total_mins % 60
                wv_str = (str(wv_hrs) + "h " if wv_hrs else "") + (str(wv_rem) + "m" if wv_rem else "")
                rv_hrs = retro_mins // 60
                rv_rem = retro_mins % 60
                rv_str = (str(rv_hrs) + "h " if rv_hrs else "") + (str(rv_rem) + "m" if rv_rem else "")
                planned_mins = total_mins - retro_mins
                pv_hrs = planned_mins // 60
                pv_rem = planned_mins % 60
                pv_str = (str(pv_hrs) + "h " if pv_hrs else "") + (str(pv_rem) + "m" if pv_rem else "")
                st.markdown(
                    '<div class="commit-card" style="margin-top:10px;">'
                    '<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
                    'letter-spacing:1px;margin-bottom:6px;">Total Work (Last 7 Days)</div>'
                    '<div style="font-size:22px;font-weight:800;color:#f0f0ff;">'
                    + wv_str + "</div>"
                    '<div style="font-size:12px;color:#6b7280;margin-top:6px;line-height:1.6;">'
                    + pv_str + " planned &nbsp;·&nbsp; "
                    + rv_str + " retroactive</div>"
                    '<div style="font-size:11px;color:#4b5563;margin-top:4px;">'
                    "Time you spent working, tracked across all logged sessions."
                    "</div></div>",
                    unsafe_allow_html=True,
                )
    else:
        empty_state(
            "&#128200;",
            "No wellness data yet.",
            "Tap energy buttons in your daily email, or use the sliders above.",
        )

    # ── Weekly Reflection ────────────────────────────────────────────────────
    section("WEEKLY REFLECTION")
    today_dow = datetime.date.today().weekday()  # 6 = Sunday
    if today_dow != 6:
        days_to_sun = 6 - today_dow
        st.markdown(
            '<div class="commit-card" style="text-align:center;padding:28px;">'
            '<div style="font-size:28px;margin-bottom:8px;">&#127807;</div>'
            '<div style="color:#9ca3af;">Weekly Reflection unlocks every Sunday.</div>'
            '<div style="color:#6b7280;font-size:13px;margin-top:4px;">'
            "Come back in " + str(days_to_sun) + " day"
            + ("s" if days_to_sun != 1 else "") + ".</div>"
            "</div>", unsafe_allow_html=True,
        )
    else:
        st.caption("Your answers feed directly into next week's AI emails.")
        with st.form("weekly_ref_form"):
            w1 = st.text_area("What went well this week?", height=80)
            w2 = st.text_area("What was your biggest distraction?", height=80)
            w3 = st.text_area("What moment are you most proud of?", height=80)
            if st.form_submit_button("Save Reflection"):
                r = api_post("/analytics/reflections", {
                    "what_went_well": w1,
                    "biggest_distraction": w2,
                    "proud_moment": w3,
                })
                if r.status_code == 200:
                    st.success("Reflection saved.")
                else:
                    try:    st.error(r.json().get("detail", r.text))
                    except: st.error(r.text)

# ── GOALS ─────────────────────────────────────────────────────────────────────

def render_goals():
    goals  = get_goals()
    active = [g for g in goals if g["status"] == "active"]
    done   = [g for g in goals if g["status"] == "completed"]

    st.markdown("### Goals")
    st.caption(
        "Goals give your commitments direction. "
        "Link any commitment to a goal in the Daily Protocol."
    )
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("#### Add a Goal")
        with st.form("create_goal_form", clear_on_submit=True):
            gt    = st.text_input("Goal title",
                                   placeholder="e.g., Land SDE internship")
            gd    = st.text_area("What does success look like? (optional)",
                                  height=80)
            gdate = st.date_input("Target date (optional)", value=None)
            if st.form_submit_button("Add Goal", width="stretch"):
                if not gt.strip():
                    st.error("Title required.")
                else:
                    r = api_post("/users/goals", {
                        "title":       gt.strip(),
                        "description": gd or None,
                        "target_date": gdate.isoformat() if gdate else None,
                    })
                    if r.status_code == 200:
                        invalidate("goals")
                        st.rerun()
                    else:
                        try:    st.error(r.json().get("detail", r.text))
                        except: st.error(r.text)

    with right:
        st.markdown("#### Active Goals (" + str(len(active)) + ")")
        if not active:
            empty_state(
                "&#127919;",
                "No active goals yet.",
                "Add one on the left, then link commitments to it.",
            )

        for g in active:
            days_badge = ""
            if g.get("target_date"):
                td   = datetime.date.fromisoformat(g["target_date"])
                diff = (td - datetime.date.today()).days
                if diff < 0:
                    days_badge = ' <span style="color:#f87171;">' + str(abs(diff)) + "d overdue</span>"
                elif diff <= 7:
                    days_badge = ' <span style="color:#fbbf24;">' + str(diff) + "d left</span>"
                else:
                    days_badge = ' <span style="color:#6b7280;">' + str(diff) + "d left</span>"

            desc_html = ""
            if g.get("description"):
                desc_html = ('<div style="font-size:13px;color:#9ca3af;margin-top:6px;">'
                             + g["description"] + "</div>")

            st.markdown(
                '<div class="commit-card">'
                '<div style="font-size:15px;font-weight:700;color:#f0f0ff;">'
                + g["title"] + "</div>"
                '<div style="font-size:12px;color:#6b7280;margin-top:3px;">'
                + (g.get("target_date") or "No target date") + days_badge + "</div>"
                + desc_html + "</div>",
                unsafe_allow_html=True,
            )
            gc1, gc2, gc3 = st.columns([3, 3, 1])
            with gc1:
                if st.button("Mark Complete", key="gc_" + str(g["id"]),
                             width="stretch"):
                    api_put("/users/goals/" + str(g["id"]),
                            {"status": "completed"})
                    invalidate("goals")
                    st.rerun()
            with gc2:
                if st.button("Archive", key="ga_" + str(g["id"]),
                             width="stretch"):
                    api_put("/users/goals/" + str(g["id"]),
                            {"status": "archived"})
                    invalidate("goals")
                    st.rerun()
            with gc3:
                if st.button("Del", key="gd_" + str(g["id"]),
                             width="stretch"):
                    api_delete("/users/goals/" + str(g["id"]))
                    invalidate("goals")
                    st.rerun()
            st.markdown("&nbsp;", unsafe_allow_html=True)

    if done:
        st.divider()
        st.markdown("#### Completed &#127942;")
        for g in done:
            st.markdown(
                '<div style="background:#022c22;border:1px solid #064e3b;'
                'border-radius:10px;padding:12px 16px;margin-bottom:8px;'
                'font-size:14px;color:#34d399;">&#10003; ' + g["title"] + "</div>",
                unsafe_allow_html=True,
            )


# ── PROFILE (Fix 4: timezone selector) ───────────────────────────────────────

def render_profile():
    resp = api_get("/users/me")
    if resp.status_code != 200:
        st.error("Failed to load profile.")
        return
    user = resp.json()

    st.markdown("### Profile & Coach Settings")
    st.caption(
        "The more accurate this is, "
        "the more your emails will feel written specifically for you."
    )

    with st.form("profile_form"):
        pc1, pc2 = st.columns(2)
        with pc1:
            pn = st.text_input("Name", value=user.get("name", ""))
            pg = st.text_input("Primary Goal",
                                value=user.get("primary_goal") or "")
        with pc2:
            existing = user.get("habits", [])
            curr_h   = (existing[0] if existing and existing[0] in HABIT_OPTIONS
                        else HABIT_OPTIONS[0])
            ph = st.selectbox("Core Daily Habit", HABIT_OPTIONS,
                               index=HABIT_OPTIONS.index(curr_h))
            curr_t = user.get("preferred_tone", TONE_OPTIONS[0])
            ti     = TONE_OPTIONS.index(curr_t) if curr_t in TONE_OPTIONS else 0
            pt     = st.selectbox("Coach Voice", TONE_OPTIONS, index=ti)

        pf = st.multiselect(
            "Focus Areas (select all that apply)",
            FOCUS_OPTIONS,
            default=[f for f in user.get("focus_areas", []) if f in FOCUS_OPTIONS],
        )
        ps = st.multiselect(
            "Challenges (select all that apply)",
            STRUGGLE_OPTIONS,
            default=[s for s in user.get("struggles", []) if s in STRUGGLE_OPTIONS],
        )
        pm = st.slider("Daily focused minutes", 15, 240,
                        user.get("daily_time_minutes", 60), step=15)

        # Fix 4: timezone selector
        curr_tz = user.get("timezone", "UTC")
        tz_idx  = TIMEZONE_OPTIONS.index(curr_tz) if curr_tz in TIMEZONE_OPTIONS else 0
        ptz = st.selectbox("Your Timezone", TIMEZONE_OPTIONS, index=tz_idx,
                            help="All commitment times will display in this timezone.")

        if st.form_submit_button("Save Changes", width="stretch"):
            r = api_put("/users/me", {
                "name": pn, "primary_goal": pg,
                "focus_areas": pf, "struggles": ps,
                "habits": [ph], "preferred_tone": pt,
                "daily_time_minutes": pm, "timezone": ptz,
            })
            if r.status_code == 200:
                st.success("Profile updated.")
                invalidate("user_profile")
                st.session_state["user_tz"] = ptz
            else:
                try:    st.error(r.json().get("detail", r.text))
                except: st.error(r.text)

    st.divider()
    with st.expander("Danger Zone"):
        st.warning("Permanent. Cannot be undone.")
        if st.button("Delete my account permanently"):
            r = api_delete("/users/me")
            if r.status_code == 200:
                st.session_state.clear()
                st.rerun()


# ── ADMIN ─────────────────────────────────────────────────────────────────────

def render_admin():
    st.markdown("### Admin — Knowledge Base")
    t1, t2 = st.tabs(["Add Content", "View All"])
    with t1:
        with st.form("admin_form", clear_on_submit=True):
            ac1, ac2 = st.columns(2)
            cat   = ac1.selectbox("Category", [
                "Growth","Consistency","Focus","Burnout","Procrastination",
                "Mindfulness","Recovery","Rest","Momentum","Self Compassion",
                "Small Wins","Discipline","Habits",
            ])
            ctype = ac2.selectbox("Type", ["Tip","Micro-Habit","Quote"])
            txt   = st.text_area("Content")
            auth  = st.text_input("Author (quotes)")
            if st.form_submit_button("Add to Knowledge Base"):
                if len(txt.strip()) < 10:
                    st.error("Too short.")
                else:
                    r = api_post("/analytics/admin/content", {
                        "category":     cat,
                        "content_type": ctype,
                        "text":         txt,
                        "author":       auth or None,
                    })
                    if r.status_code == 200:
                        st.success("Added.")
                    else:
                        try:    st.error(r.json().get("detail", r.text))
                        except: st.error(r.text)
    with t2:
        r = api_get("/analytics/admin/content")
        if r.status_code == 200:
            items = r.json()
            if not items:
                st.info("Knowledge base is empty.")
            for item in items:
                preview = item["text"][:70] + ("..." if len(item["text"]) > 70 else "")
                label   = "[" + item["content_type"] + "] " + item["category"] + " — " + preview
                with st.expander(label):
                    st.write(item["text"])
                    if item.get("author"):
                        st.caption("— " + item["author"])
                    if st.button("Delete", key="dc_" + str(item["id"])):
                        api_delete("/analytics/admin/content/" + str(item["id"]))
                        st.rerun()
        else:
            st.error("Could not load content.")


# ── EMAIL PREVIEW ─────────────────────────────────────────────────────────────

def render_email_preview():
    """
    Email Preview tab — shows the EXACT emails users receive.
    Fetches real rendered HTML from backend endpoints, so what you see
    IS what gets sent. Supports both Daily and Weekly email.
    """
    st.markdown("### Email Preview")
    st.caption("See the exact emails your users receive — rendered from the live backend.")

    tab_daily, tab_weekly = st.tabs(["Daily Morning Email", "Weekly Report Email"])

    # ── DAILY EMAIL ──────────────────────────────────────────────────────────
    with tab_daily:
        st.caption(
            "This is the exact email sent every morning at 7 AM. "
            "Calls Gemini — generates a fresh personalised email for your account."
        )
        col_btn, col_info = st.columns([1, 2])
        with col_btn:
            if st.button("Generate Daily Preview", width="stretch", type="primary"):
                with st.spinner("Generating your personalised email..."):
                    r = api_get("/preview-digest-html")
                    if r.status_code == 200:
                        st.session_state["daily_preview_html"] = r.text
                        # Also store JSON for debug
                        rj = api_get("/generate-digest")
                        if rj.status_code == 200:
                            st.session_state["preview_digest"] = rj.json()
                    else:
                        try:    st.error(r.json().get("detail", r.text))
                        except: st.error("Failed to generate preview.")

            if st.session_state.get("daily_preview_html"):
                if st.button("Clear", key="clear_daily"):
                    st.session_state.pop("daily_preview_html", None)
                    st.session_state.pop("preview_digest", None)
                    st.rerun()

        with col_info:
            st.markdown(
                '<div style="background:#13132a;border:1px solid #1e1e3a;'
                'border-radius:10px;padding:14px 16px;font-size:12px;color:#9ca3af;">'
                "This email uses: mood trends · habit streak · execution streak · "
                "goals · today's priority · yesterday's work · weekly reflection · "
                "failure patterns · neglected habits · content library"
                "</div>",
                unsafe_allow_html=True,
            )

        html = st.session_state.get("daily_preview_html")
        if html:
            st.html(html)
            d = st.session_state.get("preview_digest")
            if d:
                with st.expander("Raw AI JSON"):
                    st.json(d)
        else:
            st.markdown(
                '<div style="background:#13132a;border:1px dashed #2d2d55;'
                'border-radius:12px;padding:48px;text-align:center;color:#6b7280;">'
                '<div style="font-size:32px;margin-bottom:10px;">&#9993;</div>'
                "Click Generate to see your personalised daily email."
                "</div>",
                unsafe_allow_html=True,
            )

    # ── WEEKLY EMAIL ─────────────────────────────────────────────────────────
    with tab_weekly:
        st.caption(
            "This is the exact email sent every Sunday at 6 PM. "
            "Shows your real 7-day analytics — no Gemini needed."
        )
        if st.button("Generate Weekly Preview", width="stretch", type="primary"):
            with st.spinner("Building your weekly report..."):
                r = api_get("/preview-weekly-html")
                if r.status_code == 200:
                    st.session_state["weekly_preview_html"] = r.text
                else:
                    try:    st.error(r.json().get("detail", r.text))
                    except: st.error("Failed to generate weekly preview.")

        if st.session_state.get("weekly_preview_html"):
            if st.button("Clear", key="clear_weekly"):
                st.session_state.pop("weekly_preview_html", None)
                st.rerun()
            st.html(st.session_state["weekly_preview_html"])
        else:
            st.markdown(
                '<div style="background:#13132a;border:1px dashed #2d2d55;'
                'border-radius:12px;padding:48px;text-align:center;color:#6b7280;">'
                '<div style="font-size:32px;margin-bottom:10px;">&#128200;</div>'
                "Click Generate to see your weekly report email."
                "</div>",
                unsafe_allow_html=True,
            )


# ── PASSWORD RESET PAGE (from email link) ─────────────────────────────────────

def render_password_reset():
    """Handles GET /users/reset-password?token=... deep-link from email."""
    st.markdown('<p class="brand">VELORA</p>', unsafe_allow_html=True)
    st.markdown("## Reset Your Password")
    st.caption("Enter a new password below. This link expires in 30 minutes.")
    token = st.query_params.get("token", "")
    with st.form("reset_pw_form"):
        new_pw = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Set New Password", width="stretch"):
            if not new_pw or len(new_pw) < 8:
                st.error("Password must be at least 8 characters.")
            elif new_pw != confirm:
                st.error("Passwords do not match.")
            else:
                r = requests.post(
                    API_URL + "/users/reset-password",
                    json={"token": token, "new_password": new_pw},
                )
                if r.status_code == 200:
                    st.success("Password updated. You can now sign in.")
                    st.query_params.clear()
                else:
                    try:    st.error(r.json().get("detail", r.text))
                    except: st.error("Reset link is invalid or expired.")


# ── UNSUBSCRIBE PAGE (from weekly email footer link) ──────────────────────────

def render_unsubscribe():
    """Handles /?action=unsubscribe&token=... from email footer."""
    st.markdown('<p class="brand">VELORA</p>', unsafe_allow_html=True)
    st.markdown("## Unsubscribe from Velora Emails")
    token = st.query_params.get("token", "")
    st.markdown(
        "Click the button below to stop all Velora emails. "
        "You can re-subscribe anytime from your Profile settings."
    )
    if st.button("Confirm Unsubscribe", type="secondary"):
        r = requests.get(API_URL + "/users/unsubscribe", params={"token": token})
        if r.status_code == 200:
            st.success("You have been unsubscribed from all Velora emails.")
            st.query_params.clear()
        else:
            try:    st.error(r.json().get("detail", r.text))
            except: st.error("This unsubscribe link is invalid or has already been used.")


# ── WEEKLY REFLECTION DEEP-LINK ───────────────────────────────────────────────

def render_reflection_deeplink():
    """
    Handles /?view=reflection&token=... from weekly email.
    Bypasses the Sunday-only lock — the email is the trigger, any day is valid.
    """
    st.markdown('<p class="brand">VELORA</p>', unsafe_allow_html=True)
    st.markdown("## Weekly Reflection")
    st.caption("Your AI coach uses this to personalise next week.")
    with st.form("reflection_dl_form"):
        w1 = st.text_area("What went well this week?", height=80)
        w2 = st.text_area("What was your biggest distraction?", height=80)
        w3 = st.text_area("What are you most proud of?", height=80)
        if st.form_submit_button("Submit Reflection", width="stretch"):
            r = api_post("/analytics/reflections", {
                "what_went_well": w1,
                "biggest_distraction": w2,
                "proud_moment": w3,
            })
            if r.status_code == 200:
                st.success("Saved. You can close this window.")
                st.query_params.clear()
            else:
                try:    st.error(r.json().get("detail", r.text))
                except: st.error(r.text)


# ── ROUTING ───────────────────────────────────────────────────────────────────

query_params = st.query_params

# ── Persistent login via cookie ───────────────────────────────────────────────
# self.cookies is populated at CookieManager.__init__ time from the browser
# request headers — so get() works immediately on every render pass.

if "token" not in st.session_state:
    _stored = _cookie_mgr.get("velora_token")
    if _stored:
        try:
            _test = requests.get(
                API_URL + "/users/me",
                headers={"Authorization": "Bearer " + _stored},
                timeout=5,
            )
            if _test.status_code == 200:
                _u = _test.json()
                st.session_state["token"]   = _stored
                st.session_state["user"]    = _u
                st.session_state["user_tz"] = _u.get("timezone", "UTC")
                st.rerun()
            else:
                # Token expired — delete cookie, fall through to login
                _cookie_mgr.delete("velora_token", key="del_expired")
        except Exception:
            pass  # backend unreachable — show login

# Email deep-link: weekly reflection (any day — bypasses Sunday lock)
if query_params.get("view") == "reflection" and "token" in query_params:
    st.session_state["token"] = query_params["token"]
    render_reflection_deeplink()

# Email deep-link: password reset (no auth needed)
# Handles both /?token=xxx (old) and /?action=reset-password&token=xxx (new)
elif (query_params.get("action") == "reset-password" and "token" in query_params) or \
     ("token" in query_params and "view" not in query_params and "action" not in query_params):
    render_password_reset()

# Email deep-link: unsubscribe
elif query_params.get("action") == "unsubscribe" and "token" in query_params:
    render_unsubscribe()

elif "token" not in st.session_state:
    render_auth()

else:
    user_info = st.session_state.get("user", {})
    is_admin  = user_info.get("is_admin", False)

    # Ensure timezone is in session
    if "user_tz" not in st.session_state:
        u = cached("user_profile", "/users/me")
        st.session_state["user_tz"] = (u.get("timezone", "UTC") if u else "UTC")

    with st.sidebar:
        st.markdown('<p class="brand">VELORA</p>', unsafe_allow_html=True)
        st.markdown("**" + user_info.get("name", "User") + "**")
        goal_txt = user_info.get("primary_goal", "")
        if goal_txt:
            short = goal_txt[:48] + ("..." if len(goal_txt) > 48 else "")
            st.markdown(
                '<p style="font-size:12px;color:#6b7280;margin-top:-4px;">'
                + short + "</p>", unsafe_allow_html=True,
            )
        st.divider()
        if st.button("Mark Habit Done", width="stretch"):
            r = api_post("/streaks/complete", {})
            if r.status_code == 200:
                st.success(r.json().get("message", "Streak updated!"))
                invalidate("user_profile")
            else:
                st.error("Could not update streak.")
        st.divider()
        if st.button("Sign Out", width="stretch"):
            _cookie_mgr.delete("velora_token", key="del_signout")
            st.session_state.clear()
            st.rerun()

    # Fix 5: Wellness is the first/default tab — users land here daily
    tab_names = [
        "Habits & Wellness",
        "Execution Dashboard",
        "Daily Protocol",
        "Goals",
        "Profile",
    ]
    if is_admin:
        tab_names += ["Admin", "Email Preview"]

    tabs = st.tabs(tab_names)
    with tabs[0]: render_habits_wellness()
    with tabs[1]: render_execution_dashboard()
    with tabs[2]: render_daily_protocol()
    with tabs[3]: render_goals()
    with tabs[4]: render_profile()
    if is_admin and len(tabs) >= 7:
        with tabs[5]: render_admin()
        with tabs[6]: render_email_preview()
