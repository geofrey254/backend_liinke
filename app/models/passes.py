# passes models
import enum
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import model_validator
from sqlalchemy import DateTime, Text, CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

class PassStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"

class Pass(SQLModel, table=True):
    __tablename__ = "passes"

    __table_args__ = (
        UniqueConstraint(
            "event_guest_id", "code",
            name="uq_passes_event_guest_code",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)

    event_guest_id: int = Field(
        foreign_key="event_guests.id",
        nullable=False,
        index=True,
    )

    code: str = Field(max_length=100, nullable=False)

    pass_token_hash: str = Field(max_length=255, nullable=False)

    status: PassStatus = Field(
        default=PassStatus.ACTIVE,
        sa_column_kwargs={"server_default": PassStatus.ACTIVE.value},
        nullable=False,
    )

    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )

    expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )