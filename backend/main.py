from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from pydantic import BaseModel
import jwt

# Import your database and models
from backend.db.database import engine, SessionLocal
from backend.models.user_model import User
from backend.models.schemas import UserCreate, UserResponse, UserUpdate 

# Import your core services
from backend.services.news_service import get_top_headlines
from backend.services.summarizer_service import summarize_text
from backend.services.email_service import send_daily_digest

# Import our new security tools
from backend.services.auth_service import (
    get_password_hash, verify_password, create_access_token, 
    SECRET_KEY, ALGORITHM
)

try:
    User.metadata.create_all(bind=engine)
except Exception as e:
    print("DB connection failed:", e)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- SECURITY DEPENDENCY ---
# This tells FastAPI where the frontend will send login credentials
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # 1. The server intercepts the JWT token and attempts to decode it using the SECRET_KEY
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # 2. If the token is mathematically valid, fetch the user from the database
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# --- SCHEDULER LOGIC ---
def run_daily_digest():
    print("🚀 [SCHEDULER] Starting the automated daily digest pipeline...")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            return

        for user in users:
            print(f"🗞️ Fetching news for {user.name}...")
            raw_articles = get_top_headlines(user.interests)
            summarized_articles = []
            
            for article in raw_articles:
                description = article.get("description") or ""
                summary = summarize_text(description)
                summarized_articles.append({
                    "title": article.get("title"),
                    "summary": summary,
                    "url": article.get("url")
                })
            
            send_daily_digest(user.email, user.name, summarized_articles)
        print("✅ [SCHEDULER] Daily digest pipeline completed successfully!")
            
    except Exception as e:
        print(f"❌ [SCHEDULER] Pipeline error: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_daily_digest, 'interval', minutes=2)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)



# --- NEW: LOGIN ENDPOINT ---
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # Find user
    user = db.query(User).filter(User.email == req.email).first()
    
    # Verify math (hash matching)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Generate the VIP Badge (JWT)
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": {"name": user.name, "interests": user.interests, "email": user.email}}

# --- EXISTING/UPDATED ENDPOINTS ---
@app.get("/")
def home():
    return {"message": "SmartBrief AI running"}

@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash the password BEFORE saving it to the database
    hashed_pw = get_password_hash(user.password)
    
    new_user = User(
        name=user.name, 
        email=user.email, 
        interests=user.interests, 
        hashed_password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- PROTECTED ENDPOINTS (Requires valid JWT to access) ---
@app.put("/users/me", response_model=UserResponse)
def update_user(user_update: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Notice we don't ask for an email in the URL anymore. The identity is proven by the token.
    current_user.interests = user_update.interests
    db.commit()
    db.refresh(current_user)
    return current_user

@app.delete("/users/me")
def delete_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(current_user)
    db.commit()
    return {"message": "User successfully unsubscribed"}

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
    return {"category": category, "total_articles": len(summarized_articles), "articles": summarized_articles}