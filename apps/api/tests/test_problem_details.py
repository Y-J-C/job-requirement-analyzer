from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.core.problems import install_problem_handlers


def create_problem_app() -> FastAPI:
    application = FastAPI()
    install_problem_handlers(application)

    @application.get("/missing")
    def missing() -> None:
        raise HTTPException(status_code=404, detail="Job posting not found")

    @application.get("/upload-error")
    def upload_error() -> None:
        raise HTTPException(
            status_code=422,
            detail={"code": "file_too_large", "message": "File is too large"},
        )

    @application.get("/items/{item_id}")
    def item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    return application


client = TestClient(create_problem_app())


def test_http_exception_uses_rfc_9457_problem_details() -> None:
    response = client.get("/missing")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Job posting not found",
        "instance": "/missing",
    }


def test_business_error_code_is_a_problem_extension() -> None:
    response = client.get("/upload-error")

    assert response.status_code == 422
    assert response.json()["detail"] == "File is too large"
    assert response.json()["code"] == "file_too_large"


def test_request_validation_errors_include_json_pointers() -> None:
    response = client.get("/items/not-an-integer")

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    payload = response.json()
    assert payload["type"] == "urn:job-analyzer:problem:validation-error"
    assert payload["status"] == 422
    assert payload["instance"] == "/items/not-an-integer"
    assert payload["errors"][0]["pointer"] == "#/path/item_id"
    assert payload["errors"][0]["detail"]


def test_installer_replaces_fastapi_validation_handler() -> None:
    application = create_problem_app()

    assert RequestValidationError in application.exception_handlers
