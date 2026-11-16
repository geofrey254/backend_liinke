# import rows model
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Column, DateTime, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

class ImportRowStatus(StrEnum):
    PENDING = "pending"
    VALIDATED = "validated"
    INVALID = "invalid"
    PROCESSED = "processed"
    FAILED = "failed"

class ImportRow(SQLModel, table=True):
    __tablename__ = "import_rows"

    __table_args__ = (
        UniqueConstraint(
            "import_batch_id", "row_number",
            name="uq_import_rows_batch_row_number",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)

    import_batch_id: int = Field(
        foreign_key="import_batches.id",
        nullable=False,
        index=True,
    )

    row_number: int = Field(nullable=False)

    raw_data: str = Field(sa_column=Column(Text, nullable=False))

    normalized_data: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    matched_guest_id: int | None = Field(
        foreign_key="guests.id",
        nullable=True,
        index=True,
    )

    created_event_guest_id: int | None = Field(
        foreign_key="event_guests.id",
        nullable=True,
        index=True,
    )

    status: ImportRowStatus = Field(
        default=ImportRowStatus.PENDING,
        sa_column_kwargs={"server_default": ImportRowStatus.PENDING.value},
        nullable=False,
    )

    errors: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    warnings: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )


class ImportRowResponse(SQLModel):
    id: int
    import_batch_id: int
    row_number: int
    raw_data: str
    normalized_data: str | None
    matched_guest_id: int | None
    created_event_guest_id: int | None
    status: ImportRowStatus
    errors: str | None
    warnings: str | None