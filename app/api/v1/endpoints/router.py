from fastapi import APIRouter, Depends
from app.api.v1.endpoints import users

router = APIRouter()

router.include_router(users.router, tags=["users"])