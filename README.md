# 🚀 Velora – AI-Powered Execution Intelligence Platform

> **Plan smarter. Execute consistently. Improve continuously.**

Velora is an AI-powered productivity and execution platform that helps users transform intentions into consistent action. Instead of being just another to-do list, Velora analyzes execution patterns, tracks habits, measures productivity, and delivers personalized AI coaching based on real behavioral data.

---

## ✨ Features

### 📅 Smart Commitment Planning
- Create time-blocked commitments
- Schedule planned tasks
- Log retroactive work sessions
- Prevent overlapping commitments
- Link commitments to long-term goals

### 🎯 Goal Management
- Create and manage long-term goals
- Track progress over time
- Connect daily execution with larger objectives

### 🤖 Personalized AI Coaching
- Daily AI-generated productivity digest
- Weekly behavioral insights
- Personalized recommendations
- Context-aware productivity advice
- AI-generated motivational coaching

### 📊 Productivity Analytics
- Completion rate tracking
- Focus area analytics
- Best & worst productivity time slots
- Confidence calibration
- Recovery rate analysis
- Procrastination detection
- Execution streak tracking

### 🧠 Wellness Tracking
- Daily mood tracking
- Energy check-ins
- Productivity score logging
- Personal notes
- Trend visualization

### 🔥 Habit Tracking
- Daily habit completion
- Streak management
- Execution streaks
- Streak freeze support

### 📧 Smart Email System
- Daily productivity digest
- Weekly progress reports
- One-click email actions
- Habit reminders
- Personalized AI summaries

### 🔐 Secure Authentication
- JWT Authentication
- Password hashing
- Session management
- Password reset via email

---

# 🛠 Tech Stack

### Backend
- FastAPI
- SQLAlchemy
- Pydantic
- APScheduler

### Database
- PostgreSQL (Neon)

### Frontend
- Streamlit

### AI
- Google Gemini API

### Authentication
- JWT
- OAuth2
- bcrypt

### Email
- Brevo SMTP

### Deployment
- Render
- Neon PostgreSQL

---

# 🏗 Architecture

```
Streamlit Frontend
        │
        ▼
FastAPI Backend
        │
 ┌──────┴─────────┐
 │                │
 ▼                ▼
Gemini AI    PostgreSQL
        │
        ▼
 Email Scheduler
        │
        ▼
 Daily & Weekly AI Digests
```

---

# 📈 Core Functionalities

- User Authentication
- Goal Management
- Commitment Scheduling
- Habit Tracking
- Daily Wellness Check-ins
- AI Behavioral Analysis
- Personalized Productivity Coaching
- Analytics Dashboard
- Automated Email Reports
- Admin Content Management

---

# 🧠 AI Capabilities

Velora combines behavioral analytics with Large Language Models to generate personalized coaching.

The AI considers:

- Daily commitments
- Completion history
- Mood trends
- Energy levels
- Productivity patterns
- Habit consistency
- Long-term goals
- Daily priorities
- Focus areas
- Weekly reflections

to generate personalized insights instead of generic motivational messages.

---

# 📊 Analytics

Velora provides insights such as:

- Completion Rate
- Recovery Rate
- Productivity Trends
- Time Slot Analysis
- Confidence Calibration
- Procrastination Detection
- Focus Area Distribution
- Habit Consistency
- Execution Streaks

---

# 🔒 Security

- JWT Authentication
- Password Hashing (bcrypt)
- Protected API Routes
- Session Management
- Secure Password Reset
- Role-Based Admin Access

---

# 🚀 Future Improvements

- React / Next.js frontend
- Alembic database migrations
- Docker support
- Redis caching
- WebSocket notifications
- Mobile application
- Team collaboration
- Calendar integrations
- Advanced ML-based behavioral prediction

---



# 🧪 Local Setup

```bash
# Clone repository
git clone https://github.com/akr-2525/velora.git

cd velora

# Create virtual environment
python -m venv venv

# Activate environment
source venv/bin/activate
# Windows
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Run FastAPI
uvicorn app.main:app --reload

# Run Streamlit
streamlit run app.py
```

---



# 👨‍💻 Author

**AMAN**



---

## ⭐ Why Velora?

Most productivity apps only help users plan tasks.

Velora goes beyond planning by analyzing execution behavior, identifying productivity patterns, detecting procrastination, and delivering personalized AI-powered coaching that helps users build consistent habits and achieve long-term goals.