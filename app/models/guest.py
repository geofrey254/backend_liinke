from datetime import datetime

from pydantic import EmailStr, field_validator, model_validator
from sqlalchemy import DateTime, Index
from sqlmodel import Field, SQLModel

from app.models.organizationMembership import utc_now

class Guest(SQLModel, table=True):
    __tablename__ = "guests"
    __table_args__ = (
        Index("ix_guests_organization_email", "organization_id", "email"),
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
    full_name: str = Field(max_length=200, nullable=False)
    first_name: str | None = Field(default=None, max_length=100, nullable=True)
    last_name: str | None = Field(default=None, max_length=100, nullable=True)
    phone: str | None = Field(max_length=20, nullable=True)
    email: str | None = Field(default=None, max_length=200, nullable=True, index=True)
    organization_name: str | None = Field(max_length=200, nullable=True)
    job_title: str | None = Field(max_length=200, nullable=True)
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


class GuestCreate(SQLModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    organization_name: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)

    @field_validator("full_name", "first_name", "last_name", "phone", "organization_name", "job_title")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def build_full_name(self):
        if not self.full_name:
            parts = [part for part in (self.first_name, self.last_name) if part]
            self.full_name = " ".join(parts) or None
        if not self.full_name:
            raise ValueError("full_name or first_name/last_name is required")
        return self

class GuestResponse(SQLModel):
    id: int
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None
    organization_name: str | None = None
    job_title: str | None = None

class GuestUpdate(SQLModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    organization_name: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)

    @field_validator("full_name", "first_name", "last_name", "phone", "organization_name", "job_title")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

class GuestListResponse(SQLModel):
    guests: list[GuestResponse]