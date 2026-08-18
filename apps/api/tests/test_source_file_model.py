import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.source_file import SourceFile, SourceFileStatus
from app.models.target_role import RecruitmentStage, TargetRole


def make_job(role_id: uuid.UUID, *, status: JobPostingStatus, original_text: str) -> JobPosting:
    return JobPosting(
        target_role_id=role_id,
        company_name="示例科技",
        job_title="数据分析实习生",
        recruitment_stage=RecruitmentStage.DAILY_INTERNSHIP,
        original_text=original_text,
        status=status,
    )


def test_source_file_persists_queue_metadata_and_allows_extracting_job_without_text() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        role = TargetRole(
            name="数据分析",
            recruitment_stage=RecruitmentStage.DAILY_INTERNSHIP,
        )
        session.add(role)
        session.flush()
        job = make_job(role.id, status=JobPostingStatus.EXTRACTING, original_text="")
        session.add(job)
        session.flush()
        source = SourceFile(
            job_posting_id=job.id,
            object_key=f"source-files/{uuid.uuid4().hex}",
            original_filename="岗位.md",
            declared_mime_type="text/markdown",
            detected_media_type="text/markdown",
            size_bytes=12,
            sha256="a" * 64,
            max_attempts=3,
            available_at=datetime.now(UTC),
        )
        session.add(source)
        session.flush()

        assert source.parse_status == SourceFileStatus.PENDING
        assert source.attempt_count == 0

    engine.dispose()


def test_draft_job_cannot_persist_empty_original_text() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        role = TargetRole(
            name="数据分析",
            recruitment_stage=RecruitmentStage.DAILY_INTERNSHIP,
        )
        session.add(role)
        session.flush()
        session.add(make_job(role.id, status=JobPostingStatus.DRAFT, original_text=""))

        with pytest.raises(IntegrityError):
            session.flush()

    engine.dispose()


def test_extracting_job_allows_metadata_to_be_identified_later() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        role = TargetRole(name="数据分析", recruitment_stage=RecruitmentStage.DAILY_INTERNSHIP)
        session.add(role)
        session.flush()
        job = JobPosting(
            target_role_id=role.id,
            company_name=None,
            job_title=None,
            recruitment_stage=RecruitmentStage.DAILY_INTERNSHIP,
            original_text="",
            status=JobPostingStatus.EXTRACTING,
        )
        session.add(job)
        session.flush()

        assert job.company_name is None
        assert job.job_title is None

    engine.dispose()


def test_job_can_persist_multiple_ordered_source_files() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        role = TargetRole(name="数据分析", recruitment_stage=RecruitmentStage.DAILY_INTERNSHIP)
        session.add(role)
        session.flush()
        job = make_job(role.id, status=JobPostingStatus.EXTRACTING, original_text="")
        session.add(job)
        session.flush()
        for index in range(2):
            session.add(
                SourceFile(
                    job_posting_id=job.id,
                    sequence_index=index,
                    object_key=f"source-files/{uuid.uuid4().hex}",
                    original_filename=f"岗位-{index}.png",
                    declared_mime_type="image/png",
                    detected_media_type="image/png",
                    size_bytes=12,
                    sha256=str(index) * 64,
                    max_attempts=3,
                    available_at=datetime.now(UTC),
                )
            )
        session.flush()

        sources = session.query(SourceFile).order_by(SourceFile.sequence_index).all()
        assert [source.sequence_index for source in sources] == [0, 1]
        assert [source.extracted_text for source in sources] == [None, None]

    engine.dispose()
