from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.ai.dependencies import get_requirement_analyzer
from app.main import app
from app.storage.contracts import StorageUnavailableError
from app.storage.dependencies import get_object_store


class IntakeStore:
    def __init__(self, fail_on_put: int | None = None) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_count = 0
        self.fail_on_put = fail_on_put

    def ensure_bucket(self) -> None:
        pass

    def put(self, object_key: str, content, _content_type: str) -> None:
        self.put_count += 1
        if self.put_count == self.fail_on_put:
            raise StorageUnavailableError("unavailable")
        self.objects[object_key] = content.read()

    def read(self, object_key: str) -> bytes:
        return self.objects[object_key]

    def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


class IntakeAnalyzer:
    provider_name = "deepseek"
    model_name = "deepseek-v4-flash"

    def analyze(self, _request):
        raise AssertionError("intake must only enqueue analysis")


def create_role(client: TestClient) -> dict:
    return client.post(
        "/api/v1/target-roles",
        json={"name": "产品经理", "recruitment_stage": "daily_internship"},
    ).json()


def image_bytes(color: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 8), color=color).save(output, format="PNG")
    return output.getvalue()


def configure_dependencies(store: IntakeStore) -> None:
    app.dependency_overrides[get_object_store] = lambda: store
    app.dependency_overrides[get_requirement_analyzer] = lambda: IntakeAnalyzer()


def test_text_intake_creates_one_job_and_automatically_queues_analysis(
    api_client: TestClient,
) -> None:
    store = IntakeStore()
    configure_dependencies(store)
    role = create_role(api_client)

    response = api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs/intake",
        data={
            "source_type": "text",
            "recruitment_stage": "daily_internship",
            "text": "示例科技招聘产品经理，要求三年以上经验。",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["job"]["company_name"] is None
    assert payload["job"]["job_title"] is None
    assert payload["job"]["status"] == "queued"
    assert payload["source_files"] == []
    assert payload["analysis_run"]["status"] == "pending"
    assert store.objects == {}


def test_document_and_ordered_image_intake_create_pending_sources(
    api_client: TestClient,
) -> None:
    store = IntakeStore()
    configure_dependencies(store)
    role = create_role(api_client)

    document = api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs/intake",
        data={
            "source_type": "document",
            "recruitment_stage": "daily_internship",
            "company_name": "人工公司",
        },
        files=[("files", ("岗位.md", BytesIO(b"# Job\nSQL"), "text/markdown"))],
    )
    images = api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs/intake",
        data={"source_type": "images", "recruitment_stage": "daily_internship"},
        files=[
            ("files", ("第一页.png", BytesIO(image_bytes("red")), "image/png")),
            ("files", ("第二页.png", BytesIO(image_bytes("blue")), "image/png")),
        ],
    )

    assert document.status_code == 201
    assert document.json()["job"]["status"] == "extracting"
    assert document.json()["job"]["company_name"] == "人工公司"
    assert [item["original_filename"] for item in document.json()["source_files"]] == [
        "岗位.md"
    ]
    assert images.status_code == 201
    assert [item["original_filename"] for item in images.json()["source_files"]] == [
        "第一页.png",
        "第二页.png",
    ]
    assert images.json()["analysis_run"] is None
    assert len(store.objects) == 3


def test_intake_rejects_mixed_sources_before_storage(api_client: TestClient) -> None:
    store = IntakeStore()
    configure_dependencies(store)
    role = create_role(api_client)

    response = api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs/intake",
        data={
            "source_type": "text",
            "recruitment_stage": "daily_internship",
            "text": "岗位文本",
        },
        files=[("files", ("岗位.md", BytesIO(b"content"), "text/markdown"))],
    )

    assert response.status_code == 422
    assert store.objects == {}
    listing = api_client.get(f"/api/v1/target-roles/{role['id']}/jobs").json()
    assert listing["total"] == 0


def test_batch_storage_failure_cleans_prior_objects_and_database(
    api_client: TestClient,
) -> None:
    store = IntakeStore(fail_on_put=2)
    configure_dependencies(store)
    role = create_role(api_client)

    response = api_client.post(
        f"/api/v1/target-roles/{role['id']}/jobs/intake",
        data={"source_type": "images", "recruitment_stage": "daily_internship"},
        files=[
            ("files", ("第一页.png", BytesIO(image_bytes("red")), "image/png")),
            ("files", ("第二页.png", BytesIO(image_bytes("blue")), "image/png")),
        ],
    )

    assert response.status_code == 503
    assert store.objects == {}
    listing = api_client.get(f"/api/v1/target-roles/{role['id']}/jobs").json()
    assert listing["total"] == 0
