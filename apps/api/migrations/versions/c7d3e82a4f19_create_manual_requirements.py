"""create manual requirements

Revision ID: c7d3e82a4f19
Revises: 6ac022492f81
Create Date: 2026-08-06 21:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d3e82a4f19"
down_revision: str | None = "6ac022492f81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_posting_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "succeeded",
                "failed",
                "superseded",
                name="analysis_run_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "manual",
                "ai",
                name="analysis_run_source",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'superseded')",
            name="analysis_run_status",
        ),
        sa.CheckConstraint("source IN ('manual', 'ai')", name="analysis_run_source"),
        sa.ForeignKeyConstraint(
            ["job_posting_id"],
            ["job_postings.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_posting_id",
            "version",
            name="analysis_run_job_version",
        ),
    )
    op.create_index(
        op.f("ix_analysis_runs_job_posting_id"),
        "analysis_runs",
        ["job_posting_id"],
        unique=False,
    )
    op.create_table(
        "requirement_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.String(length=200), nullable=False),
        sa.Column(
            "requirement_type",
            sa.Enum(
                "eligibility",
                "core_competency",
                "experience",
                "preferred",
                "uncertain",
                name="requirement_item_type",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "explicitness",
            sa.Enum(
                "explicit",
                "implicit",
                "uncertain",
                name="requirement_item_explicitness",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("user_confirmed", sa.Boolean(), nullable=False),
        sa.Column("user_modified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "requirement_type IN ('eligibility', 'core_competency', 'experience', "
            "'preferred', 'uncertain')",
            name="requirement_item_type",
        ),
        sa.CheckConstraint(
            "explicitness IN ('explicit', 'implicit', 'uncertain')",
            name="requirement_item_explicitness",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="requirement_item_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_requirement_items_analysis_run_id"),
        "requirement_items",
        ["analysis_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_requirement_items_analysis_run_id"),
        table_name="requirement_items",
    )
    op.drop_table("requirement_items")
    op.drop_index(
        op.f("ix_analysis_runs_job_posting_id"),
        table_name="analysis_runs",
    )
    op.drop_table("analysis_runs")
