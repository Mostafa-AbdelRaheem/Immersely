import re
from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import hash_token
from app.services.token_logic import compute_expiry, generate_token, is_usable

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


def test_generate_token_returns_the_raw_token_and_its_sha256():
    raw, hashed = generate_token()
    assert hashed == hash_token(raw)
    assert raw != hashed


def test_token_shapes():
    raw, hashed = generate_token()
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", raw)  # 32 bytes, urlsafe, no padding
    assert re.fullmatch(r"[0-9a-f]{64}", hashed)


def test_tokens_are_unique():
    assert len({generate_token()[0] for _ in range(200)}) == 200


def test_compute_expiry_adds_the_ttl():
    assert compute_expiry(NOW, timedelta(minutes=30)) == NOW + timedelta(minutes=30)


def test_usable_when_unused_and_before_expiry():
    assert is_usable(expires_at=NOW + timedelta(seconds=1), used_at=None, now=NOW) is True


def test_the_expiry_instant_itself_is_expired():
    assert is_usable(expires_at=NOW, used_at=None, now=NOW) is False


def test_expired_token_is_not_usable():
    assert is_usable(expires_at=NOW - timedelta(seconds=1), used_at=None, now=NOW) is False


def test_used_token_is_not_usable_even_before_expiry():
    assert is_usable(expires_at=NOW + timedelta(hours=1), used_at=NOW, now=NOW) is False


def test_naive_and_aware_datetimes_are_not_silently_mixed():
    with pytest.raises(TypeError):
        is_usable(expires_at=NOW.replace(tzinfo=None), used_at=None, now=NOW)