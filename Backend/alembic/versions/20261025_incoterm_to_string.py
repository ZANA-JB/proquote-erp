"""Allow the quotation form's standard and custom incoterm values.

Revision ID: 20261025_incoterm_string
Revises: 20260930_auth_sec
Create Date: 2026-10-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261025_incoterm_string"
down_revision: Union[str, Sequence[str], None] = "20260930_auth_sec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    if dialect_name == "postgresql":
        op.alter_column(
            "quotations",
            "incoterm",
            existing_type=sa.Enum("CLIENT", "ENI", name="incoterm"),
            type_=sa.String(length=50),
            postgresql_using="incoterm::text",
        )
    elif dialect_name != "sqlite":
        raise RuntimeError(f"Unsupported database dialect for incoterm migration: {dialect_name}")


def downgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    if dialect_name == "postgresql":
        unsupported_value = op.get_bind().execute(
            sa.text(
                "SELECT incoterm FROM quotations "
                "WHERE incoterm IS NOT NULL AND incoterm NOT IN ('CLIENT', 'ENI') "
                "LIMIT 1"
            )
        ).scalar_one_or_none()
        if unsupported_value is not None:
            raise RuntimeError(
                "Cannot restore the incoterm enum while custom incoterm values exist."
            )
        op.alter_column(
            "quotations",
            "incoterm",
            existing_type=sa.String(length=50),
            type_=sa.Enum("CLIENT", "ENI", name="incoterm"),
            postgresql_using="incoterm::incoterm",
        )
    elif dialect_name != "sqlite":
        raise RuntimeError(f"Unsupported database dialect for incoterm migration: {dialect_name}")
