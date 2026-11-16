"""Complete guest registration integrity and lifecycle

Revision ID: f1c7d9e3a210
Revises: edabece94f18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1c7d9e3a210"
down_revision: Union[str, Sequence[str], None] = "edabece94f18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("guests", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("guests", sa.Column("last_name", sa.String(length=100), nullable=True))
    op.drop_constraint("uq_organization_guest_email", "guests", type_="unique")
    op.create_index("ix_guests_organization_email", "guests", ["organization_id", "email"])

    op.add_column(
        "event_guests",
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_guests",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_guests",
        sa.Column("custom_field_values", sa.String(length=10000), nullable=True),
    )
    op.create_unique_constraint(
        "uq_event_access_levels_event_id_id",
        "event_access_levels",
        ["event_id", "id"],
    )
    op.create_foreign_key(
        "fk_event_guest_access_level_same_event",
        "event_guests",
        "event_access_levels",
        ["event_id", "access_level_id"],
        ["event_id", "id"],
    )

    for label in ("DRAFT", "PENDING_APPROVAL", "APPROVED", "DECLINED"):
        op.execute(
            sa.text(
                "ALTER TYPE eventgueststatus ADD VALUE IF NOT EXISTS "
                f"'{label}'"
            )
        )


def downgrade() -> None:
    op.drop_constraint(
        "fk_event_guest_access_level_same_event",
        "event_guests",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_event_access_levels_event_id_id",
        "event_access_levels",
        type_="unique",
    )
    op.drop_column("event_guests", "custom_field_values")
    op.drop_column("event_guests", "approved_at")
    op.drop_column("event_guests", "registered_at")
    op.drop_index("ix_guests_organization_email", table_name="guests")
    op.create_unique_constraint(
        "uq_organization_guest_email",
        "guests",
        ["organization_id", "email"],
    )
    op.drop_column("guests", "last_name")
    op.drop_column("guests", "first_name")
