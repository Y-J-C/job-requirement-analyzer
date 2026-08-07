import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.target_role import utc_now


class RequirementType(StrEnum):
    ELIGIBILITY = "eligibility"
    CORE_COMPETENCY = "core_competency"
    EXPERIENCE = "experience"
    PREFERRED = "preferred"
    UNCERTAIN = "uncertain"


class RequirementExplicitness(StrEnum):
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    UNCERTAIN = "uncertain"


class RequirementItem(Base):
    __tablename__ = "requirement_items"
    __table_args__ = (
        CheckConstraint(
            "requirement_type IN ('eligibility', 'core_competency', 'experience', "
            "'preferred', 'uncertain')",
            name="requirement_item_type",
        ),
        CheckConstraint(
            "explicitness IN ('explicit', 'implicit', 'uncertain')",
            name="requirement_item_explicitness",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="requirement_item_confidence_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        index=True,
    )
    original_text: Mapped[str] = mapped_column(Text)
    normalized_name: Mapped[str] = mapped_column(String(200))
    requirement_type: Mapped[RequirementType] = mapped_column(
        SqlEnum(
            RequirementType,
            name="requirement_item_type",
            native_enum=False,
            length=32,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        )
    )
    explicitness: Mapped[RequirementExplicitness] = mapped_column(
        SqlEnum(
            RequirementExplicitness,
            name="requirement_item_explicitness",
            native_enum=False,
            length=16,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        )
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    user_modified: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
