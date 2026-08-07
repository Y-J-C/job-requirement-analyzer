import uuid
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis_run import AnalysisRun
from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.requirement_item import (
    RequirementExplicitness,
    RequirementItem,
    RequirementType,
)
from app.schemas.summary import (
    RequirementSummaryItemResponse,
    SummaryEvidenceResponse,
    TargetRoleSummaryResponse,
)


@dataclass
class SummaryAccumulator:
    job_ids: set[uuid.UUID] = field(default_factory=set)
    evidence: list[tuple[RequirementItem, JobPosting]] = field(default_factory=list)


def sample_size_notice(confirmed_job_count: int) -> str:
    if confirmed_job_count < 5:
        return "样本量很小，仅供查看录入结果。"
    if confirmed_job_count < 15:
        return "可观察初步方向，不宜代表整体市场。"
    return "样本仍受来源、时间和岗位方向影响，请结合证据审慎解读。"


def calculate_coverage_rate(
    mentioning_job_count: int,
    confirmed_job_count: int,
) -> float:
    if confirmed_job_count == 0:
        return 0
    rate = Decimal(mentioning_job_count) / Decimal(confirmed_job_count)
    return float(rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def build_target_role_summary(
    session: Session,
    *,
    target_role_id: uuid.UUID,
    target_role_name: str,
    requirement_type: RequirementType | None,
) -> TargetRoleSummaryResponse:
    job_condition = JobPosting.target_role_id == target_role_id
    sample_job_count = (
        session.scalar(select(func.count()).select_from(JobPosting).where(job_condition)) or 0
    )
    confirmed_job_count = (
        session.scalar(
            select(func.count())
            .select_from(JobPosting)
            .where(job_condition, JobPosting.status == JobPostingStatus.CONFIRMED)
        )
        or 0
    )

    evidence_query = (
        select(RequirementItem, JobPosting)
        .join(AnalysisRun, AnalysisRun.id == RequirementItem.analysis_run_id)
        .join(JobPosting, JobPosting.id == AnalysisRun.job_posting_id)
        .where(
            JobPosting.target_role_id == target_role_id,
            JobPosting.status == JobPostingStatus.CONFIRMED,
            RequirementItem.user_confirmed.is_(True),
        )
    )
    if requirement_type is not None:
        evidence_query = evidence_query.where(
            RequirementItem.requirement_type == requirement_type
        )

    groups: dict[tuple[str, RequirementType], SummaryAccumulator] = {}
    for requirement, job in session.execute(evidence_query):
        key = (requirement.normalized_name, requirement.requirement_type)
        accumulator = groups.setdefault(key, SummaryAccumulator())
        accumulator.job_ids.add(job.id)
        accumulator.evidence.append((requirement, job))

    items: list[RequirementSummaryItemResponse] = []
    for (normalized_name, item_type), accumulator in groups.items():
        sorted_evidence = sorted(
            accumulator.evidence,
            key=lambda row: (
                row[1].company_name,
                row[1].job_title,
                row[0].created_at,
                str(row[0].id),
            ),
        )
        mentioning_job_count = len(accumulator.job_ids)
        items.append(
            RequirementSummaryItemResponse(
                normalized_name=normalized_name,
                requirement_type=item_type,
                mentioning_job_count=mentioning_job_count,
                confirmed_job_count=confirmed_job_count,
                coverage_rate=calculate_coverage_rate(
                    mentioning_job_count,
                    confirmed_job_count,
                ),
                evidence_count=len(sorted_evidence),
                explicit_evidence_count=sum(
                    requirement.explicitness == RequirementExplicitness.EXPLICIT
                    for requirement, _job in sorted_evidence
                ),
                evidence=[
                    SummaryEvidenceResponse(
                        requirement_id=requirement.id,
                        job_id=job.id,
                        company_name=job.company_name,
                        job_title=job.job_title,
                        original_text=requirement.original_text,
                        explicitness=requirement.explicitness,
                    )
                    for requirement, job in sorted_evidence
                ],
            )
        )

    items.sort(
        key=lambda item: (
            -item.coverage_rate,
            -item.mentioning_job_count,
            item.normalized_name,
            item.requirement_type.value,
        )
    )
    return TargetRoleSummaryResponse(
        target_role_id=target_role_id,
        target_role_name=target_role_name,
        sample_job_count=sample_job_count,
        confirmed_job_count=confirmed_job_count,
        sample_size_notice=sample_size_notice(confirmed_job_count),
        items=items,
    )
