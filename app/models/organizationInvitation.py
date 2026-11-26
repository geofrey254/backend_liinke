from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.organizationMembership import OrganizationRole


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class OrganizationInvitation(SQLModel, table=True):
    __tablename__ = "organization_invitations"

    id: int | None = Field(default=None, primary_key=True)

    organization_id: int = Field(
        foreign_key="organizations.id",
        index=True,
        nullable=False,
    )

    invited_by_user_id: int = Field(
        foreign_key="users.id",
        index=True,
        nullable=False,
    )

    email: str = Field(
        index=True,
        max_length=255,
        nullable=False,
    )

    role: OrganizationRole = Field(
        default=OrganizationRole.MEMBER,
        max_length=20,
        nullable=False,
    )

    # SHA-256 hex digest of the random invitation token; never store the raw token.
    token_hash: str = Field(
        unique=True,
        index=True,
        max_length=64,
        nullable=False,
    )

    status: InvitationStatus = Field(
        default=InvitationStatus.PENDING,
        max_length=20,
        nullable=False,
    )

    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
    )

    accepted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
