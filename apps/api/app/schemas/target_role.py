import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.target_role import RecruitmentStage


class TargetRoleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    recruitment_stage: RecruitmentStage
    description: str | None = Field(default=None, max_length=2000)


class TargetRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    recruitment_stage: RecruitmentStage
    description: str | None
    created_at: datetime
    updated_at: datetime
    job_count: int = 0


class TargetRoleListResponse(BaseModel):
    items: list[TargetRoleResponse]
    total: int
