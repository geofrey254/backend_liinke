# passes models
import enum
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import model_validator
from sqlalchemy import DateTime, Text, CheckConstraint, UniqueConstraint, Index, text
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
        Index("ix_passes_download_token_hash", "download_token_hash", unique=True),
        Index(
            "uq_passes_one_active_per_event_guest",
            "event_guest_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
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
        sa_column_kwargs={"server_default": PassStatus.ACTIVE.name},
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

    download_token_hash: str | None = Field(default=None, max_length=255, nullable=True)
    qr_token_encrypted: str | None = Field(default=None, max_length=1000, nullable=True)
    download_token_encrypted: str | None = Field(default=None, max_length=1000, nullable=True)
    delivery_status: str = Field(default="not_sent", max_length=30, nullable=False)
    delivered_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True), nullable=True)
    template_version: int = Field(default=1, nullable=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )

class EventPassTemplate(SQLModel, table=True):
    __tablename__ = "event_pass_templates"

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", nullable=False, unique=True, index=True)
    design: str = Field(default="professional", max_length=30, nullable=False)
    orientation: str = Field(default="portrait", max_length=20, nullable=False)
    config_json: str = Field(default="{}", max_length=20000, nullable=False)
    version: int = Field(default=1, nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=DateTime(timezone=True), nullable=False)
