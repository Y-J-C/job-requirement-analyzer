from app.ai.dependencies import build_requirement_analyzer
from app.ai.e2e import E2eImageOcr, E2eRequirementAnalyzer
from app.core.config import Settings


def test_e2e_dependencies_are_deterministic_and_explicitly_gated() -> None:
    analyzer = build_requirement_analyzer(Settings(app_env="e2e", deepseek_api_key=None))

    assert isinstance(analyzer, E2eRequirementAnalyzer)
    assert E2eImageOcr().extract_text(b"not-a-real-image") == (
        "E2E 图片岗位\n熟练使用 SQL"
    )
