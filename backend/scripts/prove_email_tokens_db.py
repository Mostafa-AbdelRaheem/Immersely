"""Proof, against a REAL Postgres, of the email-token guarantees FakeDB tests
cannot show: single use, wrong-purpose rejection, the exact expiry boundary,
superseding, and exactly one winner under concurrency.

Refuses to run unless DATABASE_URL points at the scratch database, and deletes
its own throwaway user (tokens cascade) at the end.

Run:  cd backend && DATABASE_URL="$SCRATCH_URL" PYTHONPATH=. python scripts/prove_email_tokens_db.py
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.db import AsyncSessionLocal, engine
from app.core.security import hash_token
from app.models.email_token import EmailToken
from app.models.user import User
from app.schemas.email_token import TokenPurpose
from app.services.email_tokens import InvalidTokenError, consume_token, issue_token

if settings.database_url.rsplit("/", 1)[1] != "immersely_scratch":
    sys.exit("REFUSING TO RUN: DATABASE_URL is not the scratch database")

RACERS = 12  # below SQLAlchemy's default pool (5 + 10 overflow) so they really overlap
failures = 0


def check(label: str, ok: bool) -> None:
    global failures
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        failures += 1


async def issue(user_id, purpose=TokenPurpose.VERIFY_EMAIL, now=None) -> str:
    async with AsyncSessionLocal() as db:
        return await issue_token(db, user_id, purpose, now=now)


async def try_consume(raw, purpose=TokenPurpose.VERIFY_EMAIL, now=None):
    """Own session per call, like a real request. Returns the user id, or None."""
    async with AsyncSessionLocal() as db:
        try:
            return await consume_token(db, raw, purpose, now=now)
        except InvalidTokenError:
            return None


async def naive_consume(raw):
    """DEMO ONLY: the tempting SELECT-then-UPDATE, with a pause to widen the window."""
    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(
                select(EmailToken).where(
                    EmailToken.token_hash == hash_token(raw),
                    EmailToken.used_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        await asyncio.sleep(0.05)
        row.used_at = datetime.now(timezone.utc)
        await db.commit()
        return row.user_id


async def count_tokens(**conditions) -> int:
    async with AsyncSessionLocal() as db:
        stmt = select(func.count()).select_from(EmailToken)
        for column, value in conditions.items():
            stmt = stmt.where(getattr(EmailToken, column) == value)
        return (await db.execute(stmt)).scalar_one()


async def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"tokenproof-{suffix}@example.com",
            username=f"tp_{suffix}",
            hashed_password="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id

    try:
        # 1. Single use.
        raw = await issue(user_id)
        check("a fresh token consumes and returns the user id", await try_consume(raw) == user_id)
        check("the same token cannot be consumed twice", await try_consume(raw) is None)

        # 2. Purpose separation, and a failed attempt must not burn the token.
        raw = await issue(user_id)
        check(
            "a verify token is rejected as a reset token",
            await try_consume(raw, TokenPurpose.RESET_PASSWORD) is None,
        )
        check("...and that failed attempt did not burn it", await try_consume(raw) == user_id)

        # 3. Unknown token.
        check("an unknown token is rejected", await try_consume("not-a-real-token") is None)

        # 4. Exact expiry boundary (the app clock is injected, so no sleeping).
        t0 = datetime.now(timezone.utc)
        ttl = timedelta(minutes=settings.verify_email_token_ttl_minutes)
        raw = await issue(user_id, now=t0)
        check("rejected at the exact expiry instant", await try_consume(raw, now=t0 + ttl) is None)
        check(
            "...and one microsecond earlier it still works",
            await try_consume(raw, now=t0 + ttl - timedelta(microseconds=1)) == user_id,
        )

        # 5. A newer token supersedes the older one.
        first = await issue(user_id)
        second = await issue(user_id)
        check("issuing a newer token supersedes the older one", await try_consume(first) is None)
        check("...and the newer token works", await try_consume(second) == user_id)

        # 6. Concurrency: exactly one winner.
        raw = await issue(user_id)
        results = await asyncio.gather(*[try_consume(raw) for _ in range(RACERS)])
        winners = [r for r in results if r is not None]
        check(
            f"{RACERS} simultaneous consumes -> exactly one winner (got {len(winners)})",
            len(winners) == 1 and winners[0] == user_id,
        )

        # 6b. DEMO, not a check: the naive version with the same racers.
        raw = await issue(user_id)
        naive = await asyncio.gather(*[naive_consume(raw) for _ in range(RACERS)])
        print(f"DEMO  naive SELECT-then-UPDATE with {RACERS} racers -> winners = "
              f"{len([r for r in naive if r is not None])} (the safe version gave 1)")

        # 7. The raw token is never stored; only its hash is.
        raw = await issue(user_id)
        check("the raw token is not in the table", await count_tokens(token_hash=raw) == 0)
        check("its SHA-256 is", await count_tokens(token_hash=hash_token(raw)) == 1)
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
        check(
            "cleanup: deleting the throwaway user cascaded its tokens",
            await count_tokens(user_id=user_id) == 0,
        )
        await engine.dispose()


asyncio.run(main())
print("\nALL CHECKS PASSED" if failures == 0 else f"\n{failures} CHECK(S) FAILED")
sys.exit(1 if failures else 0)