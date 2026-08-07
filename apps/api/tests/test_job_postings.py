from fastapi.testclient import TestClient


def create_target_role(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/target-roles",
        json={
            "name": "数据分析实习生",
            "recruitment_stage": "daily_internship",
            "description": None,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_job(client: TestClient, role_id: str, **overrides):
    payload = {
        "company_name": "示例科技",
        "job_title": "数据分析实习生",
        "recruitment_stage": "daily_internship",
        "city": "上海",
        "source_url": "https://example.com/jobs/1",
        "original_text": "负责业务数据分析，要求熟练使用 SQL。",
    }
    payload.update(overrides)
    return client.post(f"/api/v1/target-roles/{role_id}/jobs", json=payload)


def test_create_and_get_job_posting_preserves_original_text(api_client: TestClient) -> None:
    role = create_target_role(api_client)

    response = create_job(
        api_client,
        role["id"],
        company_name="  示例科技  ",
        original_text="  负责业务数据分析，要求熟练使用 SQL。  ",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["target_role_id"] == role["id"]
    assert body["company_name"] == "示例科技"
    assert body["original_text"] == "负责业务数据分析，要求熟练使用 SQL。"
    assert body["status"] == "draft"
    assert body["collected_at"]

    detail = api_client.get(f"/api/v1/jobs/{body['id']}")
    assert detail.status_code == 200
    assert detail.json() == body


def test_list_and_delete_jobs_updates_target_role_count(api_client: TestClient) -> None:
    role = create_target_role(api_client)
    job = create_job(api_client, role["id"]).json()

    listing = api_client.get(f"/api/v1/target-roles/{role['id']}/jobs")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"] == [job]

    roles = api_client.get("/api/v1/target-roles").json()
    assert roles["items"][0]["job_count"] == 1

    role_detail = api_client.get(f"/api/v1/target-roles/{role['id']}").json()
    assert role_detail["job_count"] == 1

    deletion = api_client.delete(f"/api/v1/jobs/{job['id']}")
    assert deletion.status_code == 204
    assert api_client.get(f"/api/v1/jobs/{job['id']}").status_code == 404

    roles_after_delete = api_client.get("/api/v1/target-roles").json()
    assert roles_after_delete["items"][0]["job_count"] == 0


def test_job_routes_return_not_found_for_unknown_resources(api_client: TestClient) -> None:
    missing_id = "00000000-0000-0000-0000-000000000000"

    assert create_job(api_client, missing_id).status_code == 404
    assert api_client.get(f"/api/v1/target-roles/{missing_id}/jobs").status_code == 404
    assert api_client.get(f"/api/v1/jobs/{missing_id}").status_code == 404
    assert api_client.delete(f"/api/v1/jobs/{missing_id}").status_code == 404


def test_create_job_rejects_invalid_input(api_client: TestClient) -> None:
    role = create_target_role(api_client)

    assert create_job(api_client, role["id"], company_name="   ").status_code == 422
    assert create_job(api_client, role["id"], source_url="file:///etc/passwd").status_code == 422
    assert create_job(api_client, role["id"], original_text="   ").status_code == 422
    assert create_job(api_client, role["id"], original_text="字" * 100001).status_code == 422
