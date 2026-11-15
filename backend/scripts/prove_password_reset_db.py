"""Proof, against a REAL Postgres, of what the password-reset services rely on
and fakes cannot prove: the MAX(created_at) cooldown query, the cooldown end to
end, COALESCE on email_verified_at, "a weak password does not burn the link",
and that a failure after the claim rolls the WHOLE unit back (token, password,
sessions), after which the same link still works.

Refuses to run unless DATABASE_URL points at the scratch database, and deletes
its throwaway users (refresh_tokens has no ON DELETE CASCADE, so those rows go
first; email_tokens cascade).

Run:  cd backend && DATABASE_URL="$SCRATCH_URL" PYTHONPATH=. python scripts/prove_password_reset_db.py
"""

import asyncio
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

import app.services.password_reset as pr
from app.core.config import settings
from app.core.db import AsyncSessionLocal, engine
from app.core.security import verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.email_token import TokenPurpose
from app.services.auth import WeakPasswordError
from app.services.email_tokens import InvalidTokenError, issue_token, peek_token

if settings.database_url.rsplit("/", 1)[1] != "immersely_scratch":
    sys.exit("REFUSING TO RUN: DATABASE_URL is not the scratch database")

# Deterministic and offline: the breach lookup has its own unit tests.
settings.hibp_enabled = False

RESET = TokenPurpose.RESET_PASSWORD
VERIFY = TokenPurpose.VERIFY_EMAIL
STRONG = "zq7-quiet-Orchid-4821-xylophone-ruminate"
VERIFIED_AT = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
OLD_HASH = "x"

failures = 0
total = 0
created_user_ids: list[uuid.UUID] = []


def check(label: str, ok: bool) -> None:
    global failures, total
    total += 1
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        failures += 1


async def new_user(tag: str, verified_at=None) -> uuid.UUID:
    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"pr-{tag}-{suffix}@example.com",
            username=f"pr_{tag}_{suffix}",
            hashed_password=OLD_HASH,
            email_verified_at=verified_at,
        )
        db.add(user)
        await db.commit()
        created_user_ids.append(user.id)
        return user.id


async def get_user(user_id) -> User:
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(User).where(User.id == user_id))).scalar_one()


async def add_refresh_tokens(user_id, n: int = 2) -> None:
    async with AsyncSessionLocal() as db:
        for _ in range(n):
            db.add(
                RefreshToken(
                    user_id=user_id,
                    token_hash=uuid.uuid4().hex,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                )
            )
        await db.commit()


async def active_refresh_count(user_id) -> int:
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        )
        return len(rows.scalars().all())


async def issue(user_id, purpose=RESET) -> str:
    async with AsyncSessionLocal() as db:
        return await issue_token(db, user_id, purpose)


async def try_peek(raw):
    async with AsyncSessionLocal() as db:
        try:
            return await peek_token(db, raw, RESET)
        except InvalidTokenError:
            return None


async def last_issued(user_id):
    async with AsyncSessionLocal() as db:
        return await pr._last_reset_issued_at(db, user_id)


async def request(email):
    async with AsyncSessionLocal() as db:
        return await pr.request_password_reset(db, email)


async def do_reset(raw, password, now=None):
    async with AsyncSessionLocal() as db:
        return await pr.reset_password(db, raw, password, now=now)


def token_from(message) -> str:
    return re.search(r"#token=(\S+)", message.text_body).group(1)


async def proof_max_query():
    print("\n-- MAX(created_at) --")
    uid = await new_user("max")
    check("no tokens -> None", await last_issued(uid) is None)

    await issue(uid, RESET)
    l1 = await last_issued(uid)
    check("after one reset token -> a timestamp", l1 is not None)

    await issue(uid, VERIFY)
    check("a verify token does not move it", await last_issued(uid) == l1)

    raw_old = await issue(uid, RESET)  # supersedes the first one
    l2 = await last_issued(uid)
    check("a second reset token is newer (superseded rows still counted)",
          l2 is not None and l2 > l1)
    check("(sanity) the newest reset token peeks", await try_peek(raw_old) == uid)


async def proof_cooldown():
    print("\n-- cooldown end to end --")
    uid = await new_user("cool")
    email = (await get_user(uid)).email
    settings.reset_password_cooldown_s = 60

    m1 = await request(email)
    check("first request returns a message for the right address",
          m1 is not None and m1.to == email)
    raw1 = token_from(m1)
    check("its token is usable", await try_peek(raw1) == uid)

    check("immediate second request -> None (cooldown)", await request(email) is None)
    check("...and it did NOT supersede the first token", await try_peek(raw1) == uid)
    check("unknown email -> None",
          await request(f"nobody-{uuid.uuid4().hex[:8]}@example.com") is None)

    settings.reset_password_cooldown_s = 1
    await asyncio.sleep(1.3)
    m3 = await request(email)
    check("after the window a new message is issued", m3 is not None)
    raw3 = token_from(m3)
    check("the first token is now superseded", await try_peek(raw1) is None)
    check("the new token is usable", await try_peek(raw3) == uid)
    settings.reset_password_cooldown_s = 60


async def proof_full_reset_and_coalesce():
    print("\n-- full reset + COALESCE --")
    now = datetime.now(timezone.utc)
    uid_a = await new_user("coa", verified_at=VERIFIED_AT)
    uid_b = await new_user("cob", verified_at=None)
    for uid in (uid_a, uid_b):
        await add_refresh_tokens(uid, 2)
    raw_a, raw_b = await issue(uid_a), await issue(uid_b)

    notice_a = await do_reset(raw_a, STRONG, now=now)
    await do_reset(raw_b, STRONG, now=now)
    a, b = await get_user(uid_a), await get_user(uid_b)

    check("already-verified user keeps the ORIGINAL verification time",
          a.email_verified_at == VERIFIED_AT)
    check("unverified user gets verified at `now`", b.email_verified_at == now)
    check("user A's new hash verifies the new password",
          verify_password(STRONG, a.hashed_password))
    check("user B's new hash verifies the new password",
          verify_password(STRONG, b.hashed_password))
    check("user A's refresh tokens are all revoked", await active_refresh_count(uid_a) == 0)
    check("user B's refresh tokens are all revoked", await active_refresh_count(uid_b) == 0)
    try:
        await do_reset(raw_a, STRONG)
        reused = True
    except InvalidTokenError:
        reused = False
    check("the used link cannot be reused", reused is False)
    check("the notice goes to the right address and carries no link",
          notice_a.to == a.email and "http" not in notice_a.text_body)


async def proof_weak_password_keeps_token():
    print("\n-- weak password does not burn the link --")
    uid = await new_user("weak")
    raw = await issue(uid)
    try:
        await do_reset(raw, "short")
        raised = False
    except WeakPasswordError:
        raised = True
    check("a weak password is rejected", raised)
    check("the token is still usable", await try_peek(raw) == uid)
    check("the password hash is unchanged", (await get_user(uid)).hashed_password == OLD_HASH)


async def proof_rollback():
    print("\n-- failure after the claim rolls EVERYTHING back --")
    uid = await new_user("roll")
    await add_refresh_tokens(uid, 2)
    raw = await issue(uid)

    original = pr.revoke_user_refresh_tokens

    async def boom(*args, **kwargs):
        raise RuntimeError("simulated failure after the claim")

    pr.revoke_user_refresh_tokens = boom  # patched where it is used
    try:
        try:
            await do_reset(raw, STRONG)
            raised = False
        except RuntimeError:
            raised = True
    finally:
        pr.revoke_user_refresh_tokens = original

    user = await get_user(uid)
    check("the simulated failure propagates", raised)
    check("the token is usable again (the claim was rolled back)",
          await try_peek(raw) == uid)
    check("the password hash is unchanged", user.hashed_password == OLD_HASH)
    check("both refresh tokens are still active", await active_refresh_count(uid) == 2)
    check("email_verified_at is still NULL", user.email_verified_at is None)

    await do_reset(raw, STRONG)  # same link, real code path this time
    after = await get_user(uid)
    check("retrying with the SAME link now succeeds", await try_peek(raw) is None)
    check("...and the password really changed", verify_password(STRONG, after.hashed_password))


async def cleanup():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(created_user_ids)))
        await db.execute(delete(User).where(User.id.in_(created_user_ids)))
        await db.commit()


async def main():
    try:
        await proof_max_query()
        await proof_cooldown()
        await proof_full_reset_and_coalesce()
        await proof_weak_password_keeps_token()
        await proof_rollback()
    finally:
        await cleanup()
        await engine.dispose()
    print(f"\n{total - failures}/{total} checks passed, {failures} failed")
    sys.exit(1 if failures else 0)


asyncio.run(main())