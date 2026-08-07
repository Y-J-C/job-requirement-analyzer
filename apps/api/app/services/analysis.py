import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.contracts import AnalyzeJobRequest, AnalyzerError, RequirementAnalyzer
from app.ai.deepseek import PROMPT_VERSION, SCHEMA_VERSION
from app.models.analysis_run import AnalysisRun, AnalysisRunSource, AnalysisRunStatus
from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.requirement_item import RequirementItem

SessionFactory = Callable[[], Session]


def create_ai_analysis_run(
    session: Session,
    job: JobPosting,
    analyzer: RequirementAnalyzer,
) -> AnalysisRun | None:
    locked_job = session.scalar(
        select(JobPosting).where(JobPosting.id == job.id).with_for_update()
    )
    if locked_job is None or locked_job.status not in {
        JobPostingStatus.DRAFT,
        JobPostingStatus.FAILED,
    }:
        return None
    active = session.scalar(
        select(AnalysisRun.id).where(
            AnalysisRun.job_posting_id == job.id,
            AnalysisRun.status.in_([AnalysisRunStatus.PENDING, AnalysisRunStatus.RUNNING]),
        )
    )
    if active is not None:
        return None
    latest_version = session.scalar(
        select(func.max(AnalysisRun.version)).where(AnalysisRun.job_posting_id == job.id)
    )
    run = AnalysisRun(
        job_posting_id=job.id,
        version=(latest_version or 0) + 1,
        status=AnalysisRunStatus.PENDING,
        source=AnalysisRunSource.AI,
        model_provider=analyzer.provider_name,
        model_name=analyzer.model_name,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    locked_job.status = JobPostingStatus.QUEUED
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_analysis_run(session: Session, run_id: uuid.UUID) -> AnalysisRun | None:
    return session.get(AnalysisRun, run_id)


def execute_ai_analysis(
    session_factory: SessionFactory,
    run_id: uuid.UUID,
    analyzer: RequirementAnalyzer,
) -> None:
    with session_factory() as session:
        run = session.get(AnalysisRun, run_id)
        if run is None:
            return
        job = session.get(JobPosting, run.job_posting_id)
        if job is None:
            return

        run.status = AnalysisRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        job.status = JobPostingStatus.ANALYZING
        session.commit()

        try:
            result = analyzer.analyze(
                AnalyzeJobRequest(
                    company_name=job.company_name,
                    job_title=job.job_title,
                    original_text=job.original_text,
                )
            )
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
            run.completed_at = datetime.now(UTC)
            job.status = JobPostingStatus.REVIEW_REQUIRED
            session.commit()
        except AnalyzerError as error:
            session.rollback()
            _mark_failed(session, run.id, error.code)
        except Exception:
            session.rollback()
            _mark_failed(session, run.id, "internal_analysis_error")


def _mark_failed(session: Session, run_id: uuid.UUID, error_code: str) -> None:
    run = session.get(AnalysisRun, run_id)
    if run is None:
        return
    job = session.get(JobPosting, run.job_posting_id)
    run.status = AnalysisRunStatus.FAILED
    run.error_code = error_code
    run.completed_at = datetime.now(UTC)
    if job is not None:
        job.status = JobPostingStatus.FAILED
    session.commit()
