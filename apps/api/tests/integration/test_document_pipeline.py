import os
import uuid
from datetime import UTC, datetime
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.target_role import TargetRole
from app.storage.dependencies import get_object_store
from app.worker import run_source_file_once

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_TESTS") != "1" or os.getenv("RUN_STORAGE_TESTS") != "1",
        reason="set database and storage integration flags with Docker services running",
    ),
]


def test_markdown_upload_persists_and_extracts_with_postgres_and_minio() -> None:
    store = get_object_store()
    role_id: str | None = None
    job_id: str | None = None
    with TestClient(app) as client:
        try:
            role_response = client.post(
                "/api/v1/target-roles",
                json={
                    "name": f"文件集成测试-{uuid.uuid4().hex[:8]}",
                    "recruitment_stage": "daily_internship",
                },
            )
            assert role_response.status_code == 201
            role_id = role_response.json()["id"]
            upload = client.post(
                f"/api/v1/target-roles/{role_id}/jobs/upload",
                data={
                    "company_name": "集成测试公司",
                    "job_title": "数据分析实习生",
                    "recruitment_stage": "daily_internship",
                },
                files={
                    "file": (
                        "岗位.md",
                        BytesIO("# 岗位要求\n熟练使用 SQL".encode()),
                        "text/markdown",
                    )
                },
            )
            assert upload.status_code == 201
            job_id = upload.json()["job"]["id"]

            assert run_source_file_once(
                SessionLocal,
                store,
                worker_id="integration-worker",
                now=datetime.now(UTC),
            )
            job = client.get(f"/api/v1/jobs/{job_id}").json()
            assert job["status"] == "draft"
            assert job["original_text"] == "# 岗位要求\n熟练使用 SQL"
        finally:
            if job_id is not None:
                client.delete(f"/api/v1/jobs/{job_id}")
            if role_id is not None:
                with SessionLocal() as session:
                    role = session.get(TargetRole, uuid.UUID(role_id))
                    if role is not None:
                        session.delete(role)
                        session.commit()
