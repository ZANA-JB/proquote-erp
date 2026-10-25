"""Add explicit quotation VAT and payment terms.

Revision ID: 20261026_quote_tax_terms
Revises: 20261025_incoterm_string
Create Date: 2026-10-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261026_quote_tax_terms"
down_revision: Union[str, Sequence[str], None] = "20261025_incoterm_string"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quotations",
        sa.Column(
            "vat_mode",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'sans_tva'"),
        ),
    )
    op.add_column("quotations", sa.Column("vat_code", sa.String(length=100), nullable=True))
    op.add_column("quotations", sa.Column("vat_rate", sa.Numeric(5, 2), nullable=True))
    op.add_column("quotations", sa.Column("payment_method", sa.String(length=250), nullable=True))
    op.add_column("quotations", sa.Column("payment_terms", sa.String(length=500), nullable=True))


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade is disabled to prevent deleting saved quotation tax or payment information."
    )
