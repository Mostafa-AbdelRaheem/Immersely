"""Password reset: request a link, then use it.

request_password_reset does NOT send the email. It returns the prebuilt
message (or None) and the route sends it after the response, so neither the
mail server's latency nor an open DB session can reveal whether the account
exists. None covers "no such account" and "cooldown active": the caller must
treat both exactly the same.

Known limit: the "account exists" path does more DB work (an extra query and
a commit) than the "no account" path, so a patient attacker could still
measure a small difference. Closing it needs dummy work on the miss path
(parked, with the login-timing item).

reset_password is ONE transaction: claim the token, change the password,
mark the email verified, revoke every refresh token, commit. Any failure
rolls everything back, so the link is never burned without the password
changing.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.email_token import EmailToken
from app.models.user import User
from app.schemas.email_token import TokenPurpose
from app.services.auth import validate_new_password
from app.services.email_messages import (
    build_link,
    password_changed_message,
    password_reset_message,
)
from app.services.email_sender import EmailMessage
from app.services.email_tokens import (
    InvalidTokenError,
    consume_token,
    issue_token,
    peek_token,
)
from app.services.sessions import revoke_user_refresh_tokens
from app.services.token_logic import is_in_cooldown

# Contract with the frontend router (the page that reads #token=... and POSTs
# the new password). Changes together with frontend code, never per environment.
RESET_PASSWORD_PATH = "reset-password"


async def _find_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def _load_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
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


async def reset_password(
    db: AsyncSession,
    raw_token: str,
    new_password: str,
    *,
    now: datetime | None = None,
) -> EmailMessage:
    """Set a new password using a reset token; return the "changed" notice.

    Raises InvalidTokenError (bad/expired/used token) or WeakPasswordError
    (the token is NOT burned in that case). The route sends the notice.
    """
    now = now or datetime.now(timezone.utc)

    # Read-only checks first: a weak password must not burn the link.
    user_id = await peek_token(db, raw_token, TokenPurpose.RESET_PASSWORD, now=now)
    user = await _load_user_by_id(db, user_id)
    if user is None:
        raise InvalidTokenError("Invalid or expired token")
    to, name = user.email, user.name

    password = await validate_new_password(new_password, email=to)
    # Hash BEFORE claiming: bcrypt is slow and the claim holds a row lock.
    new_hash = hash_password(password)

    try:
        claimed_user_id = await consume_token(
            db, raw_token, TokenPurpose.RESET_PASSWORD, commit=False, now=now
        )
        if claimed_user_id != user.id:
            raise InvalidTokenError("Invalid or expired token")
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                hashed_password=new_hash,
                email_verified_at=func.coalesce(User.email_verified_at, now),
            )
            .execution_options(synchronize_session=False)
        )
        await revoke_user_refresh_tokens(db, user.id, now=now, commit=False)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return password_changed_message(to=to, name=name)