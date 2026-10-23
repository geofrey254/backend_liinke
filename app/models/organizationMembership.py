
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrganizationRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class OrganizationMembership(SQLModel, table=True):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_user_organization_membership",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="users.id", index=True)
    organization_id: int = Field(
        foreign_key="organizations.id",
        index=True,
    )

    role: OrganizationRole = Field(
        default=OrganizationRole.MEMBER,
        max_length=20,
    )

    status: MembershipStatus = Field(
        default=MembershipStatus.ACTIVE,
        max_length=20,
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )

class OrganizationMembershipJoin(SQLModel):
    organization_id: int


class OrganizationMembershipAdminCreate(SQLModel):
    user_id: int
    role: OrganizationRole = OrganizationRole.MEMBER


class OrganizationMembershipResponse(SQLModel):
    id: int
    user_id: int
    organization_id: int
    role: OrganizationRole
    status: MembershipStatus
    created_at: datetime

class OrganizationMembershipRoleUpdate(SQLModel):
    role: OrganizationRole