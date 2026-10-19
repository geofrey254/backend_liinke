from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.services.user_service import get_users_service, create_user_service, get_user_by_id_service

from app.database.session import SessionDep
from app.models.user import User, UserCreate, UserResponse

router = APIRouter()

@router.get("/users")
def get_users(db: SessionDep, ):
    users = get_users_service(db)
    return users

@router.post("/users", response_model=UserResponse)
def create_user(user_data: UserCreate, db: SessionDep):
    new_user = create_user_service(user_data, db)
    return new_user


# get current user
@router.get("/users/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: int, db: SessionDep, response_model=UserResponse):
    user = get_user_by_id_service(user_id, db)
    return user

