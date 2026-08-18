from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from fastapi.testclient import TestClient

from app.ai.dependencies import get_requirement_analyzer
from app.main import app
from app.models.analysis_run import AnalysisRun, AnalysisRunStatus
from app.models.job_posting import JobPosting, JobPostingStatus
from app.security.malware import CleanFileScanner
from app.storage.dependencies import get_object_store
from app.worker import run_source_file_once


class RetryStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def ensure_bucket(self) -> None:
        pass

    def put(self, object_key: str, content, _content_type: str) -> None:
        self.objects[object_key] = content.read()

    def read(self, object_key: str) -> bytes:
        return self.objects[object_key]

    def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


class RetryAnalyzer:
    provider_name = "deepseek"
    model_name = "deepseek-v4-flash"

    def analyze(self, _request):
        raise AssertionError("retry endpoint must only enqueue")


def setup_role(client: TestClient, store: RetryStore) -> dict:
    app.dependency_overrides[get_object_store] = lambda: store
    app.dependency_overrides[get_requirement_analyzer] = lambda: RetryAnalyzer()
    return client.post(
        "/api/v1/target-roles",
        json={"name": "数据分析", "recruitment_stage": "daily_internship"},
    ).json()


def test_retry_failed_source_returns_it_to_extraction_queue(api_client: TestClient) -> None:
    store = RetryStore()
    role = setup_role(api_client, store)
    intake = api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs/intake",
        data={"source_type": "document", "recruitment_stage": "daily_internship"},
        files=[("files", ("损坏.pdf", BytesIO(b"%PDF-1.4\nbroken"), "application/pdf"))],
    ).json()
    assert run_source_file_once(
        api_client.app.state.testing_session_factory,
        store,
        worker_id="retry-worker",
        now=datetime.now(UTC),
        file_scanner=CleanFileScanner(),
    )

    response = api_client.post(f"/api/v1/jobs/{intake['job']['id']}/retry")

    assert response.status_code == 202
    assert response.json()["job"]["status"] == "extracting"
    assert response.json()["source_files"][0]["parse_status"] == "pending"
    assert response.json()["source_files"][0]["error_code"] is None
    assert response.json()["analysis_run"] is None


def test_retry_failed_analysis_creates_one_new_run(api_client: TestClient) -> None:
    store = RetryStore()
    role = setup_role(api_client, store)
    intake = api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs/intake",
        data={
            "source_type": "text",
            "recruitment_stage": "daily_internship",
            "text": "要求熟练使用 SQL",
        },
    ).json()
    with api_client.app.state.testing_session_factory() as session:
        run = session.get(AnalysisRun, UUID(intake["analysis_run"]["id"]))
        job = session.get(JobPosting, UUID(intake["job"]["id"]))
        assert run is not None and job is not None
        run.status = AnalysisRunStatus.FAILED
        run.completed_at = datetime.now(UTC)
        job.status = JobPostingStatus.FAILED
        session.commit()

    response = api_client.post(f"/api/v1/jobs/{intake['job']['id']}/retry")

    assert response.status_code == 202
    assert response.json()["job"]["status"] == "queued"
    assert response.json()["analysis_run"]["version"] == 2
    assert response.json()["analysis_run"]["status"] == "pending"
    assert api_client.post(f"/api/v1/jobs/{intake['job']['id']}/retry").status_code == 409
