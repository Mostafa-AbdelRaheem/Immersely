"""Email verification: send the link, and consume it.

send_verification_email does NOT swallow EmailSendError: whether a failed send
aborts (resend) or is tolerated (registration) is the route's decision.
verify_email runs two commits (consume the token, then mark the user): if the
second fails the token is burned but the user stays unverified and simply
requests a resend. Acceptable here; password reset must NOT work this way.
"""

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.schemas.email_token import TokenPurpose
from app.services.email_messages import build_link, verification_message
from app.services.email_sender import EmailSender
from app.services.email_tokens import consume_token, issue_token

# Contract with the frontend router (the page that reads #token=... and POSTs
# it back). Changes together with frontend code, never per environment.
VERIFY_EMAIL_PATH = "verify-email"


class EmailAlreadyVerifiedError(Exception):
    pass


async def send_verification_email(
    db: AsyncSession,
    sender: EmailSender,
    user: User,
    *,
    now: datetime | None = None,
) -> None:
    if user.email_verified_at is not None:
        raise EmailAlreadyVerifiedError("Email is already verified")

    raw = await issue_token(db, user.id, TokenPurpose.VERIFY_EMAIL, now=now)
    link = build_link(settings.frontend_base_url, VERIFY_EMAIL_PATH, raw)
    await sender.send(
        verification_message(
            to=user.email,
            name=user.name,
            link=link,
            valid_for_minutes=settings.verify_email_token_ttl_minutes,
        )
    )


async def verify_email(
    db: AsyncSession, raw_token: str, *, now: datetime | None = None
) -> None:
    """Consume a verification token and mark its user verified.

    Raises InvalidTokenError (from email_tokens) for any bad token.
    """
    now = now or datetime.now(timezone.utc)
    user_id = await consume_token(db, raw_token, TokenPurpose.VERIFY_EMAIL, now=now)
    # IS NULL: a repeat never overwrites the original verification time.
    await db.execute(
        update(User)
        .where(User.id == user_id, User.email_verified_at.is_(None))
        .values(email_verified_at=now)
        .execution_options(synchronize_session=False)
    )
    await db.commit()