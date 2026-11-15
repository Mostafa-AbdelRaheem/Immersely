"""Pure rules for single-use email tokens (verify email, reset password).

No DB and no clock: callers pass `now` and the TTL in. The raw token only
ever travels in an email link; the database stores only its SHA-256, so a
leaked table cannot be replayed. SHA-256 (not bcrypt) is enough because the
token is 256 random bits, and it lets us look a row up BY its hash.
"""

import secrets
from datetime import datetime, timedelta

from app.core.security import hash_token


def generate_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). Only the hash is ever stored."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def compute_expiry(now: datetime, ttl: timedelta) -> datetime:
    return now + ttl


def is_usable(*, expires_at: datetime, used_at: datetime | None, now: datetime) -> bool:
    """A token works only if it is unused AND strictly before its expiry.

    The expiry instant itself counts as expired (the SQL later uses
    `expires_at > now()` to match). Naive vs aware datetimes raise TypeError
    on purpose rather than being silently compared.
    """
    return used_at is None and now < expires_at

def is_in_cooldown(
    *, last_issued_at: datetime | None, now: datetime, cooldown: timedelta
) -> bool:
    """True while a new token must NOT be issued for this user and purpose.

    No previous token means no cooldown. Exactly `cooldown` after the last
    token counts as over (strict `<`, same style as is_usable). A timestamp
    in the future (clock skew) counts as in cooldown: failing toward "send
    less mail". Naive vs aware datetimes raise TypeError on purpose.
    """
    if last_issued_at is None:
        return False
    return now - last_issued_at < cooldown