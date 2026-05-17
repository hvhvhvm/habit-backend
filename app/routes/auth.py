from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.database import get_db
from app.models import User
from app.schemas import UserRegister, OnboardingComplete
from app.core.security import hash_password,verify_password,create_access_token,get_current_user
from fastapi.security import OAuth2PasswordRequestForm
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    try:
        username = user.username.strip()
        email = user.email.strip().lower()
        password = user.password.strip()

        if not username or not email or not password:
            raise HTTPException(status_code=400, detail="Username, email, and password are required")

        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

        existing_user = db.query(User).filter(
            or_(
                func.lower(User.email) == email,
                func.lower(User.username) == username.lower()
            )
        ).first()

        if existing_user:
            raise HTTPException(status_code=400, detail="Email or username already registered")

        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        access_token = create_access_token({"sub": str(new_user.id)})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": new_user.id,
            "username": new_user.username
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    try:
        login_id = form_data.username.strip().lower()
        password = form_data.password.strip()

        if not login_id or not password:
            raise HTTPException(status_code=400, detail="Email/username and password are required")

        db_user = db.query(User).filter(
            or_(
                func.lower(User.email) == login_id,
                func.lower(User.username) == login_id
            )
        ).first()

        if not db_user:
            raise HTTPException(status_code=400, detail="Invalid credentials")

        if not verify_password(password, db_user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid credentials")

        access_token = create_access_token({"sub": str(db_user.id)})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": db_user.id,
            "username": db_user.username
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/complete-onboarding")
def complete_onboarding(
    payload: OnboardingComplete | None = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        if payload and payload.name:
            current_user.username = payload.name.strip() or current_user.username
        if payload and payload.habits:
            from app.crud import create_habits_bulk
            create_habits_bulk(db, payload.habits, current_user.id)
        current_user.onboarding_done = True
        db.commit()
        return {"message": "Onboarding completed", "created_habits": len(payload.habits) if payload else 0}
    except Exception as e:
        logger.error(f"Onboarding error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Onboarding failed")

@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    try:
        return {
            "id": current_user.id,
            "email": current_user.email,
            "onboarding_done": current_user.onboarding_done,
            "username":current_user.username,
            "journey_start_date": str(current_user.journey_start_date) if current_user.journey_start_date else None
        }
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user data")

@router.post("/refresh")
def refresh_token(current_user = Depends(get_current_user)):
    """Issue a fresh token with a new expiry. Call this on app load to extend sessions."""
    try:
        new_token = create_access_token({"sub": str(current_user.id)})
        return {
            "access_token": new_token,
            "token_type": "bearer"
        }
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed")
