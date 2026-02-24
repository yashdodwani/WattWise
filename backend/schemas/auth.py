from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ==================== REGISTRATION ====================

class CombinedRegistrationRequest(BaseModel):
    """Combined one-step registration with all details"""
    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    phone_number: str = Field(..., min_length=10, max_length=10, description="10 digit phone number")
    consumer_number: str = Field(..., min_length=10, max_length=13, description="10-13 digit consumer number")



class RegisterWithTokenResponse(BaseModel):
    """Registration response with instant JWT token (no login required)"""
    id: int
    name: str
    username: str
    phone_number: str
    consumer_number: str
    created_at: datetime
    access_token: str
    token_type: str = "bearer"
    message: str = "Registration successful! You are now logged in."

    class Config:
        from_attributes = True


# ==================== LOGIN ====================

class LoginRequest(BaseModel):
    """Login with username and password"""
    username: str
    password: str


class OTPLoginRequest(BaseModel):
    """Request OTP for phone-based login"""
    phone_number: str = Field(..., min_length=10, max_length=10, description="10 digit phone number")


class VerifyOTPRequest(BaseModel):
    """Verify OTP code"""
    phone_number: str = Field(..., min_length=10, max_length=10)
    otp_code: str = Field(..., min_length=6, max_length=6, description="6 digit OTP code")


class TokenResponse(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class OTPResponse(BaseModel):
    """OTP sent response"""
    message: str
    phone_number: str


# ==================== USER PROFILE ====================

class UserProfile(BaseModel):
    id: int
    name: str
    username: str
    phone_number: str
    consumer_number: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

