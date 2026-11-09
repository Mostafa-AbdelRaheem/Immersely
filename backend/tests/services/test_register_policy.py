import asyncio

import pytest

import app.services.auth as auth
from app.schemas.user import UserCreate
from app.services.password_policy import PasswordProblem

EMAIL = "mostafa@example.com"
STRONG = "zq7-quiet-Orchid-4821-xylophone-ruminate"


class FakeResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class FakeDB:
    """Just enough of AsyncSession for register_user."""

    def __init__(self, existing=None):
        self.existing = existing
        self.executed = 0
        self.added = []
        self.committed = False

    async def execute(self, stmt):
        self.executed += 1
        return FakeResult(self.existing)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True


def register(db, password, email=EMAIL):
    return asyncio.run(
auth.register_user(
            db,
            UserCreate(
                email=email, password=password, name="Mostafa", username="mostafa"
            ),
        )
    )


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

    async def tripwire(password, *, timeout_s):
        raise AssertionError("unexpected real HIBP lookup in a test")

    monkeypatch.setattr(auth, "is_password_breached", tripwire)


def test_too_short_is_rejected_without_a_lookup_or_db_query():
    db = FakeDB()
    with pytest.raises(auth.WeakPasswordError) as exc:
        register(db, "short")  # a lookup here would hit the tripwire
    assert exc.value.problems == [PasswordProblem.TOO_SHORT]
    assert db.executed == 0


def test_password_equal_to_email_is_rejected_without_a_lookup():
    with pytest.raises(auth.WeakPasswordError) as exc:
        register(FakeDB(), EMAIL)
    assert exc.value.problems == [PasswordProblem.SAME_AS_EMAIL]


def test_breached_password_is_rejected_after_one_lookup(monkeypatch):
    calls = install_lookup(monkeypatch, breached=True)
    db = FakeDB()
    with pytest.raises(auth.WeakPasswordError) as exc:
        register(db, STRONG)
    assert exc.value.problems == [PasswordProblem.BREACHED]
    assert calls == [(STRONG, auth.settings.hibp_timeout_s)]
    assert db.executed == 0


def test_not_breached_password_creates_a_user_with_a_hash(monkeypatch):
    install_lookup(monkeypatch, breached=False)
    db = FakeDB()
    user = register(db, STRONG)
    assert db.added == [user]
    assert db.committed is True
    assert user.email == EMAIL
    assert user.hashed_password != STRONG


def test_disabled_flag_skips_the_lookup_entirely(monkeypatch):
    monkeypatch.setattr(auth.settings, "hibp_enabled", False)  # tripwire stays armed
    db = FakeDB()
    user = register(db, STRONG)
    assert db.added == [user]


def test_weak_password_beats_duplicate_email():
    db = FakeDB(existing=object())
    with pytest.raises(auth.WeakPasswordError):
        register(db, "short")
    assert db.executed == 0


def test_breached_password_gives_the_same_error_for_a_taken_email(monkeypatch):
    # No enumeration: a breached password is rejected identically whether or
    # not the email exists, and the DB is never consulted.
    install_lookup(monkeypatch, breached=True)
    db = FakeDB(existing=object())
    with pytest.raises(auth.WeakPasswordError) as exc:
        register(db, STRONG)
    assert exc.value.problems == [PasswordProblem.BREACHED]
    assert db.executed == 0


def test_strong_password_with_taken_email_raises_duplicate(monkeypatch):
    calls = install_lookup(monkeypatch, breached=False)
    db = FakeDB(existing=object())
    with pytest.raises(auth.EmailAlreadyRegisteredError):
        register(db, STRONG)
    assert len(calls) == 1
    assert db.added == []

def test_too_long_password_is_rejected_without_a_lookup_or_db_query():
    db = FakeDB()
    with pytest.raises(auth.WeakPasswordError) as exc:
        register(db, "x" * 73)  # a lookup here would hit the tripwire
    assert exc.value.problems == [PasswordProblem.TOO_LONG]
    assert db.executed == 0