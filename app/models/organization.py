
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.organizationMembership import OrganizationMembershipResponse


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id: int | None = Field(default=None, primary_key=True)

    name: str = Field(max_length=200, index=True)
    slug: str = Field(
        max_length=100,
        unique=True,
        index=True,
        nullable=False,
    )

    category: str | None = Field(default=None, max_length=100)

    website_url: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
 
    timezone: str = Field(
        default="UTC",
        max_length=64,
        nullable=False,
    )

    is_active: bool = Field(default=True, nullable=False)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )

    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"onupdate": utc_now},
    )


class OrganizationCreate(SQLModel):
    name: str
    slug: str
    category: str | None = None
    website_url: str | None = None
    logo_url: str | None = None
    timezone: str = "UTC"
    is_active: bool = True

class OrganizationRead(SQLModel):
    id: int
    name: str
    slug: str
    category: str | None = None
    website_url: str | None = None
    logo_url: str | None = None
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class OrganizationUpdate(SQLModel):
    name: str | None = None
    slug: str | None = None
    category: str | None = None
    website_url: str | None = None
    logo_url: str | None = None
    timezone: str | None = None
    is_active: bool | None = None

class OrganizationResponse(SQLModel):
    id: int
    name: str
    slug: str
    category: str | None = None
    website_url: str | None = None
    logo_url: str | None = None
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class CurrentOrganizationResponse(SQLModel):
    organization: OrganizationResponse
    membership: OrganizationMembershipResponse