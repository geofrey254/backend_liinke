from fastapi import APIRouter, Depends
from app.api.v1.endpoints import invitations, users, auth, organization, event, guests, access_levels, access_levels_zones, security_zones

router = APIRouter()

router.include_router(users.router, tags=["users"])
router.include_router(auth.router, tags=["auth"])
router.include_router(organization.router, tags=["organizations"])
router.include_router(event.router, tags=["events"])
router.include_router(guests.router, tags=["guests"])
router.include_router(access_levels.router, tags=["access_levels"])
router.include_router(security_zones.router, tags=["security_zones"])
router.include_router(access_levels_zones.router, tags=["access_levels_zones"])
router.include_router(invitations.router, tags=["invitations"])
