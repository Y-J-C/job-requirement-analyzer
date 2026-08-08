"""add source files

Revision ID: 7d41b82cf601
Revises: 2f9c3a6b7d10
Create Date: 2026-08-08 02:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d41b82cf601"
down_revision: str | Sequence[str] | None = "2f9c3a6b7d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "job_posting_original_text_required",
        "job_postings",
        "length(trim(original_text)) > 0 OR status IN ('extracting', 'failed')",
    )
    op.create_table(
        "source_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_posting_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("declared_mime_type", sa.String(length=255), nullable=False),
        sa.Column("detected_media_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("parse_status", sa.String(length=16), nullable=False),
        sa.Column("parser_version", sa.String(length=50), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worker_id", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt_count >= 0", name="source_file_attempt_count"),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 10", name="source_file_max_attempts"),
        sa.CheckConstraint(
            "parse_status IN ('pending', 'running', 'succeeded', 'failed')",
            name="source_file_parse_status",
        ),
        sa.CheckConstraint("size_bytes >= 0", name="source_file_size_bytes"),
        sa.ForeignKeyConstraint(["job_posting_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_posting_id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(
        "ix_source_files_job_posting_id", "source_files", ["job_posting_id"], unique=True
    )
    op.create_index(
        "ix_source_files_parse_queue", "source_files", ["parse_status", "available_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_source_files_parse_queue", table_name="source_files")
    op.drop_index("ix_source_files_job_posting_id", table_name="source_files")
    op.drop_table("source_files")
    op.drop_constraint(
        "job_posting_original_text_required", "job_postings", type_="check"
    )
