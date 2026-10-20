from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import get_current_user, get_current_organization

from app.services.org_service import create_orgs_service, get_orgs_service, get_orgs_by_id_service
from app.database.session import SessionDep
from app.models.organization import Organization, OrganizationCreate, OrganizationResponse


router = APIRouter()

@router.post("/organizations", response_model=OrganizationResponse)
def create_organization(org_data: OrganizationCreate, db: SessionDep):
    new_organization = create_orgs_service(org_data, db)
    return new_organization

# get current organization
@router.get("/organizations/me", response_model=OrganizationResponse)
def read_current_organization(
    current_organization: Organization = Depends(get_current_organization),
):
    return current_organization



@router.get("/organizations/me/members", response_model=list[OrganizationResponse])
def read_organization_members(current_organization: Organization = Depends(get_current_organization), db: SessionDep):
    members = get_orgs_service(current_organization.id, db)
    return members