from sqlmodel import SQLModel

from app.models.organization import OrganizationResponse
from app.models.organizationMembership import (
    OrganizationMembershipResponse,
)


class OrganizationMembershipWithOrganization(
    OrganizationMembershipResponse
):
    organization: OrganizationResponse


class CurrentOrganizationResponse(SQLModel):
    organization: OrganizationResponse
    membership: OrganizationMembershipResponse