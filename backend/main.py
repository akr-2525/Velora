from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.news_service import get_top_headlines
from backend.services.summarizer_service import summarize_text
from backend.db.database import engine, SessionLocal
from backend.models.user_model import User
from backend.models.schemas import UserCreate, UserResponse # Import your new schema

app = FastAPI()

# Create tables
try:
    User.metadata.create_all(bind=engine)
except Exception as e:
    print("DB connection failed:", e)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"message": "SmartBrief AI running"}

# --- NEW: User Registration Endpoint ---
@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    new_user = User(name=user.name, email=user.email, interests=user.interests)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- EXISTING: News Endpoint ---
@app.get("/news")
def fetch_news(category: str = "sports"):
    articles = get_top_headlines(category)
    summarized_articles = []

    for article in articles:
        description = article.get("description") or ""
        summary = summarize_text(description)

        summarized_articles.append({
            "title": article.get("title"),
            "summary": summary,
            "url": article.get("url")
        })

    return {
        "category": category,
        "total_articles": len(summarized_articles),
        "articles": summarized_articles
    }