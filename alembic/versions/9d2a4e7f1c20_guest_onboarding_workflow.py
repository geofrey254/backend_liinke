"""Guest onboarding and spreadsheet import workflow

Revision ID: 9d2a4e7f1c20
Revises: 260ecab3d818
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d2a4e7f1c20"
down_revision: Union[str, Sequence[str], None] = "260ecab3d818"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20)),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("organization_name", sa.String(length=200)),
        sa.Column("job_title", sa.String(length=200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "email", name="uq_organization_guest_email"),
    )
    op.create_index("ix_guests_organization_id", "guests", ["organization_id"])
    op.create_index("ix_guests_email", "guests", ["email"])

    op.create_table(
        "event_guests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("guest_id", sa.Integer(), sa.ForeignKey("guests.id"), nullable=False),
        sa.Column("access_level_id", sa.Integer(), sa.ForeignKey("event_access_levels.id")),
        sa.Column("registration_number", sa.String(length=100)),
        sa.Column("registration_status", sa.String(length=30), nullable=False, server_default="invited"),
        sa.Column("invitation_status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", "guest_id", name="uq_event_guest"),
    )
    op.create_index("ix_event_guests_event_id", "event_guests", ["event_id"])
    op.create_index("ix_event_guests_guest_id", "event_guests", ["guest_id"])
    op.create_index("ix_event_guests_access_level_id", "event_guests", ["access_level_id"])
    op.create_index("ix_event_guests_created_by", "event_guests", ["created_by"])

    op.create_table(
        "passes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_guest_id", sa.Integer(), sa.ForeignKey("event_guests.id"), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("pass_token_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_guest_id", "code", name="uq_passes_event_guest_code"),
    )
    op.create_index("ix_passes_event_guest_id", "passes", ["event_guest_id"])

    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id")),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_file_name", sa.String(length=255), nullable=False),
        sa.Column("file_storage_key", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="uploaded"),
        sa.Column("column_mappings", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "original_file_name", name="uq_import_batches_organization_name"),
    )
    op.create_index("ix_import_batches_organization_id", "import_batches", ["organization_id"])
    op.create_index("ix_import_batches_event_id", "import_batches", ["event_id"])
    op.create_index("ix_import_batches_uploaded_by_id", "import_batches", ["uploaded_by_id"])

    op.create_table(
        "import_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_batch_id", sa.Integer(), sa.ForeignKey("import_batches.id"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data", sa.Text(), nullable=False),
        sa.Column("normalized_data", sa.Text()),
        sa.Column("matched_guest_id", sa.Integer(), sa.ForeignKey("guests.id")),
        sa.Column("created_event_guest_id", sa.Integer(), sa.ForeignKey("event_guests.id")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("errors", sa.Text()),
        sa.Column("warnings", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("import_batch_id", "row_number", name="uq_import_rows_batch_row_number"),
    )
    op.create_index("ix_import_rows_import_batch_id", "import_rows", ["import_batch_id"])
    op.create_index("ix_import_rows_matched_guest_id", "import_rows", ["matched_guest_id"])
    op.create_index("ix_import_rows_created_event_guest_id", "import_rows", ["created_event_guest_id"])


def downgrade() -> None:
    op.drop_table("import_rows")
    op.drop_table("import_batches")
    op.drop_table("passes")
    op.drop_table("event_guests")
    op.drop_table("guests")
