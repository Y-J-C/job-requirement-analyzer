import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.target_role import utc_now


class AnalysisRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class AnalysisRunSource(StrEnum):
    MANUAL = "manual"
    AI = "ai"


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint("job_posting_id", "version", name="analysis_run_job_version"),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'superseded')",
            name="analysis_run_status",
        ),
        CheckConstraint("source IN ('manual', 'ai')", name="analysis_run_source"),
        CheckConstraint("attempt_count >= 0", name="analysis_run_attempt_count"),
        CheckConstraint("max_attempts BETWEEN 1 AND 10", name="analysis_run_max_attempts"),
        Index(
            "uq_analysis_runs_one_active_task_per_job",
            "job_posting_id",
            unique=True,
            sqlite_where=text("status IN ('pending', 'running')"),
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[AnalysisRunStatus] = mapped_column(
        SqlEnum(
            AnalysisRunStatus,
            name="analysis_run_status",
            native_enum=False,
            length=32,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        default=AnalysisRunStatus.SUCCEEDED,
    )
    source: Mapped[AnalysisRunSource] = mapped_column(
        SqlEnum(
            AnalysisRunSource,
            name="analysis_run_source",
            native_enum=False,
            length=16,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        default=AnalysisRunSource.MANUAL,
    )
    model_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
