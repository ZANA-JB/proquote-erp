"""Add client_address to quotation

Revision ID: 20260730_client_addr
Revises: c95d85d3adf4
Create Date: 2026-07-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260730_client_addr'
down_revision = 'c95d85d3adf4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('quotations', sa.Column('client_address', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('quotations', 'client_address')
