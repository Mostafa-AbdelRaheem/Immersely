"""Password reset, step 1: request a link.

request_password_reset does NOT send the email. It returns the prebuilt
message (or None) and the route sends it after the response, so neither the
mail server's latency nor an open DB session can reveal whether the account
exists. None covers "no such account" and "cooldown active": the caller must
treat both exactly the same.

Known limit: the "account exists" path does more DB work (an extra query and
a commit) than the "no account" path, so a patient attacker could still
measure a small difference. Closing it needs dummy work on the miss path
(parked, with the login-timing item).
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.email_token import EmailToken
from app.models.user import User
from app.schemas.email_token import TokenPurpose
from app.services.email_messages import build_link, password_reset_message
from app.services.email_sender import EmailMessage
from app.services.email_tokens import issue_token
from app.services.token_logic import is_in_cooldown

# Contract with the frontend router (the page that reads #token=... and POSTs
# the new password). Changes together with frontend code, never per environment.
RESET_PASSWORD_PATH = "reset-password"


async def _find_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def _last_reset_issued_at(
    db: AsyncSession, user_id: uuid.UUID
) -> datetime | None:
    """Newest reset token's created_at, used or not (supersede keeps the rows)."""
    result = await db.execute(
        select(func.max(EmailToken.created_at)).where(
            EmailToken.user_id == user_id,
            EmailToken.purpose == TokenPurpose.RESET_PASSWORD.value,
        )
    )
    return result.scalar_one()  # MAX over zero rows is one row holding NULL


async def request_password_reset(
    db: AsyncSession, email: str, *, now: datetime | None = None
) -> EmailMessage | None:
    now = now or datetime.now(timezone.utc)

    user = await _find_user_by_email(db, email)
    if user is None:
        return None

    last = await _last_reset_issued_at(db, user.id)
    if is_in_cooldown(
        last_issued_at=last,
        now=now,
        cooldown=timedelta(seconds=settings.reset_password_cooldown_s),
    ):
        return None

    raw = await issue_token(db, user.id, TokenPurpose.RESET_PASSWORD, now=now)
    link = build_link(settings.frontend_base_url, RESET_PASSWORD_PATH, raw)
    return password_reset_message(
        to=user.email,
        name=user.name,
        link=link,
        valid_for_minutes=settings.reset_password_token_ttl_minutes,
    )