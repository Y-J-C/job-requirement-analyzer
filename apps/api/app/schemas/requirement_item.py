import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.job_posting import JobPostingStatus
from app.models.requirement_item import RequirementExplicitness, RequirementType


class RequirementItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    original_text: str = Field(min_length=1, max_length=2000)
    normalized_name: str = Field(min_length=1, max_length=200)
    requirement_type: RequirementType
    explicitness: RequirementExplicitness


class RequirementItemUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    original_text: str | None = Field(default=None, min_length=1, max_length=2000)
    normalized_name: str | None = Field(default=None, min_length=1, max_length=200)
    requirement_type: RequirementType | None = None
    explicitness: RequirementExplicitness | None = None

    @model_validator(mode="after")
    def reject_empty_or_null_update(self) -> "RequirementItemUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field_name) is None for field_name in self.model_fields_set):
            raise ValueError("Updated fields cannot be null")
        return self


class RequirementItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_run_id: uuid.UUID
    original_text: str
    normalized_name: str
    requirement_type: RequirementType
    explicitness: RequirementExplicitness
    confidence: Decimal | None
    user_confirmed: bool
    user_modified: bool
    created_at: datetime
    updated_at: datetime


class RequirementItemListResponse(BaseModel):
    items: list[RequirementItemResponse]
    total: int
    job_status: JobPostingStatus
