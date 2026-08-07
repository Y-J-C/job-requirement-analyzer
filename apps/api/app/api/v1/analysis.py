import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.analysis import AnalysisRunResponse
from app.services.analysis import get_analysis_run

router = APIRouter(prefix="/analysis-runs", tags=["analysis"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/{run_id}", response_model=AnalysisRunResponse)
def get_analysis_run_endpoint(
    run_id: uuid.UUID,
    session: SessionDependency,
) -> AnalysisRunResponse:
    run = get_analysis_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return AnalysisRunResponse.model_validate(run)

