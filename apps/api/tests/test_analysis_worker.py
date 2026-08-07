from datetime import UTC, datetime, timedelta

from app.ai.contracts import (
    AnalyzeJobRequest,
    AnalyzeJobResult,
    AnalyzerProviderError,
    ExtractedRequirement,
)
from app.ai.dependencies import get_requirement_analyzer
from app.models.requirement_item import RequirementExplicitness, RequirementType
from app.services.analysis import claim_next_analysis_run
from app.worker import run_once


class TransientAnalyzer:
    provider_name = "deepseek"
    model_name = "deepseek-v4-flash"

    def analyze(self, _request: AnalyzeJobRequest) -> AnalyzeJobResult:
        raise AnalyzerProviderError("provider_request_failed")


class SuccessfulAnalyzer:
    provider_name = "deepseek"
    model_name = "deepseek-v4-flash"

    def analyze(self, _request: AnalyzeJobRequest) -> AnalyzeJobResult:
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
        )


class PythonAnalyzer:
    provider_name = "deepseek"
    model_name = "deepseek-v4-flash"

    def analyze(self, _request: AnalyzeJobRequest) -> AnalyzeJobResult:
        return AnalyzeJobResult(
            schema_version="1.0",
            requirements=[
                ExtractedRequirement(
                    source_text="熟练使用 SQL",
                    normalized_name="Python",
                    requirement_type=RequirementType.CORE_COMPETENCY,
                    explicitness=RequirementExplicitness.EXPLICIT,
                    confidence=0.9,
                )
            ],
        )


def _create_job(api_client) -> dict:
    role = api_client.post(
        "/api/v1/target-roles",
        json={
            "name": "数据分析实习生",
            "recruitment_stage": "daily_internship",
            "description": None,
        },
    ).json()
    return api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs",
        json={
            "company_name": "示例公司",
            "job_title": "数据分析实习生",
            "recruitment_stage": "daily_internship",
            "original_text": "熟练使用 SQL",
        },
    ).json()


def test_worker_retries_transient_provider_failure(api_client) -> None:
    api_client.app.dependency_overrides[get_requirement_analyzer] = lambda: TransientAnalyzer()
    job = _create_job(api_client)
    run = api_client.post(f"/api/v1/jobs/{job['id']}/analyze").json()
    now = datetime.now(UTC)

    assert run_once(
        api_client.app.state.testing_session_factory,
        TransientAnalyzer(),
        worker_id="test-worker",
        now=now,
        retry_delay_seconds=0,
    )

    retried = api_client.get(f"/api/v1/analysis-runs/{run['id']}").json()
    assert retried["status"] == "pending"
    assert retried["attempt_count"] == 1
    assert retried["error_code"] == "provider_request_failed"

    assert run_once(
        api_client.app.state.testing_session_factory,
        SuccessfulAnalyzer(),
        worker_id="test-worker",
        now=now + timedelta(seconds=1),
    )
    completed = api_client.get(f"/api/v1/analysis-runs/{run['id']}").json()
    assert completed["status"] == "succeeded"
    assert completed["attempt_count"] == 2


def test_latest_analysis_run_allows_refresh_recovery(api_client) -> None:
    api_client.app.dependency_overrides[get_requirement_analyzer] = lambda: SuccessfulAnalyzer()
    job = _create_job(api_client)
    started = api_client.post(f"/api/v1/jobs/{job['id']}/analyze").json()

    latest = api_client.get(f"/api/v1/jobs/{job['id']}/analysis-runs/latest")

    assert latest.status_code == 200
    assert latest.json()["id"] == started["id"]
    assert latest.json()["status"] == "pending"
    assert api_client.post(
        f"/api/v1/jobs/{job['id']}/requirements",
        json={
            "original_text": "熟练使用 SQL",
            "normalized_name": "SQL",
            "requirement_type": "core_competency",
            "explicitness": "explicit",
        },
    ).status_code == 409


def test_worker_recovers_an_expired_lease(api_client) -> None:
    api_client.app.dependency_overrides[get_requirement_analyzer] = lambda: SuccessfulAnalyzer()
    job = _create_job(api_client)
    run = api_client.post(f"/api/v1/jobs/{job['id']}/analyze").json()
    now = datetime.now(UTC)
    with api_client.app.state.testing_session_factory() as session:
        claimed = claim_next_analysis_run(
            session,
            worker_id="crashed-worker",
            now=now,
            lease_seconds=30,
        )
    assert claimed is not None

    assert run_once(
        api_client.app.state.testing_session_factory,
        SuccessfulAnalyzer(),
        worker_id="replacement-worker",
        now=now + timedelta(seconds=31),
    )
    recovered = api_client.get(f"/api/v1/analysis-runs/{run['id']}").json()
    assert recovered["status"] == "succeeded"
    assert recovered["attempt_count"] == 2


def test_worker_stops_after_maximum_attempts(api_client) -> None:
    api_client.app.dependency_overrides[get_requirement_analyzer] = lambda: TransientAnalyzer()
    job = _create_job(api_client)
    run = api_client.post(f"/api/v1/jobs/{job['id']}/analyze").json()
    now = datetime.now(UTC)

    for attempt in range(3):
        assert run_once(
            api_client.app.state.testing_session_factory,
            TransientAnalyzer(),
            worker_id="test-worker",
            now=now + timedelta(seconds=attempt),
            retry_delay_seconds=0,
        )

    exhausted = api_client.get(f"/api/v1/analysis-runs/{run['id']}").json()
    assert exhausted["status"] == "failed"
    assert exhausted["attempt_count"] == 3
    assert exhausted["error_code"] == "provider_request_failed"


def test_reanalysis_keeps_old_summary_until_new_version_is_confirmed(api_client) -> None:
    api_client.app.dependency_overrides[get_requirement_analyzer] = lambda: PythonAnalyzer()
    job = _create_job(api_client)
    requirement = api_client.post(
        f"/api/v1/jobs/{job['id']}/requirements",
        json={
            "original_text": "熟练使用 SQL",
            "normalized_name": "SQL",
            "requirement_type": "core_competency",
            "explicitness": "explicit",
        },
    )
    assert requirement.status_code == 201
    confirmed = api_client.post(f"/api/v1/jobs/{job['id']}/confirm-requirements").json()
    old_run_id = confirmed["active_analysis_run_id"]

    started = api_client.post(f"/api/v1/jobs/{job['id']}/analyze")
    assert started.status_code == 202
    assert api_client.post(f"/api/v1/jobs/{job['id']}/confirm-requirements").status_code == 409
    role_id = job["target_role_id"]
    queued_summary = api_client.get(f"/api/v1/target-roles/{role_id}/summary").json()
    assert [item["normalized_name"] for item in queued_summary["items"]] == ["SQL"]

    assert run_once(
        api_client.app.state.testing_session_factory,
        PythonAnalyzer(),
        worker_id="test-worker",
    )
    review_summary = api_client.get(f"/api/v1/target-roles/{role_id}/summary").json()
    assert [item["normalized_name"] for item in review_summary["items"]] == ["SQL"]

    switched = api_client.post(f"/api/v1/jobs/{job['id']}/confirm-requirements")
    assert switched.status_code == 200
    assert switched.json()["active_analysis_run_id"] == started.json()["id"]
    final_summary = api_client.get(f"/api/v1/target-roles/{role_id}/summary").json()
    assert [item["normalized_name"] for item in final_summary["items"]] == ["Python"]
    assert api_client.get(f"/api/v1/analysis-runs/{old_run_id}").json()["status"] == "superseded"
