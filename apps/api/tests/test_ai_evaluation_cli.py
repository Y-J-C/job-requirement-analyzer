import json
from pathlib import Path

import httpx
import pytest

from app.ai.evaluate_deepseek import (
    DEFAULT_DATASET_PATH,
    EvaluationAuthorizationError,
    evaluate_if_authorized,
    write_report,
)
from app.ai.evaluation import load_evaluation_dataset
from app.core.config import Settings

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ai-quality-v2.json"


def settings(api_key: str | None) -> Settings:
    return Settings(deepseek_api_key=api_key, _env_file=None)


def test_default_evaluation_dataset_is_v2() -> None:
    assert DEFAULT_DATASET_PATH.name == "ai-quality-v2.json"


def test_evaluation_without_explicit_switch_sends_no_requests() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise AssertionError("network request must not be sent")

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(EvaluationAuthorizationError, match="RUN_DEEPSEEK_EVAL"):
        evaluate_if_authorized({}, settings("test-only-key"), FIXTURE_PATH, client)

    assert calls == 0


def test_evaluation_without_api_key_sends_no_requests() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise AssertionError("network request must not be sent")

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(EvaluationAuthorizationError, match="DEEPSEEK_API_KEY"):
        evaluate_if_authorized(
            {"RUN_DEEPSEEK_EVAL": "1"},
            settings(None),
            FIXTURE_PATH,
            client,
        )

    assert calls == 0


def test_authorized_evaluation_scores_twenty_cases_and_aggregates_usage(
    tmp_path: Path,
) -> None:
    dataset = load_evaluation_dataset(FIXTURE_PATH)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        case = dataset.cases[calls]
        calls += 1
        requirements = [
            {
                "source_text": expected.source_text,
                "normalized_name": expected.accepted_normalized_names[0],
                "requirement_type": expected.requirement_type.value,
                "explicitness": expected.explicitness.value,
                "confidence": 0.95,
            }
            for expected in case.expected_requirements
        ]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "schema_version": "1.0",
                                    "requirements": requirements,
                                    "warnings": [],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    report = evaluate_if_authorized(
        {"RUN_DEEPSEEK_EVAL": "1"},
        settings("test-only-key"),
        FIXTURE_PATH,
        client,
    )
    report_path = write_report(
        report,
        model_name="deepseek-v4-flash",
        output_directory=tmp_path,
    )
    saved = report_path.read_text(encoding="utf-8")

    assert calls == 20
    assert report.passed is True
    assert report.total_input_tokens == 200
    assert report.total_output_tokens == 100
    assert '"dataset_version": "ai-quality-v2"' in saved
    assert '"prompt_version": "requirements-v4"' in saved
    assert "authorization" not in saved.casefold()
    assert '"choices"' not in saved
    assert "original_text" not in saved
