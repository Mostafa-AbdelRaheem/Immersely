import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    # Mirrors the migration c3a9f1d27e40. Both values are stored in one
    # canonical lowercase form; the database refuses anything else.
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        CheckConstraint(
            "username = lower(username)", name="ck_users_username_lowercase"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # Free-form display name; NULL for accounts that predate N5.
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    # Unique handle, always lowercase (see username_policy.py).
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # NULL = email not verified yet.
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )