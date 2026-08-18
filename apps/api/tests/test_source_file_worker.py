from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID

from fastapi.testclient import TestClient
from PIL import Image

from app.ai.dependencies import get_requirement_analyzer
from app.main import app
from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.source_file import SourceFile, SourceFileStatus
from app.models.target_role import RecruitmentStage
from app.security.malware import (
    CleanFileScanner,
    MalwareDetectedError,
    MalwareScannerUnavailableError,
)
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


class FakeImageOcr:
    def __init__(self, text: str) -> None:
        self.text = text
        self.contents: list[bytes] = []

    def extract_text(self, content: bytes) -> str:
        self.contents.append(content)
        return self.text


class RecordingScanner:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.contents: list[bytes] = []

    def scan(self, content: bytes) -> None:
        self.contents.append(content)
        if self.error is not None:
            raise self.error


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
        file_scanner=CleanFileScanner(),
    )


def test_document_worker_writes_text_and_automatically_queues_analysis(
    api_client: TestClient,
) -> None:
    store = WorkerStore()
    uploaded = upload_file(api_client, store)

    assert run_once(api_client, store, datetime.now(UTC))

    job = api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}").json()
    source = api_client.get(f"/api/v1/jobs/{job['id']}/source-file").json()
    assert job["status"] == "queued"
    assert job["original_text"] == "# JD\nSQL required"
    assert source["parse_status"] == "succeeded"
    assert source["parser_version"] == "document-parser-v1"
    latest = api_client.get(f"/api/v1/jobs/{job['id']}/analysis-runs/latest")
    assert latest.status_code == 200
    assert latest.json()["status"] == "pending"


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


def test_document_worker_ocr_extracts_an_image_only_pdf(api_client: TestClient) -> None:
    image = Image.new("RGB", (320, 180), "white")
    scanned_pdf = BytesIO()
    image.save(scanned_pdf, format="PDF")
    store = WorkerStore()
    uploaded = upload_file(
        api_client,
        store,
        filename="扫描岗位.pdf",
        media_type="application/pdf",
        content=scanned_pdf.getvalue(),
    )
    ocr = FakeImageOcr("示例科技\n数据分析实习生\n熟练使用 SQL")

    assert run_source_file_once(
        api_client.app.state.testing_session_factory,
        store,
        worker_id="pdf-ocr-worker",
        now=datetime.now(UTC),
        file_scanner=CleanFileScanner(),
        image_ocr=ocr,
    )

    job = api_client.get(f"/api/v1/jobs/{uploaded['job']['id']}").json()
    source = api_client.get(f"/api/v1/jobs/{job['id']}/source-file").json()
    assert job["original_text"] == "示例科技\n数据分析实习生\n熟练使用 SQL"
    assert job["status"] == "queued"
    assert source["parse_status"] == "succeeded"
    assert ocr.contents[0].startswith(b"\x89PNG")


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


def test_image_worker_uses_ocr_and_queues_analysis(api_client: TestClient) -> None:
    store = WorkerStore()
    role = api_client.post(
        "/api/v1/target-roles",
        json={"name": "产品经理", "recruitment_stage": "daily_internship"},
    ).json()
    with api_client.app.state.testing_session_factory() as session:
        job = JobPosting(
            target_role_id=UUID(role["id"]),
            company_name=None,
            job_title=None,
            recruitment_stage=RecruitmentStage.DAILY_INTERNSHIP,
            original_text="",
            status=JobPostingStatus.EXTRACTING,
        )
        session.add(job)
        session.flush()
        source = SourceFile(
            job_posting_id=job.id,
            object_key="source-files/image-1",
            original_filename="岗位.png",
            declared_mime_type="image/png",
            detected_media_type="image/png",
            size_bytes=7,
            sha256="0" * 64,
        )
        session.add(source)
        session.commit()
        job_id = job.id
        source_id = source.id
    store.objects["source-files/image-1"] = b"picture"
    ocr = FakeImageOcr("示例科技\n产品经理\n要求 SQL")

    assert run_source_file_once(
        api_client.app.state.testing_session_factory,
        store,
        worker_id="image-worker",
        now=datetime.now(UTC),
        image_ocr=ocr,
        file_scanner=CleanFileScanner(),
    )

    with api_client.app.state.testing_session_factory() as session:
        job = session.get(JobPosting, job_id)
        source = session.get(SourceFile, source_id)
        assert job is not None and job.status == JobPostingStatus.QUEUED
        assert job.original_text == "示例科技\n产品经理\n要求 SQL"
        assert source is not None and source.parser_version == "image-ocr-v1"
    assert ocr.contents == [b"picture"]


def test_last_source_completion_joins_all_sources_in_sequence(api_client: TestClient) -> None:
    store = WorkerStore()
    role = api_client.post(
        "/api/v1/target-roles",
        json={"name": "数据分析", "recruitment_stage": "daily_internship"},
    ).json()
    with api_client.app.state.testing_session_factory() as session:
        job = JobPosting(
            target_role_id=UUID(role["id"]),
            company_name=None,
            job_title=None,
            recruitment_stage=RecruitmentStage.DAILY_INTERNSHIP,
            original_text="",
            status=JobPostingStatus.EXTRACTING,
        )
        session.add(job)
        session.flush()
        session.add_all(
            [
                SourceFile(
                    job_posting_id=job.id,
                    sequence_index=0,
                    object_key="source-files/image-first",
                    original_filename="第一页.png",
                    declared_mime_type="image/png",
                    detected_media_type="image/png",
                    size_bytes=5,
                    sha256="1" * 64,
                ),
                SourceFile(
                    job_posting_id=job.id,
                    sequence_index=1,
                    object_key="source-files/image-second",
                    original_filename="第二页.png",
                    declared_mime_type="image/png",
                    detected_media_type="image/png",
                    size_bytes=6,
                    sha256="2" * 64,
                    parse_status=SourceFileStatus.SUCCEEDED,
                    parser_version="image-ocr-v1",
                    extracted_text="第二页内容",
                ),
            ]
        )
        session.commit()
        job_id = job.id
    store.objects["source-files/image-first"] = b"first"

    assert run_source_file_once(
        api_client.app.state.testing_session_factory,
        store,
        worker_id="image-worker",
        now=datetime.now(UTC),
        image_ocr=FakeImageOcr("第一页内容"),
        file_scanner=CleanFileScanner(),
    )

    with api_client.app.state.testing_session_factory() as session:
        job = session.get(JobPosting, job_id)
        assert job is not None and job.status == JobPostingStatus.QUEUED
        assert job.original_text == "第一页内容\n\n第二页内容"


def test_later_source_completion_preserves_an_existing_batch_failure(
    api_client: TestClient,
) -> None:
    store = WorkerStore()
    role = api_client.post(
        "/api/v1/target-roles",
        json={"name": "风控", "recruitment_stage": "daily_internship"},
    ).json()
    with api_client.app.state.testing_session_factory() as session:
        job = JobPosting(
            target_role_id=UUID(role["id"]),
            recruitment_stage=RecruitmentStage.DAILY_INTERNSHIP,
            original_text="",
            status=JobPostingStatus.FAILED,
        )
        session.add(job)
        session.flush()
        session.add_all(
            [
                SourceFile(
                    job_posting_id=job.id,
                    sequence_index=0,
                    object_key="source-files/still-pending",
                    original_filename="第一页.png",
                    declared_mime_type="image/png",
                    detected_media_type="image/png",
                    size_bytes=5,
                    sha256="3" * 64,
                ),
                SourceFile(
                    job_posting_id=job.id,
                    sequence_index=1,
                    object_key="source-files/already-failed",
                    original_filename="第二页.png",
                    declared_mime_type="image/png",
                    detected_media_type="image/png",
                    size_bytes=6,
                    sha256="4" * 64,
                    parse_status=SourceFileStatus.FAILED,
                    error_code="no_extractable_text",
                ),
            ]
        )
        session.commit()
        job_id = job.id
    store.objects["source-files/still-pending"] = b"first"

    assert run_source_file_once(
        api_client.app.state.testing_session_factory,
        store,
        worker_id="image-worker",
        now=datetime.now(UTC),
        image_ocr=FakeImageOcr("第一页内容"),
        file_scanner=CleanFileScanner(),
    )

    with api_client.app.state.testing_session_factory() as session:
        job = session.get(JobPosting, job_id)
        assert job is not None and job.status == JobPostingStatus.FAILED


def test_malware_scan_runs_before_ocr_and_removes_quarantined_object(
    api_client: TestClient,
) -> None:
    store = WorkerStore()
    uploaded = upload_file(api_client, store)
    object_key = next(iter(store.objects))
    scanner = RecordingScanner(error=MalwareDetectedError())
    ocr = FakeImageOcr("must not be used")

    assert run_source_file_once(
        api_client.app.state.testing_session_factory,
        store,
        worker_id="security-worker",
        now=datetime.now(UTC),
        file_scanner=scanner,
        image_ocr=ocr,
    )

    source = api_client.get(
        f"/api/v1/jobs/{uploaded['job']['id']}/source-file"
    ).json()
    assert scanner.contents == [b"# JD\nSQL required"]
    assert ocr.contents == []
    assert source["parse_status"] == "failed"
    assert source["error_code"] == "malware_detected"
    assert object_key not in store.objects


def test_unavailable_malware_scanner_retries_without_parsing(
    api_client: TestClient,
) -> None:
    store = WorkerStore()
    uploaded = upload_file(api_client, store)
    scanner = RecordingScanner(error=MalwareScannerUnavailableError())

    assert run_source_file_once(
        api_client.app.state.testing_session_factory,
        store,
        worker_id="security-worker",
        now=datetime.now(UTC),
        retry_delay_seconds=0,
        file_scanner=scanner,
    )

    source = api_client.get(
        f"/api/v1/jobs/{uploaded['job']['id']}/source-file"
    ).json()
    assert source["parse_status"] == "pending"
    assert source["error_code"] == "malware_scan_unavailable"
    assert len(store.objects) == 1
