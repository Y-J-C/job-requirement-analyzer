from app.ai.contracts import (
    AnalyzeJobRequest,
    AnalyzeJobResult,
    AnalyzerOutputError,
    ExtractedRequirement,
)
from app.ai.dependencies import get_requirement_analyzer
from app.models.requirement_item import RequirementExplicitness, RequirementType
from app.worker import run_once


class FakeAnalyzer:
    provider_name = "deepseek"
    model_name = "deepseek-v4-flash"

    def analyze(self, request: AnalyzeJobRequest) -> AnalyzeJobResult:
        assert request.original_text == "岗位要求：熟练使用 SQL"
        return AnalyzeJobResult(
            schema_version="1.0",
            requirements=[
                ExtractedRequirement(
                    source_text="熟练使用 SQL",
                    normalized_name="SQL",
                    requirement_type=RequirementType.CORE_COMPETENCY,
                    explicitness=RequirementExplicitness.EXPLICIT,
                    confidence=0.98,
                )
            ],
            warnings=[],
        )


class FailingAnalyzer:
    provider_name = "deepseek"
    model_name = "deepseek-v4-flash"

    def analyze(self, _request: AnalyzeJobRequest) -> AnalyzeJobResult:
        raise AnalyzerOutputError("invalid_model_output")


def create_job(api_client):
    role = api_client.post(
        "/api/v1/target-roles",
        json={
            "name": "数据分析实习生",
            "recruitment_stage": "daily_internship",
            "description": "",
        },
    ).json()
    return api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs",
        json={
            "company_name": "示例公司",
            "job_title": "数据分析实习生",
            "recruitment_stage": "daily_internship",
            "city": None,
            "source_url": None,
            "original_text": "岗位要求：熟练使用 SQL",
        },
    ).json()


def test_analyze_job_saves_unconfirmed_ai_requirements(api_client) -> None:
    api_client.app.dependency_overrides[get_requirement_analyzer] = lambda: FakeAnalyzer()
    job = create_job(api_client)

    response = api_client.post(f"/api/v1/jobs/{job['id']}/analyze")

    assert response.status_code == 202
    run_id = response.json()["id"]
    run = api_client.get(f"/api/v1/analysis-runs/{run_id}")
    assert run.status_code == 200
    assert run.json()["status"] == "pending"
    assert run.json()["model_provider"] == "deepseek"

    assert run_once(
        api_client.app.state.testing_session_factory,
        FakeAnalyzer(),
        worker_id="test-worker",
    )
    run = api_client.get(f"/api/v1/analysis-runs/{run_id}")
    assert run.json()["status"] == "succeeded"

    listing = api_client.get(f"/api/v1/jobs/{job['id']}/requirements")
    assert listing.status_code == 200
    assert listing.json()["job_status"] == "review_required"
    assert listing.json()["total"] == 1
    requirement = listing.json()["items"][0]
    assert requirement["normalized_name"] == "SQL"
    assert requirement["confidence"] == "0.9800"
    assert requirement["user_confirmed"] is False
    assert requirement["user_modified"] is False


def test_analyze_job_rejects_reanalysis_while_review_is_pending(api_client) -> None:
    api_client.app.dependency_overrides[get_requirement_analyzer] = lambda: FakeAnalyzer()
    job = create_job(api_client)

    first = api_client.post(f"/api/v1/jobs/{job['id']}/analyze")
    assert first.status_code == 202

    assert run_once(
        api_client.app.state.testing_session_factory,
        FakeAnalyzer(),
        worker_id="test-worker",
    )

    # A succeeded run can be reviewed, but reanalysis is intentionally deferred in this slice.
    second = api_client.post(f"/api/v1/jobs/{job['id']}/analyze")
    assert second.status_code == 409


def test_failed_analysis_does_not_save_partial_requirements(api_client) -> None:
    api_client.app.dependency_overrides[get_requirement_analyzer] = lambda: FailingAnalyzer()
    job = create_job(api_client)

    response = api_client.post(f"/api/v1/jobs/{job['id']}/analyze")
    assert response.status_code == 202

    assert run_once(
        api_client.app.state.testing_session_factory,
        FailingAnalyzer(),
        worker_id="test-worker",
    )

    run = api_client.get(f"/api/v1/analysis-runs/{response.json()['id']}").json()
    assert run["status"] == "failed"
    assert run["error_code"] == "invalid_model_output"
    listing = api_client.get(f"/api/v1/jobs/{job['id']}/requirements").json()
    assert listing["job_status"] == "failed"
    assert listing["items"] == []
