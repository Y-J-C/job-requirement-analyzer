import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.job_posting import JobPosting
from app.schemas.job_posting import JobPostingCreate


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


def delete_job_posting(session: Session, job_posting: JobPosting) -> None:
    session.delete(job_posting)
    session.commit()
