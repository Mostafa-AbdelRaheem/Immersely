import asyncio
import uuid

import pytest

import app.services.auth as auth
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin

EMAIL = "mostafa@example.com"
COMPOSED = "Gr\u00fcn-quiet-Orchid-4821-xylophone"  # "ü" as one code point
DECOMPOSED = "Gru\u0308n-quiet-Orchid-4821-xylophone"  # "u" + combining diaeresis
ASCII_PASSWORD = "zq7-quiet-Orchid-4821-xylophone-ruminate"


class FakeResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class FakeDB:
    """register: two empty pre-check SELECTs. login: one SELECT returning a user."""

    def __init__(self, lookups):
        self._lookups = list(lookups)
        self.added = []

    async def execute(self, stmt):
        return FakeResult(self._lookups.pop(0))

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass


def register(password):
    db = FakeDB([None, None])
    user = asyncio.run(
        auth.register_user(
            db,
            UserCreate(
                email=EMAIL, password=password, name="Mostafa", username="mostafa"
            ),
        )
    )
    user.id = uuid.uuid4()  # normally assigned at INSERT; the fake DB never inserts
    return user


def login(user, password):
    return asyncio.run(
        auth.login_user(FakeDB([user]), UserLogin(email=EMAIL, password=password))
    )


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(auth.settings, "hibp_enabled", True)
    monkeypatch.setattr(auth.settings, "password_min_length", 8)
    monkeypatch.setattr(auth.settings, "password_max_bytes", 72)
    monkeypatch.setattr(auth.settings, "username_min_length", 3)
    monkeypatch.setattr(auth.settings, "username_max_length", 20)
    auth._failed_login_attempts.clear()
    yield
    auth._failed_login_attempts.clear()


@pytest.fixture
def no_breach(monkeypatch):
    async def fake_lookup(password, *, timeout_s):
        return False

    monkeypatch.setattr(auth, "is_password_breached", fake_lookup)


@pytest.fixture
def seen(monkeypatch):
    """Records what each step of register_user receives (no bcrypt, no network)."""
    record = {}
    real_check = auth.check_password

    def spy_check(password, **kwargs):
        record["policy"] = password
        return real_check(password, **kwargs)

    async def fake_lookup(password, *, timeout_s):
        record["breach"] = password
        return False

    def fake_hash(password):
        record["hash"] = password
        return "FAKE-HASH"

    monkeypatch.setattr(auth, "check_password", spy_check)
    monkeypatch.setattr(auth, "is_password_breached", fake_lookup)
    monkeypatch.setattr(auth, "hash_password", fake_hash)
    return record


def test_premise_the_two_forms_are_different_strings():
    assert DECOMPOSED != COMPOSED


def test_register_gives_every_step_the_normalized_password(seen):
    register(DECOMPOSED)
    assert seen == {"policy": COMPOSED, "breach": COMPOSED, "hash": COMPOSED}


def test_registered_decomposed_can_log_in_with_composed(no_breach):
    user = register(DECOMPOSED)
    access, refresh = login(user, COMPOSED)
    assert access and refresh


def test_registered_composed_can_log_in_with_decomposed(no_breach):
    user = register(COMPOSED)
    access, refresh = login(user, DECOMPOSED)
    assert access and refresh


def test_wrong_password_still_fails(no_breach):
    user = register(COMPOSED)
    with pytest.raises(auth.InvalidCredentialsError):
        login(user, COMPOSED + "x")


def test_legacy_ascii_hash_made_without_normalization_still_verifies():
    # Existing accounts were hashed with the raw password. For ASCII, NFC is
    # the identity, so they must keep working untouched.
    user = User(
        email=EMAIL,
        username="mostafa",
        hashed_password=auth.hash_password(ASCII_PASSWORD),
    )
    user.id = uuid.uuid4()
    access, refresh = login(user, ASCII_PASSWORD)
    assert access and refresh