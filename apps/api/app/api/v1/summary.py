import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.requirement_item import RequirementType
from app.schemas.summary import SelectedSummaryRequest, TargetRoleSummaryResponse
from app.services.summary import build_target_role_summary
from app.services.target_role import get_target_role

router = APIRouter(prefix="/target-roles", tags=["summary"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/{role_id}/summary", response_model=TargetRoleSummaryResponse)
def get_target_role_summary_endpoint(
    role_id: uuid.UUID,
    session: SessionDependency,
    requirement_type: Annotated[RequirementType | None, Query()] = None,
) -> TargetRoleSummaryResponse:
    target_role = get_target_role(session, role_id)
    if target_role is None:
        raise HTTPException(status_code=404, detail="Target role not found")
    return build_target_role_summary(
        session,
        target_role_id=target_role.id,
        target_role_name=target_role.name,
        requirement_type=requirement_type,
    )


@router.post("/{role_id}/summary", response_model=TargetRoleSummaryResponse)
def create_selected_target_role_summary_endpoint(
    role_id: uuid.UUID,
    payload: SelectedSummaryRequest,
    session: SessionDependency,
    requirement_type: Annotated[RequirementType | None, Query()] = None,
) -> TargetRoleSummaryResponse:
    target_role = get_target_role(session, role_id)
    if target_role is None:
        raise HTTPException(status_code=404, detail="Target role not found")
    jobs = list(
        session.scalars(select(JobPosting).where(JobPosting.id.in_(payload.job_ids)))
    )
    jobs_by_id = {job.id: job for job in jobs}
    if any(
        job_id not in jobs_by_id
        or jobs_by_id[job_id].target_role_id != role_id
        or jobs_by_id[job_id].active_analysis_run_id is None
        or jobs_by_id[job_id].status != JobPostingStatus.CONFIRMED
        for job_id in payload.job_ids
    ):
        raise HTTPException(
            status_code=422,
            detail="All selected jobs must exist, match the role, and be confirmed",
        )
    return build_target_role_summary(
        session,
        target_role_id=target_role.id,
        target_role_name=target_role.name,
        requirement_type=requirement_type,
        selected_job_ids=payload.job_ids,
    )
