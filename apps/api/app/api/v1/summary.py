import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.requirement_item import RequirementType
from app.schemas.summary import TargetRoleSummaryResponse
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
