from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager

# Import your database and models
from backend.db.database import engine, SessionLocal
from backend.models.user_model import User
from backend.models.schemas import UserCreate, UserResponse, UserUpdate 

# Import your core services
from backend.services.news_service import get_top_headlines
from backend.services.summarizer_service import summarize_text
from backend.services.email_service import send_daily_digest

# --- 1. THE MASTER PIPELINE (SCHEDULER LOGIC) ---
def run_daily_digest():
    print("🚀 [SCHEDULER] Starting the automated daily digest pipeline...")
    
    # Open a fresh database connection for the background task
    db = SessionLocal()
    try:
        # Get every registered user from the database
        users = db.query(User).all()
        
        if not users:
            print("No users found in the database. Skipping.")
            return

        for user in users:
            print(f"🗞️ Fetching news for {user.name} (Interests: {user.interests})...")
            
            # Fetch raw articles based on their specific interests
            raw_articles = get_top_headlines(user.interests)
            
            # Summarize each article using your AI transformer model
            summarized_articles = []
            for article in raw_articles:
                description = article.get("description") or ""
                summary = summarize_text(description)
                
                summarized_articles.append({
                    "title": article.get("title"),
                    "summary": summary,
                    "url": article.get("url")
                })
            
            # Dispatch the final email
            print(f"📧 Sending email to {user.email}...")
            send_daily_digest(user.email, user.name, summarized_articles)
            
        print("✅ [SCHEDULER] Daily digest pipeline completed successfully!")
            
    except Exception as e:
        print(f"❌ [SCHEDULER] Pipeline error: {e}")
    finally:
        db.close() # Always close the connection to prevent memory leaks

# --- 2. THE SCHEDULER LIFESPAN ---
# This starts the clock when the server boots and stops it when the server shuts down
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    
    # FOR TESTING: Runs every 2 minutes so you can see it work immediately
    scheduler.add_job(run_daily_digest, 'interval', hours=24)
    
    # FOR PRODUCTION (Later): Comment out the line above and uncomment this one for a daily 8 AM run
    # scheduler.add_job(run_daily_digest, 'cron', hour=8, minute=0)
    
    scheduler.start()
    yield
    scheduler.shutdown()

# Initialize FastAPI with the lifespan scheduler
app = FastAPI(lifespan=lifespan)

# Create tables if they don't exist
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

# --- 3. EXISTING API ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "SmartBrief AI running"}

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

@app.get("/news")
def fetch_news(category: str = "sports"):
    # This keeps your Streamlit "Live News" tab working independently of the emailer
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
    
    
# Read User Profile ---
@app.get("/users/{email}", response_model=UserResponse)
def get_user(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Update User Interests ---
@app.put("/users/{email}", response_model=UserResponse)
def update_user(email: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update the database with the new interests
    user.interests = user_update.interests
    db.commit()
    db.refresh(user)
    return user

# Delete/Unsubscribe User ---
@app.delete("/users/{email}")
def delete_user(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"message": "User successfully unsubscribed"}