"""Allow guest email to be optional

Revision ID: 1b6e8f4c2d10
Revises: 0a8e6d4c2b11
"""
from typing import Sequence, Union

from alembic import op


revision: str = "1b6e8f4c2d10"
down_revision: Union[str, Sequence[str], None] = "0a8e6d4c2b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("guests", "email", nullable=True)


def downgrade() -> None:
    op.alter_column("guests", "email", nullable=False)
