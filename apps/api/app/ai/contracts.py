from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.models.requirement_item import RequirementExplicitness, RequirementType


class AnalyzeJobRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: str | None = Field(default=None, min_length=1, max_length=100)
    job_title: str | None = Field(default=None, min_length=1, max_length=150)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    original_text: str = Field(min_length=1, max_length=100_000)


class ExtractedRequirement(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    source_text: str = Field(min_length=1, max_length=2_000)
    normalized_name: str = Field(min_length=1, max_length=200)
    requirement_type: RequirementType
    explicitness: RequirementExplicitness
    confidence: float = Field(ge=0, le=1)


class AnalyzeJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(pattern=r"^1\.0$")
    company_name: str | None = Field(default=None, min_length=1, max_length=100)
    job_title: str | None = Field(default=None, min_length=1, max_length=150)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    requirements: list[ExtractedRequirement] = Field(max_length=100)
    warnings: list[Annotated[str, Field(max_length=500)]] = Field(
        default_factory=list,
        max_length=20,
    )


class AnalyzerError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AnalyzerOutputError(AnalyzerError):
    pass


class AnalyzerProviderError(AnalyzerError):
    pass


class RequirementAnalyzer(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def analyze(self, request: AnalyzeJobRequest) -> AnalyzeJobResult: ...
