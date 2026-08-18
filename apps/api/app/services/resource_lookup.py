import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_run import AnalysisRun
from app.models.job_posting import JobPosting
from app.models.requirement_item import RequirementItem


def get_job(session: Session, job_id: uuid.UUID) -> JobPosting | None:
    return session.scalar(select(JobPosting).where(JobPosting.id == job_id))


def get_analysis_run(session: Session, run_id: uuid.UUID) -> AnalysisRun | None:
    return session.scalar(select(AnalysisRun).where(AnalysisRun.id == run_id))


def get_requirement(
    session: Session,
    requirement_id: uuid.UUID,
) -> RequirementItem | None:
    return session.scalar(
        select(RequirementItem).where(RequirementItem.id == requirement_id)
    )
