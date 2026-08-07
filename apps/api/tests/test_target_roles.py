from fastapi.testclient import TestClient


def create_target_role(
    client: TestClient,
    *,
    name: str = "数据分析实习生",
    recruitment_stage: str = "daily_internship",
    description: str | None = "关注互联网公司的数据分析岗位",
):
    return client.post(
        "/api/v1/target-roles",
        json={
            "name": name,
            "recruitment_stage": recruitment_stage,
            "description": description,
        },
    )


def test_create_target_role_trims_and_persists_input(api_client: TestClient) -> None:
    response = create_target_role(api_client, name="  数据分析实习生  ")

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "数据分析实习生"
    assert body["recruitment_stage"] == "daily_internship"
    assert body["description"] == "关注互联网公司的数据分析岗位"
    assert body["id"]
    assert body["created_at"]

    detail = api_client.get(f"/api/v1/target-roles/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == body["id"]


def test_list_target_roles_returns_total_and_newest_first(api_client: TestClient) -> None:
    first = create_target_role(api_client, name="后端开发实习生").json()
    second = create_target_role(api_client, name="产品经理实习生").json()

    response = api_client.get("/api/v1/target-roles?offset=0&limit=1")

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["items"] == [second]
    assert first["id"] != second["id"]


def test_get_unknown_target_role_returns_not_found(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/target-roles/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"detail": "Target role not found"}


def test_create_target_role_rejects_blank_name(api_client: TestClient) -> None:
    response = create_target_role(api_client, name="   ")

    assert response.status_code == 422


def test_create_target_role_rejects_unknown_recruitment_stage(
    api_client: TestClient,
) -> None:
    response = create_target_role(api_client, recruitment_stage="campus")

    assert response.status_code == 422


def test_create_target_role_rejects_oversized_fields(api_client: TestClient) -> None:
    response = create_target_role(api_client, name="岗" * 101, description="说" * 2001)

    assert response.status_code == 422
