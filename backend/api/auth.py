from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import User, OTPRecord
from schemas.auth import (
    CombinedRegistrationRequest,
    LoginRequest,
    OTPLoginRequest,
    VerifyOTPRequest,
    TokenResponse,
    OTPResponse,
    RegisterWithTokenResponse,
    UserProfile,
)
from utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token,
    generate_otp,
    get_otp_expiry,
)
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==================== HELPER FUNCTIONS ====================

def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid token scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def validate_phone_number(phone_number: str) -> bool:
    """Validate phone number (10 digits)"""
    return len(phone_number) == 10 and phone_number.isdigit()


def validate_consumer_number(consumer_number: str) -> bool:
    """Validate consumer number (10-13 digits)"""
    return 10 <= len(consumer_number) <= 13 and consumer_number.isdigit()



# ==================== REGISTRATION ENDPOINTS ====================

@router.post("/register", response_model=RegisterWithTokenResponse)
def register_combined(request: CombinedRegistrationRequest, db: Session = Depends(get_db)):
    """
    Combined One-Step Registration - NO LOGIN REQUIRED AFTER THIS!

    Users provide all details in one go:
    - Full name
    - Username (unique)
    - Password
    - Phone number (10 digits)
    - Consumer number (10-13 digits)

    Returns:
    - User details
    - JWT access token (instantly logged in!)
    - User can use the token immediately
    """

    # Validate consumer number format
    if not validate_consumer_number(request.consumer_number):
        raise HTTPException(
            status_code=400,
            detail="Consumer number must be 10-13 digits"
        )

    # Validate phone number format
    if not validate_phone_number(request.phone_number):
        raise HTTPException(
            status_code=400,
            detail="Phone number must be 10 digits"
        )

    # Validate username length
    if not request.username or len(request.username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters long"
        )

    # Validate password length
    if not request.password or len(request.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters long"
        )

    # Check if consumer number already exists
    existing_consumer = db.query(User).filter(User.consumer_number == request.consumer_number).first()
    if existing_consumer:
        raise HTTPException(
            status_code=400,
            detail="This consumer number is already registered"
        )

    # Check if phone number already exists
    existing_phone = db.query(User).filter(User.phone_number == request.phone_number).first()
    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="This phone number is already registered"
        )

    # Check if username already exists
    existing_username = db.query(User).filter(User.username == request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="This username is already taken"
        )

    # Hash the password
    hashed_password = hash_password(request.password)

    # Create new user
    new_user = User(
        name=request.name,
        username=request.username,
        password_hash=hashed_password,
        phone_number=request.phone_number,
        consumer_number=request.consumer_number,
        is_active=True
    )

    # Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # ✨ GENERATE JWT TOKEN INSTANTLY (NO LOGIN REQUIRED!)
    access_token = create_access_token(new_user.id, new_user.username)

    # Return user details with token
    return RegisterWithTokenResponse(
        id=new_user.id,
        name=new_user.name,
        username=new_user.username,
        phone_number=new_user.phone_number,
        consumer_number=new_user.consumer_number,
        created_at=new_user.created_at,
        access_token=access_token,
        token_type="bearer",
        message="Registration successful! You are now logged in."
    )


# ==================== LOGIN ENDPOINTS ====================

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with username and password.
    Returns JWT access token on successful authentication.
    """

    # Find user by username
    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Create JWT token
    access_token = create_access_token(user.id, user.username)

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
    )


# ==================== OTP LOGIN ENDPOINTS ====================

@router.post("/otp/request", response_model=OTPResponse)
def request_otp(request: OTPLoginRequest, db: Session = Depends(get_db)):
    """
    Request OTP for phone-based login.
    Sends OTP to the provided phone number.
    In production, integrate with SMS service (Twilio, AWS SNS, etc.)
    """

    if not validate_phone_number(request.phone_number):
        raise HTTPException(
            status_code=400,
            detail="Phone number must be 10 digits"
        )

    # Find user by phone number
    user = db.query(User).filter(User.phone_number == request.phone_number).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with this phone number not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    # Generate OTP
    otp_code = generate_otp()
    expiry_time = get_otp_expiry()

    # Store OTP in database
    otp_record = OTPRecord(
        user_id=user.id,
        otp_code=otp_code,
        expires_at=expiry_time,
    )

    db.add(otp_record)
    db.commit()

    # TODO: Send OTP via SMS (integrate with Twilio, AWS SNS, or similar)
    # send_sms(phone_number=request.phone_number, message=f"Your WattWise OTP is: {otp_code}")

    print(f"[DEV] OTP for {request.phone_number}: {otp_code} (HARDCODED)")  # For development only

    return OTPResponse(
        message="OTP sent successfully to your phone number",
        phone_number=request.phone_number,
    )


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Verify OTP and login user.
    Returns JWT access token if OTP is valid.
    """

    if not validate_phone_number(request.phone_number):
        raise HTTPException(
            status_code=400,
            detail="Phone number must be 10 digits"
        )

    if len(request.otp_code) != 6 or not request.otp_code.isdigit():
        raise HTTPException(
            status_code=400,
            detail="OTP must be 6 digits"
        )

    # Find user by phone number
    user = db.query(User).filter(User.phone_number == request.phone_number).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    # Find valid OTP record
    otp_record = db.query(OTPRecord).filter(
        OTPRecord.user_id == user.id,
        OTPRecord.otp_code == request.otp_code,
        OTPRecord.is_used == False,
        OTPRecord.expires_at > datetime.now(IST),
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired OTP"
        )

    # Mark OTP as used
    otp_record.is_used = True
    db.commit()

    # Create JWT token
    access_token = create_access_token(user.id, user.username)

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
    )


# ==================== USER PROFILE ENDPOINTS ====================

@router.get("/profile", response_model=UserProfile)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserProfile.model_validate(current_user)


@router.post("/logout", response_model=dict)
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout endpoint (token-based auth).
    In production, add token to blacklist if needed.
    """
    return {
        "message": f"User {current_user.username} logged out successfully"
    }
