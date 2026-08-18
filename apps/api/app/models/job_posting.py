import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.target_role import RecruitmentStage, utc_now


class JobPostingStatus(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    REVIEW_REQUIRED = "review_required"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (
        CheckConstraint(
            "recruitment_stage IN ('daily_internship', 'summer_internship', "
            "'winter_internship', 'autumn_recruitment', 'spring_recruitment', 'other')",
            name="job_posting_recruitment_stage",
        ),
        CheckConstraint(
            "status IN ('draft', 'queued', 'extracting', 'analyzing', "
            "'review_required', 'confirmed', 'failed')",
            name="job_posting_status",
        ),
        CheckConstraint(
            "length(trim(original_text)) > 0 OR status IN ('extracting', 'failed')",
            name="job_posting_original_text_required",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    active_analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "analysis_runs.id",
            name="job_postings_active_analysis_run_id_fkey",
            use_alter=True,
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    target_role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("target_roles.id", ondelete="CASCADE"),
        index=True,
    )
    company_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    recruitment_stage: Mapped[RecruitmentStage] = mapped_column(
        SqlEnum(
            RecruitmentStage,
            name="job_posting_recruitment_stage",
            native_enum=False,
            length=32,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        )
    )
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    original_text: Mapped[str] = mapped_column(Text)
    status: Mapped[JobPostingStatus] = mapped_column(
        SqlEnum(
            JobPostingStatus,
            name="job_posting_status",
            native_enum=False,
            length=32,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        default=JobPostingStatus.DRAFT,
    )
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
