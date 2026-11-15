import asyncio
import unicodedata

import pytest

import app.services.auth as auth
from app.services.password_policy import PasswordProblem

EMAIL = "mostafa@example.com"
STRONG = "zq7-quiet-Orchid-4821-xylophone-ruminate"


def validate(password, email=EMAIL):
    return asyncio.run(auth.validate_new_password(password, email=email))


def install_lookup(monkeypatch, *, breached):
    """Replace the HIBP lookup AS SEEN BY auth.py; record every call."""
    calls = []

    async def fake(password, *, timeout_s):
        calls.append((password, timeout_s))
        return breached

    monkeypatch.setattr(auth, "is_password_breached", fake)
    return calls


@pytest.fixture(autouse=True)
def pinned_settings_and_tripwire(monkeypatch):
    monkeypatch.setattr(auth.settings, "hibp_enabled", True)
    monkeypatch.setattr(auth.settings, "password_min_length", 8)
    monkeypatch.setattr(auth.settings, "password_max_bytes", 72)

    async def tripwire(password, *, timeout_s):
        raise AssertionError("unexpected real HIBP lookup in a test")

    monkeypatch.setattr(auth, "is_password_breached", tripwire)


def test_too_short_is_rejected_without_a_network_lookup(monkeypatch):
    calls = install_lookup(monkeypatch, breached=False)
    with pytest.raises(auth.WeakPasswordError) as exc:
        validate("short")
    assert PasswordProblem.TOO_SHORT in exc.value.problems
    assert calls == []  # cheap local checks must run BEFORE the network call


def test_password_equal_to_email_is_rejected(monkeypatch):
    calls = install_lookup(monkeypatch, breached=False)
    with pytest.raises(auth.WeakPasswordError) as exc:
        validate(EMAIL)
    assert PasswordProblem.SAME_AS_EMAIL in exc.value.problems
    assert calls == []


def test_breached_password_raises_exactly_breached(monkeypatch):
    calls = install_lookup(monkeypatch, breached=True)
    with pytest.raises(auth.WeakPasswordError) as exc:
        validate(STRONG)
    assert exc.value.problems == [PasswordProblem.BREACHED]
    assert len(calls) == 1


def test_disabled_flag_skips_the_lookup_and_returns_the_password(monkeypatch):
    monkeypatch.setattr(auth.settings, "hibp_enabled", False)  # tripwire stays armed
    assert validate(STRONG) == STRONG


def test_returns_the_nfc_normalized_password_and_hibp_sees_the_same_bytes(monkeypatch):
    calls = install_lookup(monkeypatch, breached=False)
    # "u" + U+0308 (combining diaeresis), written as escapes so no editor can
    # silently normalize the source text.
    raw = "zq7-quiet-Ju\u0308rgen-4821-xylophone"
    result = validate(raw)
    assert result == unicodedata.normalize("NFC", raw)
    assert "\u00fc" in result and "\u0308" not in result
    assert calls[0][0] == result  # the breach lookup saw the normalized form