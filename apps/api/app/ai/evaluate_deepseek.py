import json
import os
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.ai.contracts import AnalyzeJobRequest, AnalyzerError
from app.ai.deepseek import PROMPT_VERSION, DeepSeekRequirementAnalyzer
from app.ai.evaluation import (
    CasePrediction,
    EvaluationReport,
    load_evaluation_dataset,
    score_dataset,
)
from app.core.config import Settings, get_settings

DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[2] / "tests/fixtures/ai-quality-v2.json"
DEFAULT_REPORT_DIRECTORY = Path(__file__).resolve().parents[4] / ".data/ai-evaluation"


class EvaluationAuthorizationError(RuntimeError):
    pass


class RecordingClient:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self.duration_ms = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def post(self, *args, **kwargs) -> httpx.Response:
        started = time.perf_counter()
        response = self._client.post(*args, **kwargs)
        self.duration_ms += round((time.perf_counter() - started) * 1000)
        try:
            usage = response.json().get("usage", {})
            self.input_tokens += int(usage.get("prompt_tokens", 0))
            self.output_tokens += int(usage.get("completion_tokens", 0))
        except (AttributeError, TypeError, ValueError):
            pass
        return response


def evaluate_if_authorized(
    environ: Mapping[str, str],
    settings: Settings,
    dataset_path: Path,
    client: httpx.Client,
) -> EvaluationReport:
    if environ.get("RUN_DEEPSEEK_EVAL") != "1":
        raise EvaluationAuthorizationError("RUN_DEEPSEEK_EVAL=1 is required")
    if settings.deepseek_api_key is None or not settings.deepseek_api_key.get_secret_value():
        raise EvaluationAuthorizationError("DEEPSEEK_API_KEY is required")

    dataset = load_evaluation_dataset(dataset_path)
    recording_client = RecordingClient(client)
    analyzer = DeepSeekRequirementAnalyzer(
        api_key=settings.deepseek_api_key.get_secret_value(),
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        max_tokens=settings.deepseek_max_tokens,
        timeout_seconds=settings.deepseek_timeout_seconds,
        max_output_retries=settings.deepseek_max_output_retries,
        max_input_chars=settings.deepseek_max_input_chars,
        client=recording_client,
    )
    predictions: dict[str, CasePrediction] = {}
    for case in dataset.cases[:20]:
        before_duration = recording_client.duration_ms
        before_input_tokens = recording_client.input_tokens
        before_output_tokens = recording_client.output_tokens
        error_code: str | None = None
        requirements = []
        try:
            result = analyzer.analyze(
                AnalyzeJobRequest(
                    company_name=case.company_name,
                    job_title=case.job_title,
                    original_text=case.original_text,
                )
            )
            requirements = result.requirements
        except AnalyzerError as error:
            error_code = error.code
        except Exception:
            error_code = "internal_evaluation_error"
        predictions[case.id] = CasePrediction(
            case_id=case.id,
            requirements=requirements,
            error_code=error_code,
            duration_ms=recording_client.duration_ms - before_duration,
            input_tokens=recording_client.input_tokens - before_input_tokens,
            output_tokens=recording_client.output_tokens - before_output_tokens,
        )
    return score_dataset(dataset, predictions)


def write_report(
    report: EvaluationReport,
    *,
    model_name: str,
    output_directory: Path = DEFAULT_REPORT_DIRECTORY,
) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC)
    path = output_directory / f"{generated_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    payload = {
        "generated_at": generated_at.isoformat(),
        "model_name": model_name,
        "prompt_version": PROMPT_VERSION,
        **report.model_dump(mode="json"),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    if os.environ.get("RUN_DEEPSEEK_EVAL") != "1":
        print("拒绝运行：请显式设置 RUN_DEEPSEEK_EVAL=1。")
        return 2
    settings = get_settings()
    if settings.deepseek_api_key is None or not settings.deepseek_api_key.get_secret_value():
        print("拒绝运行：本地 DEEPSEEK_API_KEY 未配置。")
        return 2
    with httpx.Client(
        timeout=settings.deepseek_timeout_seconds,
        follow_redirects=False,
    ) as client:
        report = evaluate_if_authorized(
            os.environ,
            settings,
            DEFAULT_DATASET_PATH,
            client,
        )
    report_path = write_report(report, model_name=settings.deepseek_model)
    print(f"评测完成：{report.case_count} 条样本，报告 {report_path}")
    print(json.dumps(report.metrics.model_dump(), ensure_ascii=False))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
