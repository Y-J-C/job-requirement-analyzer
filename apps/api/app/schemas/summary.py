import uuid

from pydantic import BaseModel

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
    items: list[RequirementSummaryItemResponse]
