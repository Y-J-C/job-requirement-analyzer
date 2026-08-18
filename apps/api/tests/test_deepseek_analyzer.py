import json

import httpx
import pytest

from app.ai.contracts import AnalyzeJobRequest, AnalyzerOutputError
from app.ai.deepseek import PROMPT_VERSION, DeepSeekRequirementAnalyzer


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
                                    "company_name": "示例公司",
                                    "job_title": "数据分析实习生",
                                    "city": "上海",
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
            original_text="示例公司招聘上海数据分析实习生。岗位要求：熟练使用 SQL",
        )
    )

    assert result.requirements[0].normalized_name == "SQL"
    assert result.company_name == "示例公司"
    assert result.job_title == "数据分析实习生"
    assert result.city == "上海"
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
    prompt = " ".join(message["content"] for message in body["messages"])
    assert PROMPT_VERSION == "requirements-v4"
    assert "json" in prompt.lower()
    assert "空数组" in prompt
    assert "一个输出只能" in prompt
    assert "独立技能" in prompt
    assert "可替代工具" in prompt
    for boundary in ("到岗天数", "持续时间", "地点", "办公方式", "学历", "毕业年份"):
        assert boundary in prompt
    assert "normalized_name" in prompt
    assert "工作职责不是" in prompt
    assert "eligibility" in prompt
    assert "可放宽" in prompt
    assert "uncertain" in prompt
    assert "Java" in prompt
    assert "Go" in prompt
    assert "10 周" in prompt
    assert "company_name" in prompt
    assert "job_title" in prompt
    assert "无法从原文" in prompt
    assert "熟练使用 Python、SQL，有数据分析项目经验者优先。" not in prompt
    assert "每周至少到岗 4 天，可连续实习 3 个月以上。" not in prompt


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


def test_deepseek_analyzer_accepts_ocr_line_break_inside_chinese_evidence() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
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
                                            "source_text": "能够独立完成算法设计与实现",
                                            "normalized_name": "算法设计与实现",
                                            "requirement_type": "core_competency",
                                            "explicitness": "explicit",
                                            "confidence": 0.95,
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
        max_output_retries=0,
    )

    result = analyzer.analyze(
        AnalyzeJobRequest(original_text="具备扎实基础，能够独立完成算\n法设计与实现；")
    )

    assert result.requirements[0].source_text == "能够独立完成算法设计与实现"


def test_deepseek_analyzer_accepts_ocr_line_break_after_chinese_punctuation() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
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
                                            "source_text": "数学、统计学、声学、光学或相关专业",
                                            "normalized_name": "数学、统计学、声学、光学相关专业",
                                            "requirement_type": "eligibility",
                                            "explicitness": "explicit",
                                            "confidence": 0.95,
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
        max_output_retries=0,
    )

    result = analyzer.analyze(
        AnalyzeJobRequest(original_text="专业要求：数学、统计学、声学、\n光学或相关专业；")
    )

    assert result.requirements[0].source_text == "数学、统计学、声学、光学或相关专业"


def test_deepseek_analyzer_accepts_an_empty_requirement_list() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "schema_version": "1.0",
                                    "requirements": [],
                                    "warnings": ["未发现候选人准入条件"],
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
    )

    result = analyzer.analyze(
        AnalyzeJobRequest(
            original_text="工作内容：协助整理选题和维护排期。",
        )
    )

    assert result.requirements == []
    assert result.company_name is None
    assert result.job_title is None
    assert PROMPT_VERSION == "requirements-v4"


def test_deepseek_analyzer_rejects_invented_job_metadata() -> None:
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
                                    "company_name": "不存在的公司",
                                    "job_title": None,
                                    "city": None,
                                    "requirements": [],
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

    with pytest.raises(AnalyzerOutputError):
        analyzer.analyze(AnalyzeJobRequest(original_text="岗位要求：熟练使用 SQL"))

    assert calls == 2
