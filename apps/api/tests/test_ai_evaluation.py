import json
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ai.contracts import ExtractedRequirement
from app.ai.evaluation import (
    REQUIRED_SCENARIOS,
    CasePrediction,
    EvaluationCase,
    EvaluationDataset,
    ExpectedRequirement,
    QualityThresholds,
    load_evaluation_dataset,
    score_case,
    score_dataset,
)
from app.models.requirement_item import RequirementExplicitness, RequirementType

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ai-quality-v1.json"
V2_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ai-quality-v2.json"
V1_SHA256 = "8730b704e6155b2684f8a67f9cfe0ac3d1ea8fdf1ed1944cf3dca50242c19986"
APPROVED_V2_ALIASES = {
    ("ambiguous-quality-05", 0): {"综合能力优秀"},
    ("english-requirements-14", 1): {"Written English Communication"},
    ("language-certificate-17", 0): {"英语六级500分以上"},
    ("language-certificate-17", 1): {"英文邮件沟通能力"},
}


def test_dataset_fixture_has_required_size_scenarios_and_traceable_evidence() -> None:
    dataset = load_evaluation_dataset(FIXTURE_PATH)

    assert dataset.version == "ai-quality-v1"
    assert len(dataset.cases) >= 20
    assert REQUIRED_SCENARIOS <= {
        scenario for case in dataset.cases for scenario in case.scenarios
    }
    assert any(not case.expected_requirements for case in dataset.cases)
    assert sum("prompt_injection" in case.scenarios for case in dataset.cases) >= 2


def test_v1_dataset_is_immutable() -> None:
    assert sha256(FIXTURE_PATH.read_bytes()).hexdigest() == V1_SHA256


def test_dataset_v2_only_adds_approved_aliases() -> None:
    v1 = load_evaluation_dataset(FIXTURE_PATH)
    v2 = load_evaluation_dataset(V2_FIXTURE_PATH)

    assert v2.version == "ai-quality-v2"
    assert [case.id for case in v2.cases] == [case.id for case in v1.cases]
    actual_aliases: dict[tuple[str, int], set[str]] = {}
    for v1_case, v2_case in zip(v1.cases, v2.cases, strict=True):
        v1_payload = v1_case.model_dump(exclude={"expected_requirements"})
        v2_payload = v2_case.model_dump(exclude={"expected_requirements"})
        assert v2_payload == v1_payload
        assert len(v2_case.expected_requirements) == len(v1_case.expected_requirements)
        for index, (v1_expected, v2_expected) in enumerate(
            zip(v1_case.expected_requirements, v2_case.expected_requirements, strict=True)
        ):
            assert v2_expected.model_dump(exclude={"accepted_normalized_names"}) == (
                v1_expected.model_dump(exclude={"accepted_normalized_names"})
            )
            v1_names = set(v1_expected.accepted_normalized_names)
            v2_names = set(v2_expected.accepted_normalized_names)
            assert v1_names <= v2_names
            if additions := v2_names - v1_names:
                actual_aliases[(v1_case.id, index)] = additions

    assert actual_aliases == APPROVED_V2_ALIASES
    accepted_names = {
        name.casefold()
        for case in v2.cases
        for expected in case.expected_requirements
        for name in expected.accepted_normalized_names
    }
    forbidden_names = {
        name.casefold() for case in v2.cases for name in case.forbidden_normalized_names
    }
    assert accepted_names.isdisjoint(forbidden_names)


def test_dataset_rejects_duplicate_case_ids() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["cases"][1]["id"] = payload["cases"][0]["id"]

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        EvaluationDataset.model_validate(payload)


def test_dataset_rejects_expected_evidence_missing_from_original_text() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["cases"][0]["expected_requirements"][0]["source_text"] = "不存在的原文"

    with pytest.raises(ValidationError, match="expected evidence is not present"):
        EvaluationDataset.model_validate(payload)


def test_dataset_rejects_a_blank_accepted_normalized_name() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["cases"][0]["expected_requirements"][0]["accepted_normalized_names"] = [" "]

    with pytest.raises(ValidationError, match="at least 1 character"):
        EvaluationDataset.model_validate(payload)


def requirement(
    name: str,
    source: str = "熟练使用 SQL",
    requirement_type: RequirementType = RequirementType.CORE_COMPETENCY,
    explicitness: RequirementExplicitness = RequirementExplicitness.EXPLICIT,
) -> ExtractedRequirement:
    return ExtractedRequirement(
        source_text=source,
        normalized_name=name,
        requirement_type=requirement_type,
        explicitness=explicitness,
        confidence=0.9,
    )


def evaluation_case(
    *expected_names: list[str],
    forbidden_names: list[str] | None = None,
) -> EvaluationCase:
    return EvaluationCase(
        id="scoring-case",
        scenarios={"chinese"},
        company_name="示例公司",
        job_title="数据分析实习生",
        original_text="岗位要求：熟练使用 SQL。",
        expected_requirements=[
            ExpectedRequirement(
                source_text="熟练使用 SQL",
                accepted_normalized_names=names,
                requirement_type=RequirementType.CORE_COMPETENCY,
                explicitness=RequirementExplicitness.EXPLICIT,
            )
            for names in expected_names
        ],
        forbidden_normalized_names=forbidden_names or [],
    )


def test_scoring_matches_an_accepted_synonym_and_containing_evidence() -> None:
    case = evaluation_case(["SQL", "结构化查询语言"])

    score = score_case(case, [requirement("结构化查询语言", "岗位要求：熟练使用 SQL")])

    assert score.matched_count == 1
    assert score.traceable_prediction_count == 1
    assert score.correct_type_count == 1
    assert score.correct_explicitness_count == 1


def test_scoring_consumes_each_prediction_only_once() -> None:
    case = evaluation_case(["SQL"], ["SQL"])

    score = score_case(case, [requirement("SQL")])

    assert score.expected_count == 2
    assert score.matched_count == 1


def test_scoring_counts_untraceable_and_forbidden_predictions() -> None:
    case = evaluation_case(["SQL"], forbidden_names=["Kubernetes"])

    score = score_case(case, [requirement("Kubernetes", "原文没有该证据")])

    assert score.matched_count == 0
    assert score.traceable_prediction_count == 0
    assert score.forbidden_hit_count == 1


def test_dataset_scoring_applies_quality_thresholds() -> None:
    dataset = load_evaluation_dataset(FIXTURE_PATH)
    predictions = {
        case.id: CasePrediction(
            case_id=case.id,
            requirements=[
                requirement(
                    expected.accepted_normalized_names[0],
                    expected.source_text,
                    expected.requirement_type,
                    expected.explicitness,
                )
                for expected in case.expected_requirements
            ],
        )
        for case in dataset.cases
    }

    passing = score_dataset(dataset, predictions)
    failing = score_dataset(
        dataset,
        {
            case.id: CasePrediction(case_id=case.id, error_code="invalid_model_output")
            for case in dataset.cases
        },
        thresholds=QualityThresholds(),
    )

    assert passing.passed is True
    assert passing.metrics.precision == 1
    assert passing.metrics.recall == 1
    assert failing.passed is False
    assert "structural_success_rate" in failing.failed_thresholds
    assert failing.failed_case_ids == sorted(case.id for case in dataset.cases)
    assert set(failing.case_errors.values()) == {"invalid_model_output"}
    assert failing.case_differences["compound-skills-01"].expected_names == [
        "Python",
        "SQL",
        "数据分析项目经验",
    ]
    assert failing.case_differences["compound-skills-01"].predicted_names == []
