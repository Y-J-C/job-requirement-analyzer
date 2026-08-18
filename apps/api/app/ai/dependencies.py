from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.ai.contracts import RequirementAnalyzer
from app.ai.deepseek import DeepSeekRequirementAnalyzer
from app.core.config import Settings, get_settings


def build_requirement_analyzer(settings: Settings) -> RequirementAnalyzer:
    if settings.app_env == "e2e":
        from app.ai.e2e import E2eRequirementAnalyzer

        return E2eRequirementAnalyzer()
    api_key = (
        settings.deepseek_api_key.get_secret_value()
        if settings.deepseek_api_key is not None
        else ""
    )
    if not api_key:
        raise RuntimeError("AI provider is not configured")
    return DeepSeekRequirementAnalyzer(
        api_key=api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        max_tokens=settings.deepseek_max_tokens,
        timeout_seconds=settings.deepseek_timeout_seconds,
        max_output_retries=settings.deepseek_max_output_retries,
        max_input_chars=settings.deepseek_max_input_chars,
    )


def get_requirement_analyzer(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RequirementAnalyzer:
    try:
        return build_requirement_analyzer(settings)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider is not configured",
        ) from error
