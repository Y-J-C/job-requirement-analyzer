"""add durable analysis queue

Revision ID: 2f9c3a6b7d10
Revises: 8f4ec80d7e21
Create Date: 2026-08-08 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2f9c3a6b7d10"
down_revision: str | None = "8f4ec80d7e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
    )
    op.add_column(
        "analysis_runs",
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("worker_id", sa.String(100), nullable=True),
    )
    op.create_check_constraint(
        "analysis_run_attempt_count",
        "analysis_runs",
        "attempt_count >= 0",
    )
    op.create_check_constraint(
        "analysis_run_max_attempts",
        "analysis_runs",
        "max_attempts BETWEEN 1 AND 10",
    )
    op.create_index(
        "uq_analysis_runs_one_active_task_per_job",
        "analysis_runs",
        ["job_posting_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )

    op.add_column(
        "job_postings",
        sa.Column("active_analysis_run_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "job_postings_active_analysis_run_id_fkey",
        "job_postings",
        "analysis_runs",
        ["active_analysis_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_job_postings_active_analysis_run_id"),
        "job_postings",
        ["active_analysis_run_id"],
        unique=False,
    )
    op.execute(
        """
        UPDATE job_postings AS job
        SET active_analysis_run_id = confirmed_run.id
        FROM (
            SELECT DISTINCT ON (run.job_posting_id)
                run.job_posting_id,
                run.id
            FROM analysis_runs AS run
            JOIN requirement_items AS item ON item.analysis_run_id = run.id
            WHERE item.user_confirmed IS TRUE
            ORDER BY run.job_posting_id, run.version DESC
        ) AS confirmed_run
        WHERE job.id = confirmed_run.job_posting_id
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_job_postings_active_analysis_run_id"),
        table_name="job_postings",
    )
    op.drop_constraint(
        "job_postings_active_analysis_run_id_fkey",
        "job_postings",
        type_="foreignkey",
    )
    op.drop_column("job_postings", "active_analysis_run_id")
    op.drop_index(
        "uq_analysis_runs_one_active_task_per_job",
        table_name="analysis_runs",
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )
    op.drop_constraint("analysis_run_max_attempts", "analysis_runs", type_="check")
    op.drop_constraint("analysis_run_attempt_count", "analysis_runs", type_="check")
    op.drop_column("analysis_runs", "worker_id")
    op.drop_column("analysis_runs", "lease_expires_at")
    op.drop_column("analysis_runs", "available_at")
    op.drop_column("analysis_runs", "max_attempts")
    op.drop_column("analysis_runs", "attempt_count")
