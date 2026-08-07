"""add ai analysis metadata

Revision ID: 8f4ec80d7e21
Revises: c7d3e82a4f19
Create Date: 2026-08-06 23:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8f4ec80d7e21"
down_revision: str | None = "c7d3e82a4f19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("analysis_runs", sa.Column("model_provider", sa.String(50), nullable=True))
    op.add_column("analysis_runs", sa.Column("model_name", sa.String(100), nullable=True))
    op.add_column("analysis_runs", sa.Column("prompt_version", sa.String(50), nullable=True))
    op.add_column("analysis_runs", sa.Column("schema_version", sa.String(20), nullable=True))
    op.add_column("analysis_runs", sa.Column("error_code", sa.String(100), nullable=True))
    op.add_column(
        "analysis_runs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_runs", "completed_at")
    op.drop_column("analysis_runs", "started_at")
    op.drop_column("analysis_runs", "error_code")
    op.drop_column("analysis_runs", "schema_version")
    op.drop_column("analysis_runs", "prompt_version")
    op.drop_column("analysis_runs", "model_name")
    op.drop_column("analysis_runs", "model_provider")

