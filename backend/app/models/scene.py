# app/models/scene.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Text, DateTime, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)

    sentence_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )
    padding_sentence_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default="{}"
    )

    text_de: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    line_sentence_map: Mapped[dict] = mapped_column(JSONB, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default="now()",
    )
    review_count_since_generated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    model: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_scenes_user_topic_generated", "user_id", "topic", "generated_at"),
    )