"""Database and validation logic for organization invitations.

The API layer orchestrates email delivery so database rules remain independent
of the configured email provider.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.organization import Organization
from app.models.organizationInvitation import (
    InvitationStatus,
    OrganizationInvitation,
)
from app.models.organizationMembership import (
    MembershipStatus,
    OrganizationMembership,
    OrganizationRole,
)
from app.models.user import User

INVITATION_TTL = timedelta(days=7)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    """SQLite may return naive datetimes even for timezone-aware columns."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ensure_inviter_can_assign_role(
    inviter_membership: OrganizationMembership,
    role: OrganizationRole,
) -> None:
    if role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner role cannot be assigned through an invitation.",
        )

    if (
        role == OrganizationRole.ADMIN
        and inviter_membership.role != OrganizationRole.OWNER
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization owner can invite administrators.",
        )


def create_invitation(
    db: Session,
    organization: Organization,
    invited_by: User,
    inviter_membership: OrganizationMembership,
    email: str,
    role: OrganizationRole,
) -> tuple[OrganizationInvitation, str]:
    """Create a pending invitation and return it with its one-time raw token."""
    normalized_email = _normalize_email(email)
    _ensure_inviter_can_assign_role(inviter_membership, role)

    if not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot invite members to an inactive organization.",
        )

    existing_user = db.exec(
        select(User).where(func.lower(User.email) == normalized_email)
    ).first()

    if existing_user is not None:
        existing_membership = db.exec(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == existing_user.id,
                OrganizationMembership.organization_id == organization.id,
            )
        ).first()
        if (
            existing_membership is not None
            and existing_membership.status == MembershipStatus.ACTIVE
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already an active member of the organization.",
            )

    pending = db.exec(
        select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == organization.id,
            func.lower(OrganizationInvitation.email) == normalized_email,
            OrganizationInvitation.status == InvitationStatus.PENDING,
        )
    ).first()

    if pending is not None:
        if _as_utc(pending.expires_at) > _now():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending invitation already exists for this email address.",
            )
        pending.status = InvitationStatus.EXPIRED
        db.add(pending)

    raw_token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        organization_id=organization.id,
        invited_by_user_id=invited_by.id,
        email=normalized_email,
        role=role,
        token_hash=_hash_token(raw_token),
        status=InvitationStatus.PENDING,
        expires_at=_now() + INVITATION_TTL,
    )

    try:
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create the invitation because it conflicts with an existing record.",
        ) from None

    return invitation, raw_token


def list_organization_invitations(
    db: Session,
    organization_id: int,
) -> list[OrganizationInvitation]:
    invitations = db.exec(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.organization_id == organization_id)
        .order_by(OrganizationInvitation.created_at.desc())
    ).all()

    now = _now()
    changed = False
    for invitation in invitations:
        if (
            invitation.status == InvitationStatus.PENDING
            and _as_utc(invitation.expires_at) <= now
        ):
            invitation.status = InvitationStatus.EXPIRED
            db.add(invitation)
            changed = True

    if changed:
        db.commit()

    return list(invitations)


def get_invitation_by_token(
    db: Session,
    token: str,
) -> tuple[OrganizationInvitation, Organization]:
    if not token or len(token) > 512:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found.",
        )

    invitation = db.exec(
        select(OrganizationInvitation).where(
            OrganizationInvitation.token_hash == _hash_token(token)
        )
    ).first()

    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found.",
        )

    if invitation.status == InvitationStatus.PENDING and _as_utc(invitation.expires_at) <= _now():
        invitation.status = InvitationStatus.EXPIRED
        db.add(invitation)
        db.commit()
        db.refresh(invitation)

    organization = db.get(Organization, invitation.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The organization associated with this invitation no longer exists.",
        )

    return invitation, organization


def resend_invitation(
    db: Session,
    organization_id: int,
    invitation_id: int,
    inviter_membership: OrganizationMembership | None = None,
) -> tuple[OrganizationInvitation, str]:
    invitation = db.exec(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == organization_id,
        )
    ).first()

    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending invitations can be resent.",
        )

    if inviter_membership is not None:
        _ensure_inviter_can_assign_role(inviter_membership, invitation.role)

    if _as_utc(invitation.expires_at) <= _now():
        invitation.status = InvitationStatus.EXPIRED
        db.add(invitation)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invitation has expired. Create a new invitation instead.",
        )

    raw_token = secrets.token_urlsafe(32)
    invitation.token_hash = _hash_token(raw_token)
    invitation.expires_at = _now() + INVITATION_TTL

    try:
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not refresh the invitation token.",
        ) from None

    return invitation, raw_token


def revoke_invitation(
    db: Session,
    organization_id: int,
    invitation_id: int,
) -> OrganizationInvitation:
    invitation = db.exec(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == organization_id,
        )
    ).first()

    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending invitations can be revoked.",
        )

    invitation.status = InvitationStatus.REVOKED
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def accept_invitation(
    db: Session,
    token: str,
    current_user: User,
) -> tuple[OrganizationMembership, Organization]:
    """Accept an invitation for the authenticated user in one transaction."""
    if not token or len(token) > 512:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    invitation = db.exec(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.token_hash == _hash_token(token))
        .with_for_update()
    ).first()

    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This invitation is {invitation.status} and cannot be accepted.",
        )

    if _as_utc(invitation.expires_at) <= _now():
        invitation.status = InvitationStatus.EXPIRED
        db.add(invitation)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invitation has expired.",
        )

    if _normalize_email(current_user.email) != _normalize_email(invitation.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sign in with the email address this invitation was sent to.",
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account is inactive.",
        )

    organization = db.get(Organization, invitation.organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The organization is unavailable or inactive.",
        )

    existing_membership = db.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.organization_id == organization.id,
        )
    ).first()

    if (
        existing_membership is not None
        and existing_membership.status == MembershipStatus.ACTIVE
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already an active member of this organization.",
        )

    if existing_membership is not None:
        # Reactivate a previously suspended or revoked membership instead of
        # violating the unique user/organization membership constraint.
        membership = existing_membership
        membership.role = invitation.role
        membership.status = MembershipStatus.ACTIVE
    else:
        membership = OrganizationMembership(
            user_id=current_user.id,
            organization_id=organization.id,
            role=invitation.role,
            status=MembershipStatus.ACTIVE,
        )

    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = _now()

    try:
        db.add(membership)
        db.add(invitation)
        db.commit()
        db.refresh(membership)
        db.refresh(invitation)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This invitation may already have been accepted or the membership already exists.",
        ) from None

    return membership, organization
