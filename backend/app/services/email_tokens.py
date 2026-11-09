"""Issue and consume single-use email tokens (verify email, reset password).

Only the SHA-256 of a token is stored. `used_at` means "no longer usable": it
is set when a token is consumed OR superseded by a newer one for the same user
and purpose (OWASP: only the latest link should work).
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_token
from app.models.email_token import EmailToken
from app.schemas.email_token import TokenPurpose
from app.services.token_logic import compute_expiry, generate_token


class InvalidTokenError(Exception):
    """Unknown, expired, already used, or issued for a different purpose.

    One exception for all four on purpose: telling them apart would let a
    caller probe which tokens exist.
    """


def _ttl(purpose: TokenPurpose) -> timedelta:
    if purpose is TokenPurpose.VERIFY_EMAIL:
        return timedelta(minutes=settings.verify_email_token_ttl_minutes)
    if purpose is TokenPurpose.RESET_PASSWORD:
        return timedelta(minutes=settings.reset_password_token_ttl_minutes)
    raise ValueError(f"No lifetime configured for {purpose!r}")


async def issue_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    purpose: TokenPurpose,
    *,
    now: datetime | None = None,
) -> str:
    """Create a token for (user, purpose) and return the RAW value.

    The raw token exists only in this return value (it goes into the email
    link); only its hash is stored. Older unused tokens for the same user and
    purpose are superseded in the same transaction, so only the newest works.
    """
    now = now or datetime.now(timezone.utc)
    raw, token_hash = generate_token()

    await db.execute(
        update(EmailToken)
        .where(
            EmailToken.user_id == user_id,
            EmailToken.purpose == purpose.value,
            EmailToken.used_at.is_(None),
        )
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    )
    db.add(
        EmailToken(
            user_id=user_id,
            purpose=purpose.value,
            token_hash=token_hash,
            expires_at=compute_expiry(now, _ttl(purpose)),
        )
    )
    await db.commit()
    return raw


async def consume_token(
    db: AsyncSession,
    raw_token: str,
    purpose: TokenPurpose,
    *,
    now: datetime | None = None,
) -> uuid.UUID:
    """Atomically use a token once and return its user_id.

    One UPDATE ... RETURNING does the check and the mark together, so two
    simultaneous requests cannot both succeed: the second finds used_at already
    set. The rule (unused AND expires_at > now) matches token_logic.is_usable.
    `now` is the app's clock for issuing and consuming alike (no app/DB skew).
    """
    now = now or datetime.now(timezone.utc)
    result = await db.execute(
        update(EmailToken)
        .where(
            EmailToken.token_hash == hash_token(raw_token),
            EmailToken.purpose == purpose.value,
            EmailToken.used_at.is_(None),
            EmailToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(EmailToken.user_id)
        .execution_options(synchronize_session=False)
    )
    user_id = result.scalar_one_or_none()
    if user_id is None:
        raise InvalidTokenError("Invalid or expired token")
    await db.commit()
    return user_id