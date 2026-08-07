import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.job_posting import JobPostingStatus
from app.models.target_role import RecruitmentStage


class JobPostingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: str = Field(min_length=1, max_length=100)
    job_title: str = Field(min_length=1, max_length=150)
    recruitment_stage: RecruitmentStage
    city: str | None = Field(default=None, max_length=100)
    source_url: HttpUrl | None = Field(default=None, max_length=2048)
    original_text: str = Field(min_length=1, max_length=100_000)


class JobPostingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    active_analysis_run_id: uuid.UUID | None
    target_role_id: uuid.UUID
    company_name: str
    job_title: str
    recruitment_stage: RecruitmentStage
    city: str | None
    source_url: str | None
    original_text: str
    status: JobPostingStatus
    collected_at: datetime
    created_at: datetime
    updated_at: datetime


class JobPostingListResponse(BaseModel):
    items: list[JobPostingResponse]
    total: int
