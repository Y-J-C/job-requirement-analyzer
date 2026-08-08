import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.source_file import SourceFileStatus
from app.models.target_role import RecruitmentStage
from app.schemas.job_posting import JobPostingResponse


class JobPostingUploadMetadata(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: str = Field(min_length=1, max_length=100)
    job_title: str = Field(min_length=1, max_length=150)
    recruitment_stage: RecruitmentStage
    city: str | None = Field(default=None, max_length=100)
    source_url: HttpUrl | None = Field(default=None, max_length=2048)


class SourceFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_posting_id: uuid.UUID
    original_filename: str
    declared_mime_type: str
    detected_media_type: str
    size_bytes: int
    sha256: str
    parse_status: SourceFileStatus
    parser_version: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class JobPostingUploadResponse(BaseModel):
    job: JobPostingResponse
    source_file: SourceFileResponse
