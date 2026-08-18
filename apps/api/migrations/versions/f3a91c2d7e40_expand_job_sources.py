"""expand job sources for automatic intake

Revision ID: f3a91c2d7e40
Revises: 7d41b82cf601
Create Date: 2026-08-08 21:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a91c2d7e40"
down_revision: str | Sequence[str] | None = "7d41b82cf601"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "job_postings", "company_name", existing_type=sa.String(100), nullable=True
    )
    op.alter_column(
        "job_postings", "job_title", existing_type=sa.String(150), nullable=True
    )
    op.drop_index("ix_source_files_job_posting_id", table_name="source_files")
    op.drop_constraint(
        "source_files_job_posting_id_key", "source_files", type_="unique"
    )
    op.add_column(
        "source_files",
        sa.Column("sequence_index", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "source_files", sa.Column("extracted_text", sa.Text(), nullable=True)
    )
    op.create_check_constraint(
        "source_file_sequence_index", "source_files", "sequence_index >= 0"
    )
    op.create_unique_constraint(
        "uq_source_files_job_sequence",
        "source_files",
        ["job_posting_id", "sequence_index"],
    )
    op.create_index(
        "ix_source_files_job_posting_id",
        "source_files",
        ["job_posting_id"],
        unique=False,
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM source_files GROUP BY job_posting_id HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'cannot downgrade while jobs have multiple source files';
            END IF;
            IF EXISTS (
                SELECT 1 FROM job_postings WHERE company_name IS NULL OR job_title IS NULL
            ) THEN
                RAISE EXCEPTION 'cannot downgrade while job metadata is missing';
            END IF;
        END $$;
        """
    )
    op.drop_index("ix_source_files_job_posting_id", table_name="source_files")
    op.drop_constraint(
        "uq_source_files_job_sequence", "source_files", type_="unique"
    )
    op.drop_constraint("source_file_sequence_index", "source_files", type_="check")
    op.drop_column("source_files", "extracted_text")
    op.drop_column("source_files", "sequence_index")
    op.create_unique_constraint(
        "source_files_job_posting_id_key", "source_files", ["job_posting_id"]
    )
    op.create_index(
        "ix_source_files_job_posting_id",
        "source_files",
        ["job_posting_id"],
        unique=True,
    )
    op.alter_column(
        "job_postings", "job_title", existing_type=sa.String(150), nullable=False
    )
    op.alter_column(
        "job_postings", "company_name", existing_type=sa.String(100), nullable=False
    )
