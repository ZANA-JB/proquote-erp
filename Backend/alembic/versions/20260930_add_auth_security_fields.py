"""Add revocable-token version and hash stored access-request passwords.

Revision ID: 20260930_auth_sec
Revises: 20260930_prod_gaps
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext


revision: str = "20260930_auth_sec"
down_revision: Union[str, Sequence[str], None] = "20260930_prod_gaps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
    )

    bind = op.get_bind()
    requests = sa.table(
        "access_requests",
        sa.column("id", sa.String()),
        sa.column("motDePasse", sa.String()),
        sa.column("status", sa.String()),
    )
    password_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        pbkdf2_sha256__rounds=600_000,
        deprecated="auto",
    )
    for row in bind.execute(sa.select(requests.c.id, requests.c.motDePasse, requests.c.status)):
        current_value = row.motDePasse or ""
        if row.status != "EN_ATTENTE":
            secure_value = ""
        elif current_value.startswith("$pbkdf2-sha256$"):
            secure_value = current_value
        else:
            secure_value = password_context.hash(current_value)
        bind.execute(
            requests.update().where(requests.c.id == row.id).values(motDePasse=secure_value)
        )


def downgrade() -> None:
    op.drop_column("users", "token_version")
