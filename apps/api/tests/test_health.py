from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app

client = TestClient(app)


def test_health_reports_api_is_alive() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_database_is_available(monkeypatch) -> None:
    def database_is_available() -> None:
        return None

    monkeypatch.setattr("app.main.check_database_connection", database_is_available)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_reports_service_unavailable_when_database_is_down(monkeypatch) -> None:
    def database_is_unavailable() -> None:
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr("app.main.check_database_connection", database_is_unavailable)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}
