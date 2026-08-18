"""add target role ownership

Revision ID: c84b26a90d11
Revises: f3a91c2d7e40
Create Date: 2026-08-09 18:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c84b26a90d11"
down_revision: str | Sequence[str] | None = "f3a91c2d7e40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "target_roles",
        sa.Column(
            "owner_subject",
            sa.String(length=255),
            server_default="legacy-local-user",
            nullable=False,
        ),
    )
    op.alter_column("target_roles", "owner_subject", server_default=None)
    op.create_index(
        "ix_target_roles_owner_subject",
        "target_roles",
        ["owner_subject"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_target_roles_owner_subject", table_name="target_roles")
    op.drop_column("target_roles", "owner_subject")
