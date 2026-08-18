import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis_run import AnalysisRun, AnalysisRunStatus
from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.source_file import SourceFile, SourceFileStatus
from app.schemas.job_posting import JobPostingCreate, JobPostingMetadataUpdate
from app.services.analysis import enqueue_ai_analysis_run_locked
from app.storage.contracts import ObjectStore


def create_job_posting(
    session: Session,
    target_role_id: uuid.UUID,
    payload: JobPostingCreate,
) -> JobPosting:
    job_posting = JobPosting(
        target_role_id=target_role_id,
        company_name=payload.company_name,
        job_title=payload.job_title,
        recruitment_stage=payload.recruitment_stage,
        city=payload.city,
        source_url=str(payload.source_url) if payload.source_url else None,
        original_text=payload.original_text,
    )
    session.add(job_posting)
    session.commit()
    session.refresh(job_posting)
    return job_posting


def list_job_postings(
    session: Session,
    target_role_id: uuid.UUID,
    *,
    offset: int,
    limit: int,
) -> tuple[list[JobPosting], int]:
    condition = JobPosting.target_role_id == target_role_id
    items = list(
        session.scalars(
            select(JobPosting)
            .where(condition)
            .order_by(JobPosting.created_at.desc(), JobPosting.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    total = session.scalar(select(func.count()).select_from(JobPosting).where(condition)) or 0
    return items, total


def get_job_posting(session: Session, job_id: uuid.UUID) -> JobPosting | None:
    return session.get(JobPosting, job_id)


def update_job_metadata(
    session: Session,
    job: JobPosting,
    payload: JobPostingMetadataUpdate,
) -> JobPosting:
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        if field_name == "source_url" and value is not None:
            value = str(value)
        setattr(job, field_name, value)
    session.commit()
    session.refresh(job)
    return job


def retry_failed_job(
    session: Session,
    *,
    job_id: uuid.UUID,
    model_provider: str,
    model_name: str,
    analysis_max_attempts: int,
) -> tuple[JobPosting, list[SourceFile], AnalysisRun | None] | None:
    job = session.scalar(
        select(JobPosting).where(JobPosting.id == job_id).with_for_update()
    )
    if job is None or job.status != JobPostingStatus.FAILED:
        return None
    sources = list(
        session.scalars(
            select(SourceFile)
            .where(SourceFile.job_posting_id == job.id)
            .order_by(SourceFile.sequence_index.asc())
            .with_for_update()
        )
    )
    failed_sources = [
        source for source in sources if source.parse_status == SourceFileStatus.FAILED
    ]
    run = None
    if failed_sources:
        for source in failed_sources:
            source.parse_status = SourceFileStatus.PENDING
            source.error_code = None
            source.attempt_count = 0
            source.available_at = source.created_at
            source.lease_expires_at = None
            source.worker_id = None
            source.completed_at = None
        job.status = JobPostingStatus.EXTRACTING
    else:
        latest_run = session.scalar(
            select(AnalysisRun)
            .where(AnalysisRun.job_posting_id == job.id)
            .order_by(AnalysisRun.version.desc())
            .with_for_update()
            .limit(1)
        )
        if latest_run is None or latest_run.status != AnalysisRunStatus.FAILED:
            return None
        run = enqueue_ai_analysis_run_locked(
            session,
            job,
            model_provider=model_provider,
            model_name=model_name,
            max_attempts=analysis_max_attempts,
        )
        if run is None:
            return None
    session.commit()
    session.refresh(job)
    if run is not None:
        session.refresh(run)
    return job, sources, run


def delete_job_posting(
    session: Session,
    job_posting: JobPosting,
    *,
    store: ObjectStore,
) -> None:
    source_files = list(
        session.scalars(select(SourceFile).where(SourceFile.job_posting_id == job_posting.id))
    )
    for source_file in source_files:
        store.delete(source_file.object_key)
    session.delete(job_posting)
    session.commit()
