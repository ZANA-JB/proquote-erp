"""Merge the existing independent schema revisions.

Revision ID: 20260930_merge_heads
Revises: 20260730_client_addr, 20260730_month_idx
Create Date: 2026-09-30
"""

from typing import Sequence, Union


revision: str = "20260930_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "20260730_client_addr",
    "20260730_month_idx",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
