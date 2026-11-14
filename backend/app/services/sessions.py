"""Revoking refresh tokens (sessions).

Used by password reset, change-password and "logout everywhere". Access tokens
are stateless JWTs and cannot be revoked: revoking the refresh tokens only
stops them being renewed, so a stolen access token still works until its
(30 minute) expiry. A known limit, not a bug.
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
    except_token_hash: str | None = None,
) -> int:
    """Revoke every still-active refresh token of a user; return how many.

    WHERE revoked_at IS NULL: tokens revoked earlier keep their ORIGINAL
    timestamp (the audit trail), and calling this twice revokes nothing the
    second time. With commit=False the caller owns the transaction.

    except_token_hash spares one token (the caller's own session). The query
    is always filtered by user_id, so a hash belonging to another user spares
    nothing here: the safe outcome is that all of this user's tokens go.
    """
    now = now or datetime.now(timezone.utc)
    conditions = [
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ]
    if except_token_hash is not None:
        conditions.append(RefreshToken.token_hash != except_token_hash)

    result = await db.execute(
        update(RefreshToken)
        .where(*conditions)
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )
    if commit:
        await db.commit()
    return result.rowcount


async def revoke_refresh_token(
    db: AsyncSession,
    token_hash: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Revoke the single active refresh token with this hash; True if one was.

    Possession of the raw token is the proof of ownership, so there is no
    user id to check. Unknown or already-revoked tokens return False and
    keep their original revoked_at.
    """
    now = now or datetime.now(timezone.utc)
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return result.rowcount > 0