from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.source_file import SourceFile
from app.storage.contracts import StorageUnavailableError
from app.storage.dependencies import get_object_store


class MemoryObjectStore:
    def __init__(self, *, unavailable: bool = False, delete_unavailable: bool = False) -> None:
        self.objects: dict[str, bytes] = {}
        self.unavailable = unavailable
        self.delete_unavailable = delete_unavailable

    def ensure_bucket(self) -> None:
        if self.unavailable:
            raise StorageUnavailableError("Object storage is unavailable")

    def put(self, object_key: str, content, content_type: str) -> None:
        assert content_type == "text/markdown"
        self.objects[object_key] = content.read()

    def read(self, object_key: str) -> bytes:
        return self.objects[object_key]

    def delete(self, object_key: str) -> None:
        if self.delete_unavailable:
            raise StorageUnavailableError("Object storage is unavailable")
        self.objects.pop(object_key, None)


def create_target_role(client: TestClient) -> dict:
    return client.post(
        "/api/v1/target-roles",
        json={"name": "数据分析", "recruitment_stage": "daily_internship"},
    ).json()


def upload_markdown(client: TestClient, role_id: str, content: bytes = b"# JD\nSQL"):
    return client.post(
        f"/api/v1/target-roles/{role_id}/jobs/upload",
        data={
            "company_name": "示例科技",
            "job_title": "数据分析实习生",
            "recruitment_stage": "daily_internship",
            "city": "上海",
            "source_url": "https://example.com/job",
        },
        files={"file": ("岗位.md", BytesIO(content), "text/markdown")},
    )


def test_upload_creates_extracting_job_and_pending_source_file(api_client: TestClient) -> None:
    store = MemoryObjectStore()
    app.dependency_overrides[get_object_store] = lambda: store
    role = create_target_role(api_client)

    response = upload_markdown(api_client, role["id"])

    assert response.status_code == 201
    body = response.json()
    assert body["job"]["status"] == "extracting"
    assert body["job"]["original_text"] == ""
    assert body["source_file"]["parse_status"] == "pending"
    assert body["source_file"]["original_filename"] == "岗位.md"
    assert list(store.objects.values()) == [b"# JD\nSQL"]
    with app.state.testing_session_factory() as session:
        source_file = session.scalar(select(SourceFile))
        assert source_file is not None
        assert "岗位.md" not in source_file.object_key

    status_response = api_client.get(f"/api/v1/jobs/{body['job']['id']}/source-file")
    assert status_response.status_code == 200
    assert status_response.json() == body["source_file"]


def test_upload_rejects_invalid_signature_before_storing(api_client: TestClient) -> None:
    store = MemoryObjectStore()
    app.dependency_overrides[get_object_store] = lambda: store
    role = create_target_role(api_client)

    response = api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs/upload",
        data={
            "company_name": "示例科技",
            "job_title": "数据分析实习生",
            "recruitment_stage": "daily_internship",
        },
        files={"file": ("岗位.pdf", BytesIO(b"not pdf"), "application/pdf")},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "file_signature_mismatch"
    assert store.objects == {}


def test_upload_returns_not_found_before_storing(api_client: TestClient) -> None:
    store = MemoryObjectStore()
    app.dependency_overrides[get_object_store] = lambda: store

    response = upload_markdown(api_client, "00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert store.objects == {}


def test_upload_hides_object_storage_failure(api_client: TestClient) -> None:
    store = MemoryObjectStore(unavailable=True)
    app.dependency_overrides[get_object_store] = lambda: store
    role = create_target_role(api_client)

    response = upload_markdown(api_client, role["id"])

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "File storage is unavailable"
    assert response.json()["status"] == 503


def test_delete_uploaded_job_removes_original_object(api_client: TestClient) -> None:
    store = MemoryObjectStore()
    app.dependency_overrides[get_object_store] = lambda: store
    role = create_target_role(api_client)
    uploaded = upload_markdown(api_client, role["id"]).json()

    response = api_client.delete(f"/api/v1/jobs/{uploaded['job']['id']}")

    assert response.status_code == 204
    assert store.objects == {}
    assert api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}").status_code == 404


def test_delete_storage_failure_keeps_job_for_retry(api_client: TestClient) -> None:
    store = MemoryObjectStore()
    app.dependency_overrides[get_object_store] = lambda: store
    role = create_target_role(api_client)
    uploaded = upload_markdown(api_client, role["id"]).json()
    store.delete_unavailable = True

    response = api_client.delete(f"/api/v1/jobs/{uploaded['job']['id']}")

    assert response.status_code == 503
    assert api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}").status_code == 200
    assert store.objects


def test_delete_target_role_removes_uploaded_jobs_and_objects(api_client: TestClient) -> None:
    store = MemoryObjectStore()
    app.dependency_overrides[get_object_store] = lambda: store
    role = create_target_role(api_client)
    uploaded = upload_markdown(api_client, role["id"]).json()

    response = api_client.delete(f"/api/v1/target-roles/{role['id']}")

    assert response.status_code == 204
    assert store.objects == {}
    assert api_client.get(f"/api/v1/target-roles/{role['id']}").status_code == 404
    assert api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}").status_code == 404


def test_delete_target_role_storage_failure_keeps_database_records(
    api_client: TestClient,
) -> None:
    store = MemoryObjectStore()
    app.dependency_overrides[get_object_store] = lambda: store
    role = create_target_role(api_client)
    uploaded = upload_markdown(api_client, role["id"]).json()
    store.delete_unavailable = True

    response = api_client.delete(f"/api/v1/target-roles/{role['id']}")

    assert response.status_code == 503
    assert api_client.get(f"/api/v1/target-roles/{role['id']}").status_code == 200
    assert api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}").status_code == 200
    assert store.objects
