from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
import jwt
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "Set it in your .env file before starting the server."
    )

ALGORITHM = "HS256"
# 30-day sessions — users stay logged in across days without re-authenticating
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generate_reset_token() -> str:
    """Generate a cryptographically secure password-reset token."""
    return secrets.token_urlsafe(32)
