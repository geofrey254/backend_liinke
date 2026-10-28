
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Text, CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Event(SQLModel, table=True):
    __tablename__ = "events"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "slug",
            name="uq_organization_event_slug",
        ),
        CheckConstraint(
            "end_at IS NULL OR start_at IS NULL "
            "OR end_at >= start_at",
            name="ck_events_valid_time_range",
        ),
        CheckConstraint(
            "capacity IS NULL OR capacity >= 0",
            name="ck_events_capacity_nonnegative",
        ),
    )

    id: int | None = Field(
        default=None,
        primary_key=True,
    )

    organization_id: int = Field(
        foreign_key="organizations.id",
        nullable=False,
        index=True,
    )

    created_by_user_id: int | None = Field(
        default=None,
        foreign_key="users.id",
        nullable=True,
    )

    # Identity
    name: str = Field(max_length=200, nullable=False)
    slug: str = Field(max_length=100, nullable=False)
    description: str | None = Field(
        default=None,
        sa_type=Text,
    )

    # Scheduling
    timezone_name: str = Field(
        default="Africa/Nairobi",
        max_length=64,
        nullable=False,
    )
    start_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    end_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    registration_opens_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    registration_closes_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )

    # Venue
    venue_name: str | None = Field(
        default=None,
        max_length=200,
    )
    venue_address: str | None = Field(
        default=None,
        max_length=500,
    )

    # Registration
    capacity: int | None = Field(default=None)
    registration_enabled: bool = Field(default=False)

    # Lifecycle
    status: EventStatus = Field(
        default=EventStatus.DRAFT,
        nullable=False,
        index=True,
    )
    published_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    

    # Audit timestamps
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

class EventCreate(SQLModel):
    organization_id: int
    created_by_user_id: int | None = None
    name: str
    slug: str
    description: str | None = None
    timezone_name: str = "Africa/Nairobi"
    start_at: datetime | None = None
    end_at: datetime | None = None
    registration_opens_at: datetime | None = None
    registration_closes_at: datetime | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    capacity: int | None = None
    registration_enabled: bool = False

class EventResponse(SQLModel):
    id: int
    organization_id: int
    created_by_user_id: int | None
    name: str
    slug: str
    description: str | None
    timezone_name: str
    start_at: datetime | None
    end_at: datetime | None
    registration_opens_at: datetime | None
    registration_closes_at: datetime | None
    venue_name: str | None
    venue_address: str | None
    capacity: int | None
    registration_enabled: bool
    status: EventStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

class EventUpdate(SQLModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    timezone_name: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    registration_opens_at: datetime | None = None
    registration_closes_at: datetime | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    capacity: int | None = None
    registration_enabled: bool | None = None