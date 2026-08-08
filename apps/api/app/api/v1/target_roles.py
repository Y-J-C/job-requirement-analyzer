import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.target_role import (
    TargetRoleCreate,
    TargetRoleListResponse,
    TargetRoleResponse,
)
from app.services.target_role import (
    create_target_role,
    delete_target_role,
    get_target_role_with_job_count,
    list_target_roles,
)
from app.storage.contracts import ObjectStore, StorageUnavailableError
from app.storage.dependencies import get_object_store

router = APIRouter(prefix="/target-roles", tags=["target-roles"])
SessionDependency = Annotated[Session, Depends(get_session)]
ObjectStoreDependency = Annotated[ObjectStore, Depends(get_object_store)]


@router.post("", response_model=TargetRoleResponse, status_code=status.HTTP_201_CREATED)
def create_target_role_endpoint(
    payload: TargetRoleCreate,
    session: SessionDependency,
) -> TargetRoleResponse:
    target_role = create_target_role(session, payload)
    return TargetRoleResponse.model_validate(target_role)


@router.get("", response_model=TargetRoleListResponse)
def list_target_roles_endpoint(
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TargetRoleListResponse:
    rows, total = list_target_roles(session, offset=offset, limit=limit)
    items = [
        TargetRoleResponse.model_validate(target_role).model_copy(update={"job_count": job_count})
        for target_role, job_count in rows
    ]
    return TargetRoleListResponse(items=items, total=total)


@router.get("/{role_id}", response_model=TargetRoleResponse)
def get_target_role_endpoint(
    role_id: uuid.UUID,
    session: SessionDependency,
) -> TargetRoleResponse:
    row = get_target_role_with_job_count(session, role_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target role not found",
        )
    target_role, job_count = row
    return TargetRoleResponse.model_validate(target_role).model_copy(
        update={"job_count": job_count}
    )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_target_role_endpoint(
    role_id: uuid.UUID,
    session: SessionDependency,
    store: ObjectStoreDependency,
) -> Response:
    row = get_target_role_with_job_count(session, role_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target role not found",
        )
    target_role, _ = row
    try:
        delete_target_role(session, target_role, store=store)
    except StorageUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is unavailable",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
