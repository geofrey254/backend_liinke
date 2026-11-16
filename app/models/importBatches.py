# import batches models
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Column, DateTime, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ImportBatchStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    MAPPING = "mapping"
    VALIDATING = "validating"
    READY_FOR_REVIEW = "ready_for_review"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ImportBatch(SQLModel, table=True):
    __tablename__ = "import_batches"

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "original_file_name",
            name="uq_import_batches_organization_name",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)

    organization_id: int = Field(
        foreign_key="organizations.id",
        nullable=False,
        index=True,
    )

    event_id: int | None = Field(
        foreign_key="events.id",
        nullable=True,
        index=True,
    )

    uploaded_by_id: int = Field(
        foreign_key="users.id",
        nullable=False,
        index=True,
    )

    original_file_name: str = Field(max_length=255, nullable=False)

    file_storage_key: str = Field(max_length=255, nullable=False)

    file_type: str = Field(max_length=50, nullable=False)

    total_rows: int = Field(nullable=False)

    valid_rows: int = Field(nullable=False, default=0)

    invalid_rows: int = Field(nullable=False, default=0)

    duplicate_rows: int = Field(nullable=False, default=0)

    status: ImportBatchStatus = Field(
        default=ImportBatchStatus.UPLOADED,
        sa_column_kwargs={"server_default": ImportBatchStatus.UPLOADED.value},
        nullable=False,
    )

    column_mappings: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    started_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )

    completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )


class ImportBatchResponse(SQLModel):
    id: int
    organization_id: int
    event_id: int | None
    uploaded_by_id: int
    original_file_name: str
    file_type: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    status: ImportBatchStatus
    created_at: datetime