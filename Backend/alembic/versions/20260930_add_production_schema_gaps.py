"""Add ORM schema objects missing from the initial migrations.

Revision ID: 20260930_prod_gaps
Revises: 20260930_merge_heads
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260930_prod_gaps"
down_revision: Union[str, Sequence[str], None] = "20260930_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(), nullable=True))
    op.create_table(
        "access_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("nomComplet", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("motDePasse", sa.String(), nullable=False),
        sa.Column(
            "profilSouhaite",
            sa.Enum("COMMERCIAL", "MANAGER", name="accessprofile", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("EN_ATTENTE", "ACCEPTEE", "REFUSEE", name="accessrequeststatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_requests_email", "access_requests", ["email"], unique=False)
    op.create_index("ix_access_requests_id", "access_requests", ["id"], unique=True)
    op.create_index("ix_access_requests_status", "access_requests", ["status"], unique=False)
    op.drop_index("ix_reference_counters_name", table_name="reference_counters")


def downgrade() -> None:
    op.create_index("ix_reference_counters_name", "reference_counters", ["name"], unique=True)
    op.drop_index("ix_access_requests_status", table_name="access_requests")
    op.drop_index("ix_access_requests_id", table_name="access_requests")
    op.drop_index("ix_access_requests_email", table_name="access_requests")
    op.drop_table("access_requests")
    op.drop_column("users", "avatar_url")