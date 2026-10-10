"""add creation month index

Revision ID: 20260730_month_idx
Revises: c95d85d3adf4
Create Date: 2026-07-30 00:00:00.000000
"""

from alembic import op, context
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260730_month_idx'
down_revision = 'c95d85d3adf4'
branch_labels = None
depend_on = None


def upgrade() -> None:
    # The initial schema already indexes creation_date; date_trunc is not immutable in PostgreSQL.
    pass


def downgrade() -> None:
    pass
