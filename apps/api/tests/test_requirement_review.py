import uuid

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.models.job_posting import JobPosting


def create_job(client: TestClient) -> dict:
    role_response = client.post(
        "/api/v1/target-roles",
        json={
            "name": "数据分析实习生",
            "recruitment_stage": "daily_internship",
            "description": None,
        },
    )
    assert role_response.status_code == 201
    role = role_response.json()
    job_response = client.post(
        f"/api/v1/target-roles/{role['id']}/jobs",
        json={
            "company_name": "示例科技",
            "job_title": "数据分析实习生",
            "recruitment_stage": "daily_internship",
            "city": "上海",
            "source_url": None,
            "original_text": "熟练使用 SQL，有数据分析项目经验者优先。",
        },
    )
    assert job_response.status_code == 201
    return job_response.json()


def create_requirement(client: TestClient, job_id: str, **overrides):
    payload = {
        "original_text": "熟练使用 SQL",
        "normalized_name": "SQL",
        "requirement_type": "core_competency",
        "explicitness": "explicit",
    }
    payload.update(overrides)
    return client.post(f"/api/v1/jobs/{job_id}/requirements", json=payload)


def test_create_and_list_manual_requirement(api_client: TestClient) -> None:
    job = create_job(api_client)

    empty = api_client.get(f"/api/v1/jobs/{job['id']}/requirements")
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "total": 0, "job_status": "draft"}

    response = create_requirement(
        api_client,
        job["id"],
        normalized_name="  SQL  ",
        original_text="  熟练使用 SQL  ",
    )

    assert response.status_code == 201
    item = response.json()
    assert item["normalized_name"] == "SQL"
    assert item["original_text"] == "熟练使用 SQL"
    assert item["requirement_type"] == "core_competency"
    assert item["explicitness"] == "explicit"
    assert item["confidence"] is None
    assert item["user_modified"] is True
    assert item["user_confirmed"] is False

    listing = api_client.get(f"/api/v1/jobs/{job['id']}/requirements")
    assert listing.status_code == 200
    assert listing.json()["items"] == [item]
    assert listing.json()["total"] == 1
    assert listing.json()["job_status"] == "review_required"


def test_confirmed_requirements_are_read_only(api_client: TestClient) -> None:
    job = create_job(api_client)
    item = create_requirement(api_client, job["id"]).json()

    confirmation = api_client.post(f"/api/v1/jobs/{job['id']}/confirm-requirements")

    assert confirmation.status_code == 200
    assert confirmation.json()["status"] == "confirmed"
    confirmed_items = api_client.get(f"/api/v1/jobs/{job['id']}/requirements").json()
    assert confirmed_items["items"][0]["user_confirmed"] is True

    update = api_client.patch(
        f"/api/v1/requirements/{item['id']}",
        json={"normalized_name": "结构化查询语言"},
    )

    assert update.status_code == 409
    assert api_client.delete(f"/api/v1/requirements/{item['id']}").status_code == 409
    assert create_requirement(api_client, job["id"]).status_code == 409
    unchanged = api_client.get(f"/api/v1/jobs/{job['id']}/requirements").json()
    assert unchanged["job_status"] == "confirmed"
    assert unchanged["items"][0]["normalized_name"] == "SQL"
    assert unchanged["items"][0]["user_confirmed"] is True


def test_delete_last_unconfirmed_requirement_returns_job_to_draft(api_client: TestClient) -> None:
    job = create_job(api_client)
    item = create_requirement(api_client, job["id"]).json()
    remaining_item = create_requirement(
        api_client,
        job["id"],
        original_text="数据分析项目经验者优先",
        normalized_name="数据分析项目经验",
        requirement_type="preferred",
    ).json()
    deletion = api_client.delete(f"/api/v1/requirements/{item['id']}")

    assert deletion.status_code == 204
    listing = api_client.get(f"/api/v1/jobs/{job['id']}/requirements").json()
    assert listing["job_status"] == "review_required"
    assert listing["items"][0]["id"] == remaining_item["id"]
    assert listing["items"][0]["user_confirmed"] is False
    assert api_client.get(f"/api/v1/requirements/{item['id']}").status_code == 404

    assert api_client.delete(f"/api/v1/requirements/{remaining_item['id']}").status_code == 204
    listing = api_client.get(f"/api/v1/jobs/{job['id']}/requirements").json()
    assert listing == {"items": [], "total": 0, "job_status": "draft"}


def test_confirm_empty_requirement_set_is_rejected(api_client: TestClient) -> None:
    job = create_job(api_client)

    response = api_client.post(f"/api/v1/jobs/{job['id']}/confirm-requirements")

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "Cannot confirm a job without requirements"
    assert response.json()["title"] == "Conflict"


def test_confirm_requirements_is_rejected_when_job_metadata_is_missing(api_client) -> None:
    job = create_job(api_client)
    with api_client.app.state.testing_session_factory() as session:
        session.execute(
            update(JobPosting)
            .where(JobPosting.id == uuid.UUID(job["id"]))
            .values(company_name=None, job_title=None)
        )
        session.commit()
    assert create_requirement(api_client, job["id"]).status_code == 201

    response = api_client.post(f"/api/v1/jobs/{job['id']}/confirm-requirements")

    assert response.status_code == 409


def test_requirement_routes_validate_input_and_unknown_resources(
    api_client: TestClient,
) -> None:
    job = create_job(api_client)
    missing_id = "00000000-0000-0000-0000-000000000000"

    assert create_requirement(api_client, missing_id).status_code == 404
    assert api_client.get(f"/api/v1/jobs/{missing_id}/requirements").status_code == 404
    assert api_client.post(f"/api/v1/jobs/{missing_id}/confirm-requirements").status_code == 404
    assert api_client.patch(
        f"/api/v1/requirements/{missing_id}", json={"normalized_name": "SQL"}
    ).status_code == 404
    assert api_client.delete(f"/api/v1/requirements/{missing_id}").status_code == 404

    assert create_requirement(api_client, job["id"], normalized_name="   ").status_code == 422
    assert create_requirement(
        api_client, job["id"], requirement_type="hard_requirement"
    ).status_code == 422
    assert create_requirement(api_client, job["id"], explicitness="guessed").status_code == 422
    assert create_requirement(
        api_client, job["id"], original_text="证" * 2001
    ).status_code == 422
    requirement = create_requirement(api_client, job["id"]).json()
    assert api_client.patch(
        f"/api/v1/requirements/{requirement['id']}", json={}
    ).status_code == 422
    assert api_client.patch(
        f"/api/v1/requirements/{requirement['id']}", json={"normalized_name": None}
    ).status_code == 422
    assert api_client.get(
        f"/api/v1/jobs/{job['id']}/requirements?limit=101"
    ).status_code == 422
