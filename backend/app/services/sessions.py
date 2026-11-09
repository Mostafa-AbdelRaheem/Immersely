"""Revoking refresh tokens (sessions).

Used by password reset now, and by "logout everywhere" later. Access tokens are
stateless JWTs and cannot be revoked: revoking the refresh tokens only stops
them being renewed, so a stolen access token still works until its (30 minute)
expiry. A known limit, not a bug.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


async def revoke_user_refresh_tokens(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    now: datetime | None = None,
    commit: bool = True,
) -> int:
    """Revoke every still-active refresh token of a user; return how many.

    WHERE revoked_at IS NULL: tokens revoked earlier keep their ORIGINAL
    timestamp (the audit trail), and calling this twice revokes nothing the
    second time. With commit=False the caller owns the transaction.
    """
    now = now or datetime.now(timezone.utc)
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )
    if commit:
        await db.commit()
    return result.rowcount