from app.ai.contracts import AnalyzeJobRequest, AnalyzeJobResult, ExtractedRequirement
from app.models.requirement_item import RequirementExplicitness, RequirementType


class E2eRequirementAnalyzer:
    provider_name = "e2e"
    model_name = "deterministic-e2e-v1"

    def analyze(self, request: AnalyzeJobRequest) -> AnalyzeJobResult:
        evidence = (
            "熟练使用 SQL"
            if "熟练使用 SQL" in request.original_text
            else request.original_text[:2_000]
        )
        normalized_name = "SQL" if "SQL" in evidence else "岗位明确要求"
        return AnalyzeJobResult(
            schema_version="1.0",
            company_name=request.company_name,
            job_title=request.job_title,
            city=request.city,
            requirements=[
                ExtractedRequirement(
                    source_text=evidence,
                    normalized_name=normalized_name,
                    requirement_type=RequirementType.CORE_COMPETENCY,
                    explicitness=RequirementExplicitness.EXPLICIT,
                    confidence=1,
                )
            ],
        )


class E2eImageOcr:
    def extract_text(self, _content: bytes) -> str:
        return "E2E 图片岗位\n熟练使用 SQL"
