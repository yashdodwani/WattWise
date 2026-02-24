import os
import bcrypt
import secrets
import string
import jwt
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# ==================== CONFIG ====================
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
OTP_EXPIRE_MINUTES = 10  # 10 minutes


# ==================== PASSWORD HASHING ====================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# ==================== JWT TOKENS ====================

def create_access_token(user_id: int, username: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(IST) + expires_delta
    to_encode = {
        "sub": str(user_id),
        "username": username,
        "exp": expire
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ==================== OTP ====================
def generate_otp() -> str:
    return ''.join(secrets.choice("0123456789") for _ in range(6))


def get_otp_expiry() -> datetime:
    """Get OTP expiry time (current time + 10 minutes)"""
    return datetime.now(IST) + timedelta(minutes=OTP_EXPIRE_MINUTES)
