from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.database import get_db
from app.models import User
from app.schemas import UserRegister
from app.core.security import hash_password,verify_password,create_access_token
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    username = user.username.strip()
    email = user.email.strip().lower()
    password = user.password.strip()

    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="Username, email, and password are required")

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

    return {"message": "User created"}
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
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
        "token_type": "bearer"
    }
