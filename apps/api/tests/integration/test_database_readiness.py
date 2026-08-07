import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.core.database import engine
from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="set RUN_DATABASE_TESTS=1 with PostgreSQL running",
)


def test_readiness_checks_the_real_database() -> None:
    response = TestClient(app).get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_durable_queue_schema_is_present() -> None:
    inspector = inspect(engine)
    analysis_columns = {
        column["name"] for column in inspector.get_columns("analysis_runs")
    }
    job_columns = {column["name"] for column in inspector.get_columns("job_postings")}
    analysis_indexes = {
        index["name"] for index in inspector.get_indexes("analysis_runs")
    }

    assert {
        "attempt_count",
        "max_attempts",
        "available_at",
        "lease_expires_at",
        "worker_id",
    } <= analysis_columns
    assert "active_analysis_run_id" in job_columns
    assert "uq_analysis_runs_one_active_task_per_job" in analysis_indexes
