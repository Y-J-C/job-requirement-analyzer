from datetime import UTC, datetime, timedelta
from io import BytesIO

from fastapi.testclient import TestClient

from app.ai.dependencies import get_requirement_analyzer
from app.main import app
from app.services.source_file import claim_next_source_file
from app.storage.contracts import StorageUnavailableError
from app.storage.dependencies import get_object_store
from app.worker import run_source_file_once


class WorkerStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.read_unavailable = False

    def ensure_bucket(self) -> None:
        pass

    def put(self, object_key: str, content, _content_type: str) -> None:
        self.objects[object_key] = content.read()

    def read(self, object_key: str) -> bytes:
        if self.read_unavailable:
            raise StorageUnavailableError("Object storage is unavailable")
        return self.objects[object_key]

    def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


class UnusedAnalyzer:
    provider_name = "deepseek"
    model_name = "deepseek-v4-flash"

    def analyze(self, _request):
        raise AssertionError("analyzer must not run")


def upload_file(
    client: TestClient,
    store: WorkerStore,
    *,
    filename: str = "岗位.md",
    media_type: str = "text/markdown",
    content: bytes = b"# JD\nSQL required",
) -> dict:
    app.dependency_overrides[get_object_store] = lambda: store
    role = client.post(
        "/api/v1/target-roles",
        json={"name": "数据分析", "recruitment_stage": "daily_internship"},
    ).json()
    response = client.post(
        f"/api/v1/target-roles/{role['id']}/jobs/upload",
        data={
            "company_name": "示例科技",
            "job_title": "数据分析实习生",
            "recruitment_stage": "daily_internship",
        },
        files={"file": (filename, BytesIO(content), media_type)},
    )
    assert response.status_code == 201
    return response.json()


def run_once(client: TestClient, store: WorkerStore, now: datetime) -> bool:
    return run_source_file_once(
        client.app.state.testing_session_factory,
        store,
        worker_id="document-worker",
        now=now,
        lease_seconds=30,
        retry_delay_seconds=0,
        max_chars=100_000,
        pdf_max_pages=50,
    )


def test_document_worker_writes_text_and_returns_job_to_draft(api_client: TestClient) -> None:
    store = WorkerStore()
    uploaded = upload_file(api_client, store)

    assert run_once(api_client, store, datetime.now(UTC))

    job = api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}").json()
    source = api_client.get(f"/api/v1/jobs/{job['id']}/source-file").json()
    assert job["status"] == "draft"
    assert job["original_text"] == "# JD\nSQL required"
    assert source["parse_status"] == "succeeded"
    assert source["parser_version"] == "document-parser-v1"


def test_document_worker_retries_transient_storage_failure(api_client: TestClient) -> None:
    store = WorkerStore()
    uploaded = upload_file(api_client, store)
    now = datetime.now(UTC)
    store.read_unavailable = True

    assert run_once(api_client, store, now)
    source = api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}/source-file").json()
    assert source["parse_status"] == "pending"
    assert source["error_code"] == "storage_unavailable"

    store.read_unavailable = False
    assert run_once(api_client, store, now + timedelta(seconds=1))
    source = api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}/source-file").json()
    assert source["parse_status"] == "succeeded"


def test_document_worker_does_not_retry_invalid_document(api_client: TestClient) -> None:
    store = WorkerStore()
    uploaded = upload_file(
        api_client,
        store,
        filename="岗位.pdf",
        media_type="application/pdf",
        content=b"%PDF-1.4\nbroken",
    )

    assert run_once(api_client, store, datetime.now(UTC))

    source = api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}/source-file").json()
    job = api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}").json()
    assert source["parse_status"] == "failed"
    assert source["error_code"] == "document_parse_failed"
    assert job["status"] == "failed"
    app.dependency_overrides[get_requirement_analyzer] = lambda: UnusedAnalyzer()
    assert api_client.post(f"/api/v1/jobs/{job['id']}/analyze").status_code == 409


def test_document_worker_recovers_expired_lease(api_client: TestClient) -> None:
    store = WorkerStore()
    uploaded = upload_file(api_client, store)
    now = datetime.now(UTC)
    with api_client.app.state.testing_session_factory() as session:
        claimed = claim_next_source_file(
            session, worker_id="crashed", now=now, lease_seconds=30
        )
    assert claimed is not None

    assert run_once(api_client, store, now + timedelta(seconds=31))
    source = api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}/source-file").json()
    assert source["parse_status"] == "succeeded"
