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
from backend.services.ai_coach_service import generate_daily_digest
from backend.services.email_service import send_email

# Import our security tools
from backend.services.auth_service import (
    get_password_hash, verify_password, create_access_token, 
    SECRET_KEY, ALGORITHM
)

# Initialize the database tables
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
    print("🚀 [SCHEDULER] Starting the automated daily AI Coach pipeline...")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            print(f"🧠 Generating custom advice for {user.name}...")
            
            # 1. Ask Gemini to generate the custom JSON
            ai_advice = generate_daily_digest(user.name, user.interests)
            
            # 🚨 THE LOUD DEBUGGER
            print(f"🚨 DEBUG TYPE: {type(ai_advice)}")
            
            # 🛡️ THE ARMOR PLATING: If it's a string, force it to be a dictionary!
            if isinstance(ai_advice, str):
                import json
                try:
                    print("⚠️ WARNING: It was a string! Converting to dictionary now...")
                    ai_advice = json.loads(ai_advice)
                except:
                    print("❌ ERROR: String was corrupted. Using safe fallback dictionary.")
                    ai_advice = {
                        "tip": "Take a 5-minute walk away from your keyboard.",
                        "habit_reminder": "Spend 10 minutes reviewing your core goals today.",
                        "quote": "Consistency is what transforms average into excellence.",
                        "author": "System Coach"
                    }
                    
            # 2. Format it into a beautiful HTML email
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                    <h2 style="color: #2c3e50;">Good Morning, {user.name}! ☕</h2>
                    <p>Here is your daily personalized coaching to help you master: <strong>{user.interests}</strong></p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #2980b9;">💡 Today's Technical Tip</h3>
                        <p>{ai_advice.get('tip', 'Keep pushing forward.')}</p>
                    </div>
                    
                    <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #856404;">🎯 Daily Micro-Habit</h3>
                        <p>{ai_advice.get('habit_reminder', 'Stay consistent.')}</p>
                    </div>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
                    
                    <blockquote style="font-style: italic; color: #7f8c8d; font-size: 1.1em; text-align: center;">
                        "{ai_advice.get('quote', 'Never give up.')}" <br>
                        <strong>- {ai_advice.get('author', 'Coach')}</strong>
                    </blockquote>
                </body>
            </html>
            """
            
            # 3. Send the email
            try:
                # We are directly passing the HTML string to your updated email_service.py
                send_email(user.email, f"Your Daily AI Coach: {user.interests}", html_content)
                print(f"✅ Email successfully sent to {user.email}")
            except Exception as email_err:
                print(f"❌ Could not send email. Error: {email_err}")
            
    except Exception as e:
        print(f"❌ Scheduler Error: {e}")
    finally:
        db.close()

# Start the background job when the server starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    # Currently set to run every 2 minutes for testing. 
    # Change 'minutes=2' to 'hours=24' when you are done testing.
    scheduler.add_job(run_daily_digest, 'interval', minutes=2)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# --- LOGIN ENDPOINT ---
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": {"name": user.name, "interests": user.interests, "email": user.email}}

# --- STANDARD ENDPOINTS ---
@app.get("/")
def home():
    return {"message": "SmartBrief AI Coach running"}

@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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

# --- PROTECTED ENDPOINTS ---
@app.put("/users/me", response_model=UserResponse)
def update_user(user_update: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.interests = user_update.interests
    db.commit()
    db.refresh(current_user)
    return current_user

@app.delete("/users/me")
def delete_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(current_user)
    db.commit()
    return {"message": "User successfully unsubscribed"}

# --- AI COACH ENDPOINT ---
@app.get("/generate-digest")
def get_daily_digest(goals: str, name: str = "User"):
    digest = generate_daily_digest(name, goals)
    if not digest:
        raise HTTPException(status_code=500, detail="Failed to generate AI digest")
    return digest