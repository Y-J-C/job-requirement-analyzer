import uuid

from pydantic import BaseModel, Field, field_validator

from app.models.requirement_item import RequirementExplicitness, RequirementType


class SummaryEvidenceResponse(BaseModel):
    requirement_id: uuid.UUID
    job_id: uuid.UUID
    company_name: str
    job_title: str
    original_text: str
    explicitness: RequirementExplicitness


class RequirementSummaryItemResponse(BaseModel):
    normalized_name: str
    requirement_type: RequirementType
    mentioning_job_count: int
    confirmed_job_count: int
    coverage_rate: float
    evidence_count: int
    explicit_evidence_count: int
    evidence: list[SummaryEvidenceResponse]


class TargetRoleSummaryResponse(BaseModel):
    target_role_id: uuid.UUID
    target_role_name: str
    sample_job_count: int
    confirmed_job_count: int
    sample_size_notice: str
    selected_job_ids: list[uuid.UUID] = Field(default_factory=list)
    items: list[RequirementSummaryItemResponse]


class SelectedSummaryRequest(BaseModel):
    job_ids: list[uuid.UUID] = Field(min_length=2, max_length=500)

    @field_validator("job_ids")
    @classmethod
    def require_unique_job_ids(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(value)) != len(value):
            raise ValueError("job_ids must be unique")
        return value
