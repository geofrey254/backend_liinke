from datetime import datetime

from pydantic import EmailStr, field_validator
from sqlmodel import SQLModel

from app.models.organizationInvitation import InvitationStatus
from app.models.organizationMembership import OrganizationRole


class OrganizationInvitationCreate(SQLModel):
    email: EmailStr
    role: OrganizationRole = OrganizationRole.MEMBER

    @field_validator("role")
    @classmethod
    def owner_cannot_be_invited(cls, value: OrganizationRole) -> OrganizationRole:
        if value == OrganizationRole.OWNER:
            raise ValueError("Owner role cannot be assigned through an invitation.")
        return value


class OrganizationInvitationResponse(SQLModel):
    id: int
    organization_id: int
    invited_by_user_id: int
    email: EmailStr
    role: OrganizationRole
    status: InvitationStatus
    expires_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime


class InvitationPublicResponse(SQLModel):
    organization_name: str
    organization_slug: str
    email: EmailStr
    role: OrganizationRole
    status: InvitationStatus
    expires_at: datetime


class InvitationAcceptResponse(SQLModel):
    message: str
    organization_id: int
    organization_slug: str
    role: OrganizationRole
