from fastapi import APIRouter, Depends
from app.services.user_service import get_users

router = APIRouter()

@router.get("/users")
def get_users():
    users = get_users()
    return users