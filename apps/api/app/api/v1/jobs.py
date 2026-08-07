import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.ai.contracts import RequirementAnalyzer
from app.ai.dependencies import get_requirement_analyzer
from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.schemas.analysis import AnalysisRunResponse
from app.schemas.job_posting import (
    JobPostingCreate,
    JobPostingListResponse,
    JobPostingResponse,
)
from app.services.analysis import create_ai_analysis_run, get_latest_analysis_run
from app.services.job_posting import (
    create_job_posting,
    delete_job_posting,
    get_job_posting,
    list_job_postings,
)
from app.services.target_role import get_target_role

target_role_jobs_router = APIRouter(prefix="/target-roles", tags=["jobs"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])
SessionDependency = Annotated[Session, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
AnalyzerDependency = Annotated[RequirementAnalyzer, Depends(get_requirement_analyzer)]


def require_target_role(session: Session, role_id: uuid.UUID) -> None:
    if get_target_role(session, role_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target role not found",
        )


@target_role_jobs_router.post(
    "/{role_id}/jobs",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job_posting_endpoint(
    role_id: uuid.UUID,
    payload: JobPostingCreate,
    session: SessionDependency,
) -> JobPostingResponse:
    require_target_role(session, role_id)
    return JobPostingResponse.model_validate(create_job_posting(session, role_id, payload))


@target_role_jobs_router.get("/{role_id}/jobs", response_model=JobPostingListResponse)
def list_job_postings_endpoint(
    role_id: uuid.UUID,
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JobPostingListResponse:
    require_target_role(session, role_id)
    items, total = list_job_postings(session, role_id, offset=offset, limit=limit)
    return JobPostingListResponse(items=items, total=total)


@jobs_router.get("/{job_id}", response_model=JobPostingResponse)
def get_job_posting_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
) -> JobPostingResponse:
    job_posting = get_job_posting(session, job_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return JobPostingResponse.model_validate(job_posting)


@jobs_router.post(
    "/{job_id}/analyze",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze_job_posting_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
    settings: SettingsDependency,
    analyzer: AnalyzerDependency,
) -> AnalysisRunResponse:
    job_posting = get_job_posting(session, job_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    analysis_run = create_ai_analysis_run(
        session,
        job_posting,
        model_provider=analyzer.provider_name,
        model_name=analyzer.model_name,
        max_attempts=settings.analysis_worker_max_attempts,
    )
    if analysis_run is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is already being analyzed or has review data",
        )
    return AnalysisRunResponse.model_validate(analysis_run)


@jobs_router.get(
    "/{job_id}/analysis-runs/latest",
    response_model=AnalysisRunResponse,
)
def get_latest_analysis_run_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
) -> AnalysisRunResponse:
    if get_job_posting(session, job_id) is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    analysis_run = get_latest_analysis_run(session, job_id)
    if analysis_run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return AnalysisRunResponse.model_validate(analysis_run)


@jobs_router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_posting_endpoint(job_id: uuid.UUID, session: SessionDependency) -> Response:
    job_posting = get_job_posting(session, job_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    delete_job_posting(session, job_posting)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
