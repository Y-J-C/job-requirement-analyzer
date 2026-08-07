import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.job_posting import JobPosting
from app.models.target_role import TargetRole
from app.schemas.target_role import TargetRoleCreate


def create_target_role(session: Session, payload: TargetRoleCreate) -> TargetRole:
    target_role = TargetRole(
        name=payload.name,
        recruitment_stage=payload.recruitment_stage,
        description=payload.description,
    )
    session.add(target_role)
    session.commit()
    session.refresh(target_role)
    return target_role


def list_target_roles(
    session: Session,
    *,
    offset: int,
    limit: int,
) -> tuple[list[tuple[TargetRole, int]], int]:
    items = [
        (target_role, job_count)
        for target_role, job_count in session.execute(
            select(TargetRole, func.count(JobPosting.id))
            .outerjoin(JobPosting, JobPosting.target_role_id == TargetRole.id)
            .group_by(TargetRole.id)
            .order_by(TargetRole.created_at.desc(), TargetRole.id.desc())
            .offset(offset)
            .limit(limit)
        )
    ]
    total = session.scalar(select(func.count()).select_from(TargetRole)) or 0
    return items, total


def get_target_role(session: Session, role_id: uuid.UUID) -> TargetRole | None:
    return session.get(TargetRole, role_id)


def get_target_role_with_job_count(
    session: Session,
    role_id: uuid.UUID,
) -> tuple[TargetRole, int] | None:
    return session.execute(
        select(TargetRole, func.count(JobPosting.id))
        .outerjoin(JobPosting, JobPosting.target_role_id == TargetRole.id)
        .where(TargetRole.id == role_id)
        .group_by(TargetRole.id)
    ).one_or_none()
