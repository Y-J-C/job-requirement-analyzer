import json
import re
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.contracts import ExtractedRequirement
from app.models.requirement_item import RequirementExplicitness, RequirementType

REQUIRED_SCENARIOS = frozenset(
    {
        "chinese",
        "mixed_language",
        "compound",
        "structured_constraint",
        "preference_strength",
        "ambiguous",
        "messy_format",
        "duties_mixed",
        "prompt_injection",
        "no_requirements",
    }
)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


class ExpectedRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_text: str = Field(min_length=1, max_length=2_000)
    accepted_normalized_names: list[
        Annotated[str, Field(min_length=1, max_length=200)]
    ] = Field(min_length=1, max_length=10)
    requirement_type: RequirementType
    explicitness: RequirementExplicitness


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    scenarios: set[str] = Field(min_length=1)
    company_name: str = Field(min_length=1, max_length=100)
    job_title: str = Field(min_length=1, max_length=150)
    original_text: str = Field(min_length=1, max_length=30_000)
    expected_requirements: list[ExpectedRequirement] = Field(default_factory=list, max_length=100)
    forbidden_normalized_names: list[
        Annotated[str, Field(min_length=1, max_length=200)]
    ] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_expected_evidence(self) -> Self:
        original = normalize_text(self.original_text)
        for requirement in self.expected_requirements:
            if normalize_text(requirement.source_text) not in original:
                raise ValueError(
                    f"expected evidence is not present in original text for case {self.id}"
                )
        return self


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(pattern=r"^ai-quality-v\d+$")
    cases: list[EvaluationCase] = Field(min_length=20, max_length=100)

    @model_validator(mode="after")
    def validate_dataset(self) -> Self:
        case_ids = [case.id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("case IDs must be unique")
        scenarios = {scenario for case in self.cases for scenario in case.scenarios}
        missing = REQUIRED_SCENARIOS - scenarios
        if missing:
            raise ValueError(f"required scenarios are missing: {', '.join(sorted(missing))}")
        return self


def load_evaluation_dataset(path: Path) -> EvaluationDataset:
    return EvaluationDataset.model_validate(json.loads(path.read_text(encoding="utf-8")))


class CasePrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    requirements: list[ExtractedRequirement] = Field(default_factory=list, max_length=100)
    error_code: str | None = None
    duration_ms: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


class CaseScore(BaseModel):
    case_id: str
    expected_count: int
    prediction_count: int
    matched_count: int
    correct_type_count: int
    correct_explicitness_count: int
    traceable_prediction_count: int
    forbidden_hit_count: int


class QualityThresholds(BaseModel):
    structural_success_rate: float = 1.0
    evidence_traceability_rate: float = 1.0
    unsupported_evidence_rate: float = 0.0
    forbidden_hit_rate: float = 0.0
    precision: float = 0.90
    recall: float = 0.85
    type_accuracy: float = 0.90
    explicitness_accuracy: float = 0.85


class QualityMetrics(BaseModel):
    structural_success_rate: float
    evidence_traceability_rate: float
    unsupported_evidence_rate: float
    forbidden_hit_rate: float
    precision: float
    recall: float
    type_accuracy: float
    explicitness_accuracy: float


class CaseDifference(BaseModel):
    expected_names: list[str]
    predicted_names: list[str]


class EvaluationReport(BaseModel):
    dataset_version: str
    case_count: int
    metrics: QualityMetrics
    passed: bool
    failed_thresholds: dict[str, float]
    failed_case_ids: list[str]
    case_errors: dict[str, str]
    case_differences: dict[str, CaseDifference]
    total_duration_ms: int
    total_input_tokens: int
    total_output_tokens: int


def _evidence_matches(expected: str, predicted: str) -> bool:
    normalized_expected = normalize_text(expected)
    normalized_predicted = normalize_text(predicted)
    return (
        normalized_expected in normalized_predicted
        or normalized_predicted in normalized_expected
    )


def _maximum_matches(
    case: EvaluationCase,
    predictions: list[ExtractedRequirement],
) -> list[tuple[int, int]]:
    adjacency: list[list[int]] = []
    for prediction in predictions:
        normalized_name = normalize_text(prediction.normalized_name)
        adjacency.append(
            [
                index
                for index, expected in enumerate(case.expected_requirements)
                if normalized_name
                in {normalize_text(name) for name in expected.accepted_normalized_names}
                and _evidence_matches(expected.source_text, prediction.source_text)
            ]
        )

    expected_to_prediction = [-1] * len(case.expected_requirements)

    def assign(prediction_index: int, visited: set[int]) -> bool:
        for expected_index in adjacency[prediction_index]:
            if expected_index in visited:
                continue
            visited.add(expected_index)
            previous = expected_to_prediction[expected_index]
            if previous == -1 or assign(previous, visited):
                expected_to_prediction[expected_index] = prediction_index
                return True
        return False

    for prediction_index in range(len(predictions)):
        assign(prediction_index, set())
    return [
        (expected_index, prediction_index)
        for expected_index, prediction_index in enumerate(expected_to_prediction)
        if prediction_index >= 0
    ]


def score_case(
    case: EvaluationCase,
    predictions: list[ExtractedRequirement],
) -> CaseScore:
    matches = _maximum_matches(case, predictions)
    original = normalize_text(case.original_text)
    forbidden = {normalize_text(name) for name in case.forbidden_normalized_names}
    return CaseScore(
        case_id=case.id,
        expected_count=len(case.expected_requirements),
        prediction_count=len(predictions),
        matched_count=len(matches),
        correct_type_count=sum(
            case.expected_requirements[expected_index].requirement_type
            == predictions[prediction_index].requirement_type
            for expected_index, prediction_index in matches
        ),
        correct_explicitness_count=sum(
            case.expected_requirements[expected_index].explicitness
            == predictions[prediction_index].explicitness
            for expected_index, prediction_index in matches
        ),
        traceable_prediction_count=sum(
            normalize_text(prediction.source_text) in original for prediction in predictions
        ),
        forbidden_hit_count=sum(
            normalize_text(prediction.normalized_name) in forbidden for prediction in predictions
        ),
    )


def _ratio(numerator: int, denominator: int, *, empty: float) -> float:
    return numerator / denominator if denominator else empty


def score_dataset(
    dataset: EvaluationDataset,
    predictions: dict[str, CasePrediction],
    *,
    thresholds: QualityThresholds | None = None,
) -> EvaluationReport:
    active_thresholds = thresholds or QualityThresholds()
    scores: list[CaseScore] = []
    structural_successes = 0
    failed_case_ids: set[str] = set()
    case_errors: dict[str, str] = {}
    case_differences: dict[str, CaseDifference] = {}
    for case in dataset.cases:
        prediction = predictions.get(case.id)
        if prediction is None or prediction.error_code is not None:
            failed_case_ids.add(case.id)
            case_errors[case.id] = (
                prediction.error_code
                if prediction is not None
                else "missing_prediction"
            )
            prediction = prediction or CasePrediction(
                case_id=case.id,
                error_code="missing_prediction",
            )
        else:
            structural_successes += 1
        score = score_case(case, prediction.requirements)
        scores.append(score)
        if (
            score.matched_count != score.expected_count
            or score.matched_count != score.prediction_count
            or score.correct_type_count != score.matched_count
            or score.correct_explicitness_count != score.matched_count
            or score.traceable_prediction_count != score.prediction_count
            or score.forbidden_hit_count
        ):
            failed_case_ids.add(case.id)
            case_errors.setdefault(case.id, "quality_mismatch")
        if case.id in failed_case_ids:
            case_differences[case.id] = CaseDifference(
                expected_names=[
                    expected.accepted_normalized_names[0]
                    for expected in case.expected_requirements
                ],
                predicted_names=[
                    requirement.normalized_name for requirement in prediction.requirements
                ],
            )

    expected_count = sum(score.expected_count for score in scores)
    prediction_count = sum(score.prediction_count for score in scores)
    matched_count = sum(score.matched_count for score in scores)
    traceable_count = sum(score.traceable_prediction_count for score in scores)
    forbidden_count = sum(score.forbidden_hit_count for score in scores)
    metrics = QualityMetrics(
        structural_success_rate=_ratio(structural_successes, len(scores), empty=0),
        evidence_traceability_rate=_ratio(traceable_count, prediction_count, empty=1),
        unsupported_evidence_rate=_ratio(
            prediction_count - traceable_count,
            prediction_count,
            empty=0,
        ),
        forbidden_hit_rate=_ratio(forbidden_count, prediction_count, empty=0),
        precision=_ratio(matched_count, prediction_count, empty=float(expected_count == 0)),
        recall=_ratio(matched_count, expected_count, empty=1),
        type_accuracy=_ratio(
            sum(score.correct_type_count for score in scores),
            matched_count,
            empty=float(expected_count == 0),
        ),
        explicitness_accuracy=_ratio(
            sum(score.correct_explicitness_count for score in scores),
            matched_count,
            empty=float(expected_count == 0),
        ),
    )
    failed_thresholds = {
        name: value
        for name, value in metrics.model_dump().items()
        if (
            value > getattr(active_thresholds, name)
            if name in {"unsupported_evidence_rate", "forbidden_hit_rate"}
            else value < getattr(active_thresholds, name)
        )
    }
    return EvaluationReport(
        dataset_version=dataset.version,
        case_count=len(dataset.cases),
        metrics=metrics,
        passed=not failed_thresholds,
        failed_thresholds=failed_thresholds,
        failed_case_ids=sorted(failed_case_ids),
        case_errors=case_errors,
        case_differences=case_differences,
        total_duration_ms=sum(prediction.duration_ms for prediction in predictions.values()),
        total_input_tokens=sum(prediction.input_tokens for prediction in predictions.values()),
        total_output_tokens=sum(prediction.output_tokens for prediction in predictions.values()),
    )
