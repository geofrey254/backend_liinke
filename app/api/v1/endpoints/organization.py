from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.services.user_service import get_users_service, create_user_service, get_user_by_id_service

from app.database.session import SessionDep
from app.models.organization import Organization, OrganizationCreate, OrganizationResponse