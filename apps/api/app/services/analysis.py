import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.contracts import AnalyzeJobRequest, AnalyzeJobResult, AnalyzerError
from app.ai.deepseek import PROMPT_VERSION, SCHEMA_VERSION
from app.models.analysis_run import AnalysisRun, AnalysisRunSource, AnalysisRunStatus
from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.requirement_item import RequirementItem


@dataclass(frozen=True)
class ClaimedAnalysisRun:
    run_id: uuid.UUID
    request: AnalyzeJobRequest


def create_ai_analysis_run(
    session: Session,
    job: JobPosting,
    *,
    model_provider: str,
    model_name: str,
    max_attempts: int,
) -> AnalysisRun | None:
    locked_job = session.scalar(
        select(JobPosting).where(JobPosting.id == job.id).with_for_update()
    )
    if locked_job is None or locked_job.status not in {
        JobPostingStatus.DRAFT,
        JobPostingStatus.FAILED,
        JobPostingStatus.CONFIRMED,
    }:
        return None
    active_task = session.scalar(
        select(AnalysisRun.id).where(
            AnalysisRun.job_posting_id == job.id,
            AnalysisRun.status.in_([AnalysisRunStatus.PENDING, AnalysisRunStatus.RUNNING]),
        )
    )
    if active_task is not None:
        return None
    latest_version = session.scalar(
        select(func.max(AnalysisRun.version)).where(AnalysisRun.job_posting_id == job.id)
    )
    run = AnalysisRun(
        job_posting_id=job.id,
        version=(latest_version or 0) + 1,
        status=AnalysisRunStatus.PENDING,
        source=AnalysisRunSource.AI,
        model_provider=model_provider,
        model_name=model_name,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        max_attempts=max_attempts,
    )
    locked_job.status = JobPostingStatus.QUEUED
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_analysis_run(session: Session, run_id: uuid.UUID) -> AnalysisRun | None:
    return session.get(AnalysisRun, run_id)


def get_latest_analysis_run(session: Session, job_id: uuid.UUID) -> AnalysisRun | None:
    return session.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.job_posting_id == job_id)
        .order_by(AnalysisRun.version.desc())
        .limit(1)
    )


def recover_stale_analysis_runs(session: Session, *, now: datetime) -> int:
    stale_runs = list(
        session.scalars(
            select(AnalysisRun)
            .where(
                AnalysisRun.status == AnalysisRunStatus.RUNNING,
                AnalysisRun.lease_expires_at <= now,
            )
            .with_for_update(skip_locked=True)
        )
    )
    for run in stale_runs:
        job = session.get(JobPosting, run.job_posting_id)
        run.worker_id = None
        run.lease_expires_at = None
        if run.attempt_count >= run.max_attempts:
            run.status = AnalysisRunStatus.FAILED
            run.error_code = "worker_lease_expired"
            run.completed_at = now
            if job is not None:
                job.status = JobPostingStatus.FAILED
        else:
            run.status = AnalysisRunStatus.PENDING
            run.available_at = now
            run.error_code = "worker_lease_expired"
            if job is not None:
                job.status = JobPostingStatus.QUEUED
    if stale_runs:
        session.commit()
    return len(stale_runs)


def claim_next_analysis_run(
    session: Session,
    *,
    worker_id: str,
    now: datetime,
    lease_seconds: int,
) -> ClaimedAnalysisRun | None:
    recover_stale_analysis_runs(session, now=now)
    run = session.scalar(
        select(AnalysisRun)
        .where(
            AnalysisRun.status == AnalysisRunStatus.PENDING,
            AnalysisRun.available_at <= now,
        )
        .order_by(AnalysisRun.available_at.asc(), AnalysisRun.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if run is None:
        return None
    job = session.get(JobPosting, run.job_posting_id)
    if job is None:
        run.status = AnalysisRunStatus.FAILED
        run.error_code = "job_not_found"
        run.completed_at = now
        session.commit()
        return None

    run.status = AnalysisRunStatus.RUNNING
    run.attempt_count += 1
    run.started_at = run.started_at or now
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    run.worker_id = worker_id[:100]
    job.status = JobPostingStatus.ANALYZING
    request = AnalyzeJobRequest(
        company_name=job.company_name,
        job_title=job.job_title,
        original_text=job.original_text,
    )
    session.commit()
    return ClaimedAnalysisRun(run_id=run.id, request=request)


def complete_analysis_run(
    session: Session,
    *,
    run_id: uuid.UUID,
    worker_id: str,
    result: AnalyzeJobResult,
    now: datetime,
) -> None:
    run = session.scalar(
        select(AnalysisRun)
        .where(
            AnalysisRun.id == run_id,
            AnalysisRun.status == AnalysisRunStatus.RUNNING,
            AnalysisRun.worker_id == worker_id[:100],
        )
        .with_for_update()
    )
    if run is None:
        return
    job = session.get(JobPosting, run.job_posting_id)
    for extracted in result.requirements:
        session.add(
            RequirementItem(
                analysis_run_id=run.id,
                original_text=extracted.source_text,
                normalized_name=extracted.normalized_name,
                requirement_type=extracted.requirement_type,
                explicitness=extracted.explicitness,
                confidence=extracted.confidence,
                user_confirmed=False,
                user_modified=False,
            )
        )
    run.status = AnalysisRunStatus.SUCCEEDED
    run.error_code = None
    run.completed_at = now
    run.lease_expires_at = None
    run.worker_id = None
    if job is not None:
        job.status = JobPostingStatus.REVIEW_REQUIRED
    session.commit()


def fail_or_retry_analysis_run(
    session: Session,
    *,
    run_id: uuid.UUID,
    worker_id: str,
    error_code: str,
    retryable: bool,
    now: datetime,
    retry_delay_seconds: int,
) -> None:
    run = session.scalar(
        select(AnalysisRun)
        .where(
            AnalysisRun.id == run_id,
            AnalysisRun.status == AnalysisRunStatus.RUNNING,
            AnalysisRun.worker_id == worker_id[:100],
        )
        .with_for_update()
    )
    if run is None:
        return
    job = session.get(JobPosting, run.job_posting_id)
    run.error_code = error_code
    run.lease_expires_at = None
    run.worker_id = None
    if retryable and run.attempt_count < run.max_attempts:
        run.status = AnalysisRunStatus.PENDING
        backoff = retry_delay_seconds * (2 ** (run.attempt_count - 1))
        run.available_at = now + timedelta(seconds=backoff)
        if job is not None:
            job.status = JobPostingStatus.QUEUED
    else:
        run.status = AnalysisRunStatus.FAILED
        run.completed_at = now
        if job is not None:
            job.status = JobPostingStatus.FAILED
    session.commit()


def execute_claimed_analysis(
    session_factory,
    claimed: ClaimedAnalysisRun,
    analyzer,
    *,
    worker_id: str,
    now: datetime | None,
    retry_delay_seconds: int,
) -> None:
    try:
        result = analyzer.analyze(claimed.request)
    except AnalyzerError as error:
        finished_at = now or datetime.now(UTC)
        with session_factory() as session:
            fail_or_retry_analysis_run(
                session,
                run_id=claimed.run_id,
                worker_id=worker_id,
                error_code=error.code,
                retryable=error.code == "provider_request_failed",
                now=finished_at,
                retry_delay_seconds=retry_delay_seconds,
            )
    except Exception:
        finished_at = now or datetime.now(UTC)
        with session_factory() as session:
            fail_or_retry_analysis_run(
                session,
                run_id=claimed.run_id,
                worker_id=worker_id,
                error_code="internal_analysis_error",
                retryable=True,
                now=finished_at,
                retry_delay_seconds=retry_delay_seconds,
            )
    else:
        finished_at = now or datetime.now(UTC)
        with session_factory() as session:
            complete_analysis_run(
                session,
                run_id=claimed.run_id,
                worker_id=worker_id,
                result=result,
                now=finished_at,
            )
