import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.target_role import utc_now


class SourceFileStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SourceFile(Base):
    __tablename__ = "source_files"
    __table_args__ = (
        CheckConstraint(
            "parse_status IN ('pending', 'running', 'succeeded', 'failed')",
            name="source_file_parse_status",
        ),
        CheckConstraint("size_bytes >= 0", name="source_file_size_bytes"),
        CheckConstraint("attempt_count >= 0", name="source_file_attempt_count"),
        CheckConstraint("max_attempts BETWEEN 1 AND 10", name="source_file_max_attempts"),
        Index("ix_source_files_parse_queue", "parse_status", "available_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), unique=True, index=True
    )
    object_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    declared_mime_type: Mapped[str] = mapped_column(String(255))
    detected_media_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    parse_status: Mapped[SourceFileStatus] = mapped_column(
        SqlEnum(
            SourceFileStatus,
            name="source_file_parse_status",
            native_enum=False,
            length=16,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        default=SourceFileStatus.PENDING,
    )
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
