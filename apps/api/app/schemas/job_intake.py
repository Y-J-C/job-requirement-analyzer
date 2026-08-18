from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.target_role import RecruitmentStage
from app.schemas.analysis import AnalysisRunResponse
from app.schemas.job_posting import JobPostingResponse
from app.schemas.source_file import SourceFileResponse


class JobSourceType(StrEnum):
    TEXT = "text"
    DOCUMENT = "document"
    IMAGES = "images"


class JobIntakeMetadata(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: str | None = Field(default=None, min_length=1, max_length=100)
    job_title: str | None = Field(default=None, min_length=1, max_length=150)
    recruitment_stage: RecruitmentStage
    city: str | None = Field(default=None, min_length=1, max_length=100)
    source_url: HttpUrl | None = Field(default=None, max_length=2048)


class JobIntakeResponse(BaseModel):
    job: JobPostingResponse
    source_files: list[SourceFileResponse]
    analysis_run: AnalysisRunResponse | None
