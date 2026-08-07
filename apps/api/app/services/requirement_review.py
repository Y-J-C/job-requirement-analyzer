import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.analysis_run import (
    AnalysisRun,
    AnalysisRunSource,
    AnalysisRunStatus,
)
from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.requirement_item import RequirementItem
from app.schemas.requirement_item import RequirementItemCreate, RequirementItemUpdate


def get_manual_run(session: Session, job_id: uuid.UUID) -> AnalysisRun | None:
    return session.scalar(
        select(AnalysisRun)
        .where(
            AnalysisRun.job_posting_id == job_id,
            AnalysisRun.source == AnalysisRunSource.MANUAL,
        )
        .order_by(AnalysisRun.version.desc())
        .limit(1)
    )


def get_review_run(session: Session, job_id: uuid.UUID) -> AnalysisRun | None:
    return session.scalar(
        select(AnalysisRun)
        .where(
            AnalysisRun.job_posting_id == job_id,
            AnalysisRun.status == AnalysisRunStatus.SUCCEEDED,
        )
        .order_by(AnalysisRun.version.desc())
        .limit(1)
    )


def get_or_create_manual_run(session: Session, job_id: uuid.UUID) -> AnalysisRun:
    existing = get_review_run(session, job_id)
    if existing is not None:
        return existing

    latest_version = session.scalar(
        select(func.max(AnalysisRun.version)).where(AnalysisRun.job_posting_id == job_id)
    )
    analysis_run = AnalysisRun(
        job_posting_id=job_id,
        version=(latest_version or 0) + 1,
        status=AnalysisRunStatus.SUCCEEDED,
        source=AnalysisRunSource.MANUAL,
    )
    session.add(analysis_run)
    session.flush()
    return analysis_run


def create_manual_requirement(
    session: Session,
    job: JobPosting,
    payload: RequirementItemCreate,
) -> RequirementItem:
    analysis_run = get_or_create_manual_run(session, job.id)
    requirement = RequirementItem(
        analysis_run_id=analysis_run.id,
        original_text=payload.original_text,
        normalized_name=payload.normalized_name,
        requirement_type=payload.requirement_type,
        explicitness=payload.explicitness,
        confidence=None,
        user_confirmed=False,
        user_modified=True,
    )
    session.add(requirement)
    job.status = JobPostingStatus.REVIEW_REQUIRED
    session.execute(
        update(RequirementItem)
        .where(RequirementItem.analysis_run_id == analysis_run.id)
        .values(user_confirmed=False)
    )
    session.commit()
    session.refresh(requirement)
    return requirement


def list_manual_requirements(
    session: Session,
    job_id: uuid.UUID,
    *,
    offset: int,
    limit: int,
) -> tuple[list[RequirementItem], int]:
    analysis_run = get_review_run(session, job_id)
    if analysis_run is None:
        return [], 0

    condition = RequirementItem.analysis_run_id == analysis_run.id
    items = list(
        session.scalars(
            select(RequirementItem)
            .where(condition)
            .order_by(RequirementItem.created_at.asc(), RequirementItem.id.asc())
            .offset(offset)
            .limit(limit)
        )
    )
    total = (
        session.scalar(select(func.count()).select_from(RequirementItem).where(condition)) or 0
    )
    return items, total


def get_requirement(session: Session, requirement_id: uuid.UUID) -> RequirementItem | None:
    return session.get(RequirementItem, requirement_id)


def get_requirement_job(
    session: Session,
    requirement: RequirementItem,
) -> JobPosting:
    return session.scalars(
        select(JobPosting)
        .join(AnalysisRun, AnalysisRun.job_posting_id == JobPosting.id)
        .where(AnalysisRun.id == requirement.analysis_run_id)
    ).one()


def reopen_review(session: Session, analysis_run_id: uuid.UUID, job: JobPosting) -> None:
    session.execute(
        update(RequirementItem)
        .where(RequirementItem.analysis_run_id == analysis_run_id)
        .values(user_confirmed=False)
    )
    job.status = JobPostingStatus.REVIEW_REQUIRED


def update_requirement(
    session: Session,
    requirement: RequirementItem,
    payload: RequirementItemUpdate,
) -> RequirementItem:
    for field_name in payload.model_fields_set:
        setattr(requirement, field_name, getattr(payload, field_name))
    requirement.user_modified = True
    job = get_requirement_job(session, requirement)
    reopen_review(session, requirement.analysis_run_id, job)
    session.commit()
    session.refresh(requirement)
    return requirement


def delete_requirement(session: Session, requirement: RequirementItem) -> None:
    analysis_run_id = requirement.analysis_run_id
    job = get_requirement_job(session, requirement)
    session.delete(requirement)
    session.flush()
    remaining = (
        session.scalar(
            select(func.count())
            .select_from(RequirementItem)
            .where(RequirementItem.analysis_run_id == analysis_run_id)
        )
        or 0
    )
    if remaining == 0:
        job.status = JobPostingStatus.DRAFT
    else:
        reopen_review(session, analysis_run_id, job)
    session.commit()


def confirm_requirements(session: Session, job: JobPosting) -> bool:
    analysis_run = get_review_run(session, job.id)
    if analysis_run is None:
        return False
    count = (
        session.scalar(
            select(func.count())
            .select_from(RequirementItem)
            .where(RequirementItem.analysis_run_id == analysis_run.id)
        )
        or 0
    )
    if count == 0:
        return False
    session.execute(
        update(RequirementItem)
        .where(RequirementItem.analysis_run_id == analysis_run.id)
        .values(user_confirmed=True)
    )
    job.status = JobPostingStatus.CONFIRMED
    session.commit()
    session.refresh(job)
    return True
