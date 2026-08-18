from uuid import UUID

from fastapi.testclient import TestClient

from app.models.job_posting import JobPosting, JobPostingStatus
from app.services.summary import calculate_coverage_rate, sample_size_notice


def create_role(client: TestClient, name: str = "数据分析实习生") -> dict:
    response = client.post(
        "/api/v1/target-roles",
        json={
            "name": name,
            "recruitment_stage": "daily_internship",
            "description": None,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_job(client: TestClient, role_id: str, company_name: str) -> dict:
    response = client.post(
        f"/api/v1/target-roles/{role_id}/jobs",
        json={
            "company_name": company_name,
            "job_title": "数据分析实习生",
            "recruitment_stage": "daily_internship",
            "city": "上海",
            "source_url": None,
            "original_text": "熟练使用 SQL，了解 Python，有相关经验者优先。",
        },
    )
    assert response.status_code == 201
    return response.json()


def add_requirement(
    client: TestClient,
    job_id: str,
    *,
    normalized_name: str,
    requirement_type: str,
    original_text: str,
    explicitness: str = "explicit",
) -> dict:
    response = client.post(
        f"/api/v1/jobs/{job_id}/requirements",
        json={
            "normalized_name": normalized_name,
            "requirement_type": requirement_type,
            "original_text": original_text,
            "explicitness": explicitness,
        },
    )
    assert response.status_code == 201
    return response.json()


def confirm_job(client: TestClient, job_id: str) -> None:
    response = client.post(f"/api/v1/jobs/{job_id}/confirm-requirements")
    assert response.status_code == 200


def test_summary_deduplicates_by_job_and_preserves_evidence(
    api_client: TestClient,
) -> None:
    role = create_role(api_client)
    first_job = create_job(api_client, role["id"], "甲公司")
    second_job = create_job(api_client, role["id"], "乙公司")
    unconfirmed_job = create_job(api_client, role["id"], "未确认公司")

    add_requirement(
        api_client,
        first_job["id"],
        normalized_name="SQL",
        requirement_type="core_competency",
        original_text="熟练使用 SQL",
    )
    add_requirement(
        api_client,
        first_job["id"],
        normalized_name="SQL",
        requirement_type="core_competency",
        original_text="能够编写复杂 SQL 查询",
        explicitness="implicit",
    )
    add_requirement(
        api_client,
        first_job["id"],
        normalized_name="Python",
        requirement_type="preferred",
        original_text="了解 Python 者优先",
    )
    confirm_job(api_client, first_job["id"])

    add_requirement(
        api_client,
        second_job["id"],
        normalized_name="SQL",
        requirement_type="core_competency",
        original_text="掌握 SQL",
    )
    add_requirement(
        api_client,
        second_job["id"],
        normalized_name="SQL",
        requirement_type="preferred",
        original_text="熟悉 SQL 优先",
    )
    confirm_job(api_client, second_job["id"])

    add_requirement(
        api_client,
        unconfirmed_job["id"],
        normalized_name="SQL",
        requirement_type="core_competency",
        original_text="熟练使用 SQL",
    )

    response = api_client.get(f"/api/v1/target-roles/{role['id']}/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["target_role_id"] == role["id"]
    assert body["target_role_name"] == role["name"]
    assert body["sample_job_count"] == 3
    assert body["confirmed_job_count"] == 2
    assert body["sample_size_notice"] == "样本量很小，仅供查看录入结果。"
    assert [
        (item["normalized_name"], item["requirement_type"])
        for item in body["items"]
    ] == [
        ("SQL", "core_competency"),
        ("Python", "preferred"),
        ("SQL", "preferred"),
    ]

    sql_core = body["items"][0]
    assert sql_core["mentioning_job_count"] == 2
    assert sql_core["confirmed_job_count"] == 2
    assert sql_core["coverage_rate"] == 1.0
    assert sql_core["evidence_count"] == 3
    assert sql_core["explicit_evidence_count"] == 2
    assert [evidence["company_name"] for evidence in sql_core["evidence"]] == [
        "乙公司",
        "甲公司",
        "甲公司",
    ]
    assert {evidence["job_id"] for evidence in sql_core["evidence"]} == {
        first_job["id"],
        second_job["id"],
    }
    assert all(evidence["company_name"] != "未确认公司" for evidence in sql_core["evidence"])


def test_summary_filter_keeps_confirmed_job_denominator(api_client: TestClient) -> None:
    role = create_role(api_client)
    first_job = create_job(api_client, role["id"], "甲公司")
    second_job = create_job(api_client, role["id"], "乙公司")
    add_requirement(
        api_client,
        first_job["id"],
        normalized_name="Python",
        requirement_type="preferred",
        original_text="了解 Python 者优先",
    )
    add_requirement(
        api_client,
        second_job["id"],
        normalized_name="SQL",
        requirement_type="core_competency",
        original_text="掌握 SQL",
    )
    confirm_job(api_client, first_job["id"])
    confirm_job(api_client, second_job["id"])

    response = api_client.get(
        f"/api/v1/target-roles/{role['id']}/summary?requirement_type=preferred"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["confirmed_job_count"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["normalized_name"] == "Python"
    assert body["items"][0]["coverage_rate"] == 0.5


def test_empty_summary_and_error_boundaries(api_client: TestClient) -> None:
    role = create_role(api_client)
    create_job(api_client, role["id"], "未确认公司")
    missing_id = "00000000-0000-0000-0000-000000000000"

    response = api_client.get(f"/api/v1/target-roles/{role['id']}/summary")

    assert response.status_code == 200
    assert response.json()["sample_job_count"] == 1
    assert response.json()["confirmed_job_count"] == 0
    assert response.json()["items"] == []
    assert api_client.get(f"/api/v1/target-roles/{missing_id}/summary").status_code == 404
    assert api_client.get(
        f"/api/v1/target-roles/{role['id']}/summary?requirement_type=hard"
    ).status_code == 422


def test_sample_size_notice_boundaries() -> None:
    assert sample_size_notice(4) == "样本量很小，仅供查看录入结果。"
    assert sample_size_notice(5) == "可观察初步方向，不宜代表整体市场。"
    assert sample_size_notice(14) == "可观察初步方向，不宜代表整体市场。"
    assert sample_size_notice(15) == "样本仍受来源、时间和岗位方向影响，请结合证据审慎解读。"


def test_coverage_rate_uses_conventional_half_up_rounding() -> None:
    assert calculate_coverage_rate(1, 32) == 0.0313
    assert calculate_coverage_rate(0, 0) == 0


def test_selected_summary_only_uses_explicitly_selected_jobs(
    api_client: TestClient,
) -> None:
    role = create_role(api_client)
    first = create_job(api_client, role["id"], "甲公司")
    second = create_job(api_client, role["id"], "乙公司")
    third = create_job(api_client, role["id"], "丙公司")
    for job, name in [(first, "SQL"), (second, "Excel"), (third, "SQL")]:
        add_requirement(
            api_client,
            job["id"],
            normalized_name=name,
            requirement_type="core_competency",
            original_text=f"要求掌握 {name}",
        )
        confirm_job(api_client, job["id"])

    response = api_client.post(
        f"/api/v1/target-roles/{role['id']}/summary",
        json={"job_ids": [first["id"], third["id"]]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_job_ids"] == [first["id"], third["id"]]
    assert body["sample_job_count"] == 2
    assert body["confirmed_job_count"] == 2
    assert [(item["normalized_name"], item["coverage_rate"]) for item in body["items"]] == [
        ("SQL", 1.0)
    ]
    assert {evidence["job_id"] for evidence in body["items"][0]["evidence"]} == {
        first["id"],
        third["id"],
    }


def test_selected_summary_rejects_invalid_job_sets(api_client: TestClient) -> None:
    role = create_role(api_client)
    other_role = create_role(api_client, "产品经理")
    confirmed = create_job(api_client, role["id"], "甲公司")
    unconfirmed = create_job(api_client, role["id"], "未确认公司")
    cross_role = create_job(api_client, other_role["id"], "跨方向公司")
    add_requirement(
        api_client,
        confirmed["id"],
        normalized_name="SQL",
        requirement_type="core_competency",
        original_text="要求掌握 SQL",
    )
    confirm_job(api_client, confirmed["id"])
    endpoint = f"/api/v1/target-roles/{role['id']}/summary"

    assert api_client.post(endpoint, json={"job_ids": [confirmed["id"]]}).status_code == 422
    assert api_client.post(
        endpoint, json={"job_ids": [confirmed["id"], confirmed["id"]]}
    ).status_code == 422
    assert api_client.post(
        endpoint, json={"job_ids": [confirmed["id"], unconfirmed["id"]]}
    ).status_code == 422
    assert api_client.post(
        endpoint, json={"job_ids": [confirmed["id"], cross_role["id"]]}
    ).status_code == 422

    add_requirement(
        api_client,
        unconfirmed["id"],
        normalized_name="Python",
        requirement_type="core_competency",
        original_text="要求掌握 Python",
    )
    confirm_job(api_client, unconfirmed["id"])
    with api_client.app.state.testing_session_factory() as session:
        confirmed_job = session.get(JobPosting, UUID(confirmed["id"]))
        assert confirmed_job is not None
        confirmed_job.status = JobPostingStatus.ANALYZING
        session.commit()
    assert api_client.post(
        endpoint, json={"job_ids": [confirmed["id"], unconfirmed["id"]]}
    ).status_code == 422
