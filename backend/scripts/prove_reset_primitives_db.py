"""Proof, against a REAL Postgres, of the primitives password reset is built on:
peek (read-only), consume with commit=False (rollback undoes the claim, a
concurrent consumer blocks on the locked row), and session revocation.

Refuses to run unless DATABASE_URL points at the scratch database, and deletes
its throwaway users. refresh_tokens has no ON DELETE CASCADE (a known gap), so
cleanup deletes those rows explicitly first.

Run:  cd backend && DATABASE_URL="$SCRATCH_URL" PYTHONPATH=. python scripts/prove_reset_primitives_db.py
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.db import AsyncSessionLocal, engine
from app.models.email_token import EmailToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.email_token import TokenPurpose
from app.services.email_tokens import (
    InvalidTokenError,
    consume_token,
    issue_token,
    peek_token,
)
from app.services.sessions import revoke_user_refresh_tokens

if settings.database_url.rsplit("/", 1)[1] != "immersely_scratch":
    sys.exit("REFUSING TO RUN: DATABASE_URL is not the scratch database")

RESET = TokenPurpose.RESET_PASSWORD
VERIFY = TokenPurpose.VERIFY_EMAIL
failures = 0


def check(label: str, ok: bool) -> None:
    global failures
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        failures += 1


async def new_user(tag: str):
    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"reset-{tag}-{suffix}@example.com",
            username=f"rs_{tag}_{suffix}",
            hashed_password="x",
        )
        db.add(user)
        await db.commit()
        return user.id


async def issue(user_id, purpose=RESET, now=None) -> str:
    async with AsyncSessionLocal() as db:
        return await issue_token(db, user_id, purpose, now=now)


async def try_peek(raw, purpose=RESET, now=None):
    async with AsyncSessionLocal() as db:
        try:
            return await peek_token(db, raw, purpose, now=now)
        except InvalidTokenError:
            return None


async def try_consume(raw, purpose=RESET, now=None):
    async with AsyncSessionLocal() as db:
        try:
            return await consume_token(db, raw, purpose, now=now)
        except InvalidTokenError:
            return None


async def contention(user_id, holder_finish: str):
    """A holder claims a token WITHOUT committing; a second consumer tries too."""
    raw = await issue(user_id)
    async with AsyncSessionLocal() as holder:
        await consume_token(holder, raw, RESET, commit=False)  # row locked, uncommitted
        waiter = asyncio.create_task(try_consume(raw))
        await asyncio.sleep(0.5)
        blocked = not waiter.done()
        peek_during = await try_peek(raw)  # a plain SELECT is not blocked
        if holder_finish == "commit":
            await holder.commit()
        else:
            await holder.rollback()
        result = await waiter
    return blocked, peek_during, result


async def add_refresh(user_id, revoked_at=None) -> None:
    async with AsyncSessionLocal() as db:
        db.add(
            RefreshToken(
                user_id=user_id,
                token_hash=uuid.uuid4().hex,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                revoked_at=revoked_at,
            )
        )
        await db.commit()


async def counts(user_id) -> tuple[int, int]:
    """(total, revoked) refresh tokens of a user."""
    async with AsyncSessionLocal() as db:
        total = (
            await db.execute(
                select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == user_id)
            )
        ).scalar_one()
        revoked = (
            await db.execute(
                select(func.count())
                .select_from(RefreshToken)
                .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_not(None))
            )
        ).scalar_one()
        return total, revoked


async def earliest_revoked_at(user_id):
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(
                select(func.min(RefreshToken.revoked_at)).where(RefreshToken.user_id == user_id)
            )
        ).scalar_one()


async def main() -> None:
    a = await new_user("a")
    b = await new_user("b")
    ids = [a, b]
    try:
        # --- peek: read-only, same rules as consume ---
        raw = await issue(a)
        check("peek returns the token's user id", await try_peek(raw) == a)
        check(
            "peeking twice changes nothing (the token still consumes once)",
            await try_peek(raw) == a and await try_consume(raw) == a,
        )
        check("a consumed token is no longer peekable", await try_peek(raw) is None)
        check("peek rejects an unknown token", await try_peek("not-a-real-token") is None)

        raw = await issue(a)
        check("peek rejects a token of another purpose", await try_peek(raw, VERIFY) is None)

        t0 = datetime.now(timezone.utc)
        ttl = timedelta(minutes=settings.reset_password_token_ttl_minutes)
        raw = await issue(a, now=t0)
        check("peek rejects at the exact expiry instant", await try_peek(raw, now=t0 + ttl) is None)
        check(
            "...and one microsecond earlier it still works",
            await try_peek(raw, now=t0 + ttl - timedelta(microseconds=1)) == a,
        )

        # --- commit=False: the claim lives in the caller's transaction ---
        raw = await issue(a)
        async with AsyncSessionLocal() as db:
            claimed = await consume_token(db, raw, RESET, commit=False)
            await db.rollback()
        check(
            "commit=False then rollback: the claim is undone (token still usable)",
            claimed == a and await try_peek(raw) == a,
        )
        check("...and it can still be consumed afterwards", await try_consume(raw) == a)

        raw = await issue(a)
        async with AsyncSessionLocal() as db:
            await consume_token(db, raw, RESET, commit=False)
            await db.commit()
        check("commit=False then commit: the token is burned", await try_peek(raw) is None)

        # --- contention on an uncommitted claim ---
        blocked, peek_during, result = await contention(a, "commit")
        check("a peek DURING an uncommitted claim still sees the token (peek is advisory)", peek_during == a)
        check("a concurrent consumer BLOCKS while the claim is uncommitted", blocked)
        check("...and loses once the holder commits", result is None)

        blocked, _, result = await contention(a, "rollback")
        check("a concurrent consumer blocks again while uncommitted", blocked)
        check("...and wins once the holder rolls back", result == a)

        # --- revoking refresh tokens ---
        old = datetime(2026, 1, 1, tzinfo=timezone.utc)
        await add_refresh(a)
        await add_refresh(a)
        await add_refresh(a, revoked_at=old)
        await add_refresh(b)
        async with AsyncSessionLocal() as db:
            n = await revoke_user_refresh_tokens(db, a)
        check(f"revoke returns how many were newly revoked (expected 2, got {n})", n == 2)
        check("all of the user's tokens are now revoked", await counts(a) == (3, 3))
        check(
            "a token revoked earlier keeps its ORIGINAL timestamp (audit trail)",
            await earliest_revoked_at(a) == old,
        )
        check("another user's token is untouched", await counts(b) == (1, 0))
        async with AsyncSessionLocal() as db:
            n = await revoke_user_refresh_tokens(db, a)
        check("a second call revokes nothing (idempotent)", n == 0)

        await add_refresh(a)
        await add_refresh(a)
        async with AsyncSessionLocal() as db:
            n = await revoke_user_refresh_tokens(db, a, commit=False)
            await db.rollback()
        check(
            "commit=False then rollback: nothing is revoked",
            n == 2 and await counts(a) == (5, 3),
        )
        async with AsyncSessionLocal() as db:
            await revoke_user_refresh_tokens(db, a, commit=False)
            await db.commit()
        check("commit=False then commit: they are revoked", await counts(a) == (5, 5))
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(ids)))
            await db.execute(delete(User).where(User.id.in_(ids)))  # email_tokens cascade
            await db.commit()
        async with AsyncSessionLocal() as db:
            left = 0
            for stmt in (
                select(func.count()).select_from(User).where(User.id.in_(ids)),
                select(func.count()).select_from(EmailToken).where(EmailToken.user_id.in_(ids)),
                select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id.in_(ids)),
            ):
                left += (await db.execute(stmt)).scalar_one()
        check("cleanup: no throwaway users or tokens remain", left == 0)
        await engine.dispose()


asyncio.run(main())
print("\nALL CHECKS PASSED" if failures == 0 else f"\n{failures} CHECK(S) FAILED")
sys.exit(1 if failures else 0)