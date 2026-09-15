# app/models/sentence.py
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Text, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Float, CheckConstraint, Index

from app.models.base import Base


class Sentence(Base):
    __tablename__ = "sentences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    de: Mapped[str] = mapped_column(Text, nullable=False)
    en: Mapped[str] = mapped_column(Text, nullable=False)
    topics: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )
    grammar_tag: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    srs_due: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default="now()",
    )
    srs_interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    srs_ease: Mapped[float] = mapped_column(Float, nullable=False, default=2.5, server_default="2.5")
    srs_reps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    srs_lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    srs_state: Mapped[str] = mapped_column(Text, nullable=False, default="new", server_default="new")

    __table_args__ = (
        CheckConstraint(
            "srs_state in ('new','learning','review','relearning')",
            name="ck_sentences_srs_state_valid",
        ),
        Index("ix_sentences_user_id_srs_due", "user_id", "srs_due"),
    )