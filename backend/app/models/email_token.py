import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.schemas.email_token import TokenPurpose

# Built from the enum so the CHECK can never drift from the code's vocabulary.
_PURPOSES_SQL = ", ".join(f"'{p.value}'" for p in TokenPurpose)


class EmailToken(Base):
    """Single-use, expiring token sent by email (verify address, reset password).

    Only the SHA-256 of the token is stored. `used_at` NULL = still unused.
    """

    __tablename__ = "email_tokens"
    __table_args__ = (
        CheckConstraint(
            f"purpose IN ({_PURPOSES_SQL})", name="ck_email_tokens_purpose"
        ),
        Index("ix_email_tokens_user_purpose", "user_id", "purpose"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )