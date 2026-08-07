import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RecruitmentStage(StrEnum):
    DAILY_INTERNSHIP = "daily_internship"
    SUMMER_INTERNSHIP = "summer_internship"
    WINTER_INTERNSHIP = "winter_internship"
    AUTUMN_RECRUITMENT = "autumn_recruitment"
    SPRING_RECRUITMENT = "spring_recruitment"
    OTHER = "other"


def utc_now() -> datetime:
    return datetime.now(UTC)


class TargetRole(Base):
    __tablename__ = "target_roles"
    __table_args__ = (
        CheckConstraint(
            "recruitment_stage IN ('daily_internship', 'summer_internship', "
            "'winter_internship', 'autumn_recruitment', 'spring_recruitment', 'other')",
            name="target_role_recruitment_stage",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    recruitment_stage: Mapped[RecruitmentStage] = mapped_column(
        SqlEnum(
            RecruitmentStage,
            name="target_role_recruitment_stage",
            native_enum=False,
            length=32,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        )
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
