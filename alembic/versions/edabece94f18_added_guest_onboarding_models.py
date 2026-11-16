"""added guest onboarding models

Revision ID: edabece94f18
Revises: 9d2a4e7f1c20
Create Date: 2026-11-16 13:55:01.005426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edabece94f18'
down_revision: Union[str, Sequence[str], None] = '9d2a4e7f1c20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("event_access_levels", sa.Column("color", sa.String(length=7), nullable=True))

    enum_definitions = {
        "eventgueststatus": ("INVITED", "REGISTERED", "CONFIRMED", "CANCELLED", "CHECKED_IN"),
        "invitationstatus": ("PENDING", "SENT", "ACCEPTED", "DECLINED"),
        "importbatchstatus": (
            "UPLOADED", "PARSING", "MAPPING", "VALIDATING", "READY_FOR_REVIEW",
            "PROCESSING", "COMPLETED", "PARTIALLY_COMPLETED", "FAILED", "CANCELLED",
        ),
        "importrowstatus": ("PENDING", "VALIDATED", "INVALID", "PROCESSED", "FAILED"),
        "passstatus": ("ACTIVE", "REVOKED", "EXPIRED"),
    }
    for name, labels in enum_definitions.items():
        labels_sql = ", ".join(f"'{label}'" for label in labels)
        op.execute(sa.text(
            f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({labels_sql}); "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        ))

    columns = (
        ("event_guests", "registration_status", "eventgueststatus", "INVITED"),
        ("event_guests", "invitation_status", "invitationstatus", "PENDING"),
        ("import_batches", "status", "importbatchstatus", "UPLOADED"),
        ("import_rows", "status", "importrowstatus", "PENDING"),
        ("passes", "status", "passstatus", "ACTIVE"),
    )
    for table, column, enum_name, default in columns:
        op.alter_column(table, column, server_default=None)
        op.execute(sa.text(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {enum_name} "
            f"USING upper({column})::{enum_name}"
        ))
        op.alter_column(table, column, server_default=sa.text(f"'{default}'::{enum_name}"))


def downgrade() -> None:
    """Downgrade schema."""
    columns = (
        ("passes", "status", "passstatus"),
        ("import_rows", "status", "importrowstatus"),
        ("import_batches", "status", "importbatchstatus"),
        ("event_guests", "invitation_status", "invitationstatus"),
        ("event_guests", "registration_status", "eventgueststatus"),
    )
    for table, column, enum_name in columns:
        op.alter_column(table, column, server_default=None)
        op.execute(sa.text(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR(30) "
            f"USING lower({column}::text)"
        ))
    for enum_name in ("passstatus", "importrowstatus", "importbatchstatus", "invitationstatus", "eventgueststatus"):
        op.execute(sa.text(f"DROP TYPE {enum_name}"))
    op.drop_column("event_access_levels", "color")
