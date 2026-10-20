from fastapi import APIRouter, Depends
from app.api.v1.endpoints import users, auth, organization

router = APIRouter()

router.include_router(users.router, tags=["users"])
router.include_router(auth.router, tags=["auth"])
router.include_router(organization.router, tags=["organizations"])