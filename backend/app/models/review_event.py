# app/models/review_event.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReviewEvent(Base):
    __tablename__ = "review_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    sentence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sentences.id", ondelete="CASCADE"),
        nullable=False,
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )

    mode: Mapped[str] = mapped_column(Text, nullable=False)
    user_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    tier: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_practiced: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    grade: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default="now()",
    )

    __table_args__ = (
        CheckConstraint(
            "mode in ('isolated','cloze_in_scene','free_production','flip')",
            name="ck_review_events_mode_valid",
        ),
        CheckConstraint(
            "tier in ('correct','almost_correct','incorrect')",
            name="ck_review_events_tier_valid",
        ),
        CheckConstraint(
            "grade in ('again','hard','good','easy')",
            name="ck_review_events_grade_valid",
        ),
        Index("ix_review_events_user_created", "user_id", "created_at"),
    )