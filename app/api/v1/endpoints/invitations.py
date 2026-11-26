from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import settings
from app.core.dependencies import (
    get_current_user,
    get_current_organization,
    get_current_membership,
    require_organization_admin,
)
from app.database.session import SessionDep
from app.models.organization import Organization
from app.models.organizationInvitation import OrganizationInvitation
from app.models.organizationMembership import OrganizationMembership
from app.models.user import User
from app.schemas.invitations import (
    OrganizationInvitationCreate,
    OrganizationInvitationResponse,
    InvitationPublicResponse,
    InvitationAcceptResponse,
)
from app.services.invitation_service import (
    create_invitation,
    list_organization_invitations,
    get_invitation_by_token,
    resend_invitation,
    revoke_invitation,
    accept_invitation,
)
from app.utils.email import send_organization_invitation

router = APIRouter()


def _send_email(invitation: OrganizationInvitation, token: str,
                organization: Organization, inviter: User) -> None:
    query = urlencode({"token": token})
    invitation_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/invite/accept?{query}"
    )
    send_organization_invitation(
        to_email=invitation.email,
        organization_name=organization.name,
        inviter_name=inviter.full_name,
        role=str(invitation.role),
        invitation_url=invitation_url,
    )


@router.get(
    "/me/invitations",
    response_model=list[OrganizationInvitationResponse],
    tags=["invitations"],
)
def list_invitations(
    db: SessionDep,
    organization: Annotated[Organization, Depends(get_current_organization)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    __: Annotated[None, Depends(require_organization_admin)],
):
    return list_organization_invitations(db, organization.id)


@router.post(
    "/me/invitations",
    response_model=OrganizationInvitationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["invitations"],
)
def invite_team_member(
    data: OrganizationInvitationCreate,
    db: SessionDep,
    organization: Annotated[Organization, Depends(get_current_organization)],
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
):
    invitation, token = create_invitation(
        db=db,
        organization=organization,
        invited_by=current_user,
        inviter_membership=membership,
        email=str(data.email),
        role=data.role,
    )
    _send_email(invitation, token, organization, current_user)
    return invitation


@router.post(
    "/me/invitations/{invitation_id}/resend",
    response_model=OrganizationInvitationResponse,
    tags=["invitations"],
)
def resend_team_invitation(
    invitation_id: int,
    db: SessionDep,
    organization: Annotated[Organization, Depends(get_current_organization)],
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
):
    invitation, token = resend_invitation(db, organization.id, invitation_id, membership)
    # The service rotates the token before delivery. If delivery fails, the
    # administrator can safely retry using this endpoint.
    _send_email(invitation, token, organization, current_user)
    return invitation


@router.delete(
    "/me/invitations/{invitation_id}",
    response_model=OrganizationInvitationResponse,
    tags=["invitations"],
)
def revoke_team_invitation(
    invitation_id: int,
    db: SessionDep,
    organization: Annotated[Organization, Depends(get_current_organization)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
):
    return revoke_invitation(db, organization.id, invitation_id)


@router.get(
    "/invitations/lookup",
    response_model=InvitationPublicResponse,
    tags=["invitations"],
)
def lookup_invitation(
    db: SessionDep,
    token: Annotated[str, Query(min_length=1, max_length=512)],
):
    invitation, organization = get_invitation_by_token(db, token)
    return InvitationPublicResponse(
        organization_name=organization.name,
        organization_slug=organization.slug,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        expires_at=invitation.expires_at,
    )


@router.post(
    "/invitations/accept",
    response_model=InvitationAcceptResponse,
    tags=["invitations"],
)
def accept_team_invitation(
    token: Annotated[str, Query(min_length=1, max_length=512)],
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
):
    membership, organization = accept_invitation(db, token, current_user)
    return InvitationAcceptResponse(
        message="Invitation accepted successfully.",
        organization_id=organization.id,
        organization_slug=organization.slug,
        role=membership.role,
    )
