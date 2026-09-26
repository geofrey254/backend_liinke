from fastapi import APIRouter, Depends
from app.services.user_service import get_users_service, create_user_service, get_user_by_id_service

from app.database.session import SessionDep
from app.models.user import UserCreate, UserResponse

router = APIRouter()

@router.get("/users")
def get_users(db: SessionDep):
    users = get_users_service(db)
    return users

@router.post("/users", response_model=UserResponse)
def create_user(user_data: UserCreate, db: SessionDep):
    new_user = create_user_service(user_data, db)
    return new_user

@router.get("/users/{user_id}")
def get_user_by_id(user_id: int, db: SessionDep):
    user = get_user_by_id_service(user_id, db)
    return user