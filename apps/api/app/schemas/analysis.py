import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.analysis_run import AnalysisRunSource, AnalysisRunStatus


class AnalysisRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_posting_id: uuid.UUID
    version: int
    status: AnalysisRunStatus
    source: AnalysisRunSource
    model_provider: str | None
    model_name: str | None
    prompt_version: str | None
    schema_version: str | None
    error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

