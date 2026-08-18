from app.main import app


def test_openapi_uses_standard_contract_and_problem_schema() -> None:
    schema = app.openapi()

    assert schema["openapi"].startswith("3.1.")
    problem_schema = schema["components"]["schemas"]["ProblemDetails"]
    assert {"type", "title", "status", "detail", "instance"}.issubset(
        problem_schema["properties"]
    )

    validation_response = schema["paths"]["/api/v1/jobs/{job_id}"]["get"]["responses"][
        "422"
    ]
    assert set(validation_response["content"]) == {"application/problem+json"}
    assert validation_response["content"]["application/problem+json"]["schema"] == {
        "$ref": "#/components/schemas/ProblemDetails"
    }


def test_openapi_exposes_business_api_without_an_authentication_scheme() -> None:
    schema = app.openapi()

    assert "securitySchemes" not in schema["components"]
    assert "security" not in schema["paths"]["/api/v1/target-roles"]["get"]
    assert "security" not in schema["paths"]["/health"]["get"]
