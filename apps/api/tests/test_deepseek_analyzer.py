import json

import httpx
import pytest

from app.ai.contracts import AnalyzeJobRequest, AnalyzerOutputError
from app.ai.deepseek import DeepSeekRequirementAnalyzer


def test_deepseek_analyzer_uses_official_chat_json_contract() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "schema_version": "1.0",
                                    "requirements": [
                                        {
                                            "source_text": "熟练使用 SQL",
                                            "normalized_name": "SQL",
                                            "requirement_type": "core_competency",
                                            "explicitness": "explicit",
                                            "confidence": 0.98,
                                        }
                                    ],
                                    "warnings": [],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    analyzer = DeepSeekRequirementAnalyzer(
        api_key="test-only-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        max_tokens=2000,
        max_output_retries=1,
        client=client,
    )

    result = analyzer.analyze(
        AnalyzeJobRequest(
            company_name="示例公司",
            job_title="数据分析实习生",
            original_text="岗位要求：熟练使用 SQL",
        )
    )

    assert result.requirements[0].normalized_name == "SQL"
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["authorization"] == "Bearer test-only-key"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "deepseek-v4-flash"
    assert body["thinking"] == {"type": "disabled"}
    assert body["response_format"] == {"type": "json_object"}
    assert body["temperature"] == 0
    assert body["stream"] is False
    assert body["max_tokens"] == 2000
    assert "json" in " ".join(message["content"] for message in body["messages"]).lower()


def test_deepseek_analyzer_retries_then_rejects_untraceable_evidence() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "schema_version": "1.0",
                                    "requirements": [
                                        {
                                            "source_text": "要求精通 Kubernetes",
                                            "normalized_name": "Kubernetes",
                                            "requirement_type": "core_competency",
                                            "explicitness": "explicit",
                                            "confidence": 0.9,
                                        }
                                    ],
                                    "warnings": [],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    analyzer = DeepSeekRequirementAnalyzer(
        api_key="test-only-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_output_retries=1,
    )

    with pytest.raises(AnalyzerOutputError) as error:
        analyzer.analyze(
            AnalyzeJobRequest(
                company_name="示例公司",
                job_title="数据分析实习生",
                original_text="岗位要求：熟练使用 SQL",
            )
        )

    assert error.value.code == "invalid_model_output"
    assert calls == 2
