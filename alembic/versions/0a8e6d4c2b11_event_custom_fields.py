"""Add event custom fields for guest registration

Revision ID: 0a8e6d4c2b11
Revises: f1c7d9e3a210
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0a8e6d4c2b11"
down_revision: Union[str, Sequence[str], None] = "f1c7d9e3a210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS event_custom_fields (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id),
            field_key VARCHAR(100) NOT NULL,
            label VARCHAR(200) NOT NULL,
            field_type VARCHAR(30) NOT NULL,
            required BOOLEAN NOT NULL DEFAULT FALSE,
            options TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            CONSTRAINT uq_event_custom_field_key UNIQUE (event_id, field_key)
        )
    """))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_event_custom_fields_event_id "
        "ON event_custom_fields (event_id)"
    ))


def downgrade() -> None:
    op.drop_table("event_custom_fields")
