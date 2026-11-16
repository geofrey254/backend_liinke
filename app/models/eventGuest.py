# event guests models
from datetime import datetime
from enum import StrEnum
from sqlalchemy import DateTime, ForeignKeyConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.organizationMembership import utc_now

class EventGuestStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    INVITED = "invited"
    REGISTERED = "registered"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"
    DECLINED = "declined"

class InvitationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class EventGuestResponse(SQLModel):
    id: int
    event_id: int
    guest_id: int
    access_level_id: int | None
    registration_number: str | None
    registration_status: EventGuestStatus
    invitation_status: InvitationStatus
    registered_at: datetime | None
    approved_at: datetime | None
    custom_field_values: str | None
    created_at: datetime
    updated_at: datetime

class EventGuest(SQLModel, table=True):
    __tablename__ = "event_guests"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "guest_id",
            name="uq_event_guest",
        ),
        ForeignKeyConstraint(
            ["event_id", "access_level_id"],
            ["event_access_levels.event_id", "event_access_levels.id"],
            name="fk_event_guest_access_level_same_event",
        ),
    )

    id: int | None = Field(
        default=None,
        primary_key=True,
    )

    event_id: int = Field(
        foreign_key="events.id",
        nullable=False,
        index=True,
    )
    guest_id: int = Field(
        foreign_key="guests.id",
        nullable=False,
        index=True,
    )
    access_level_id: int | None = Field(
        foreign_key="event_access_levels.id",
        nullable=True,
        index=True,
    )
    registration_number: str | None = Field(max_length=100, nullable=True)
    registered_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    custom_field_values: str | None = Field(default=None, max_length=10000)
    registration_status: EventGuestStatus = Field(
        default=EventGuestStatus.INVITED,
        sa_column_kwargs={"server_default": EventGuestStatus.INVITED.value},
        nullable=False,
    )
    invitation_status: InvitationStatus = Field(
        default=InvitationStatus.PENDING,
        sa_column_kwargs={"server_default": InvitationStatus.PENDING.value},
        nullable=False,
    )
   
    created_by: int | None = Field(
        foreign_key="users.id",
        nullable=True,
        index=True,
    )
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