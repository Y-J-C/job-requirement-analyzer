import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.job_posting import JobPostingResponse
from app.schemas.requirement_item import (
    RequirementItemCreate,
    RequirementItemListResponse,
    RequirementItemResponse,
    RequirementItemUpdate,
)
from app.services.job_posting import get_job_posting
from app.services.requirement_review import (
    RequirementReviewConflict,
    confirm_requirements,
    create_manual_requirement,
    delete_requirement,
    get_requirement,
    list_manual_requirements,
    update_requirement,
)

job_requirements_router = APIRouter(prefix="/jobs", tags=["requirements"])
requirements_router = APIRouter(prefix="/requirements", tags=["requirements"])
SessionDependency = Annotated[Session, Depends(get_session)]


@job_requirements_router.get(
    "/{job_id}/requirements",
    response_model=RequirementItemListResponse,
)
def list_requirements_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> RequirementItemListResponse:
    job = get_job_posting(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    items, total = list_manual_requirements(session, job_id, offset=offset, limit=limit)
    return RequirementItemListResponse(items=items, total=total, job_status=job.status)


@job_requirements_router.post(
    "/{job_id}/requirements",
    response_model=RequirementItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_requirement_endpoint(
    job_id: uuid.UUID,
    payload: RequirementItemCreate,
    session: SessionDependency,
) -> RequirementItemResponse:
    job = get_job_posting(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    try:
        requirement = create_manual_requirement(session, job, payload)
    except RequirementReviewConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requirements cannot be edited in the current job state",
        ) from error
    return RequirementItemResponse.model_validate(requirement)


@requirements_router.get(
    "/{requirement_id}",
    response_model=RequirementItemResponse,
)
def get_requirement_endpoint(
    requirement_id: uuid.UUID,
    session: SessionDependency,
) -> RequirementItemResponse:
    requirement = get_requirement(session, requirement_id)
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return RequirementItemResponse.model_validate(requirement)


@requirements_router.patch(
    "/{requirement_id}",
    response_model=RequirementItemResponse,
)
def update_requirement_endpoint(
    requirement_id: uuid.UUID,
    payload: RequirementItemUpdate,
    session: SessionDependency,
) -> RequirementItemResponse:
    requirement = get_requirement(session, requirement_id)
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    try:
        updated = update_requirement(session, requirement, payload)
    except RequirementReviewConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requirements cannot be edited in the current job state",
        ) from error
    return RequirementItemResponse.model_validate(updated)


@requirements_router.delete(
    "/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_requirement_endpoint(
    requirement_id: uuid.UUID,
    session: SessionDependency,
) -> Response:
    requirement = get_requirement(session, requirement_id)
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    try:
        delete_requirement(session, requirement)
    except RequirementReviewConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requirements cannot be edited in the current job state",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@job_requirements_router.post(
    "/{job_id}/confirm-requirements",
    response_model=JobPostingResponse,
)
def confirm_requirements_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
) -> JobPostingResponse:
    job = get_job_posting(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    if not confirm_requirements(session, job):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot confirm a job without requirements",
        )
    return JobPostingResponse.model_validate(job)
