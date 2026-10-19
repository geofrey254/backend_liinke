
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)

    organization_id: int = Field(
        foreign_key="organizations.id",
        index=True,
        nullable=False,
    )
    name: str = Field(index=True, max_length=200)
    description: str | None = None
    location: str | None = Field(default=None, max_length=300)

    start_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    end_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )

    status: str = Field(default="draft", index=True)

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
