from fastapi import APIRouter, HTTPException, status
from sqlmodel import select
from datetime import timedelta

from app.core.config import settings
from app.core.security import create_access_token

from app.database.session import SessionDep
from app.models.user import User, UserCreate, UserResponse
from app.utils.passwordhash import hash_password, verify_password
from app.schemas.auth import LoginRequest

router = APIRouter()

# login
@router.post("/login")
def login(credentials: LoginRequest, db: SessionDep):
    user = db.exec(select(User).where(User.email == credentials.email)).first()
    
    if user is None or not verify_password(
        credentials.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )

    # print user info for debugging
    print(f"User {user.email} logged in successfully.")

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# signup
@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, db: SessionDep):
    existing_user = db.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    hashed_password = hash_password(user_data.password)

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hashed_password,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise

    return new_user