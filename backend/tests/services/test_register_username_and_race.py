import asyncio

import pytest
from sqlalchemy.exc import IntegrityError

import app.services.auth as auth
from app.schemas.user import UserCreate
from app.services.username_policy import UsernameProblem

EMAIL = "mostafa@example.com"
STRONG = "zq7-quiet-Orchid-4821-xylophone-ruminate"
SECRET_HASH = "SECRET-HASH-DO-NOT-LEAK"


class FakeCause(Exception):
    """Shaped like asyncpg's UniqueViolationError (checked on the real DB).

    Must derive from Exception: Python only accepts exceptions as __cause__.
    """

    def __init__(self, constraint_name):
        super().__init__("unique violation")
        self.constraint_name = constraint_name


def make_integrity_error(constraint_name):
    orig = Exception("driver wrapper")  # stands in for SQLAlchemy's adapter error
    if constraint_name is not None:
        orig.__cause__ = FakeCause(constraint_name)
    return IntegrityError(
        "INSERT INTO users ...", {"hashed_password": SECRET_HASH}, orig
    )


class FakeResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class FakeDB:
    """Just enough of AsyncSession. `lookups` feeds the pre-check SELECTs in
    order: (email lookup, username lookup). A third query would raise."""

    def __init__(self, lookups=(None, None), commit_error=None):
        self._lookups = list(lookups)
        self.commit_error = commit_error
        self.executed = 0
        self.added = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, stmt):
        self.executed += 1
        return FakeResult(self._lookups.pop(0))

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


def register(db, *, password=STRONG, email=EMAIL, name="Mostafa", username="mostafa"):
    return asyncio.run(
        auth.register_user(
            db,
            UserCreate(email=email, password=password, name=name, username=username),
        )
    )


@pytest.fixture(autouse=True)
def lookup_calls(monkeypatch):
    """Pin settings, skip bcrypt, and record HIBP lookups (never real ones)."""
    monkeypatch.setattr(auth.settings, "hibp_enabled", True)
    monkeypatch.setattr(auth.settings, "password_min_length", 8)
    monkeypatch.setattr(auth.settings, "username_min_length", 3)
    monkeypatch.setattr(auth.settings, "username_max_length", 20)
    monkeypatch.setattr(auth, "hash_password", lambda password: SECRET_HASH)

    calls = []

    async def fake_lookup(password, *, timeout_s):
        calls.append(password)
        return False

    monkeypatch.setattr(auth, "is_password_breached", fake_lookup)
    return calls


def test_invalid_username_is_rejected_before_any_lookup_or_query(lookup_calls):
    db = FakeDB()
    with pytest.raises(auth.InvalidUsernameError) as exc:
        register(db, username="a!")
    assert exc.value.problems == [
        UsernameProblem.TOO_SHORT,
        UsernameProblem.INVALID_CHARACTERS,
    ]
    assert lookup_calls == []
    assert db.executed == 0


def test_username_problems_win_over_password_problems():
    with pytest.raises(auth.InvalidUsernameError):
        register(FakeDB(), password="short", username="a!")


def test_username_is_normalized_before_it_is_stored():
    user = register(FakeDB(), username="  MoStAfA ")
    assert user.username == "mostafa"


def test_name_is_stored_trimmed():
    user = register(FakeDB(), name="  Mostafa A.  ")
    assert user.name == "Mostafa A."


def test_taken_email_raises_and_skips_the_username_check():
    db = FakeDB(lookups=(object(),))  # a second query would raise IndexError
    with pytest.raises(auth.EmailAlreadyRegisteredError):
        register(db)
    assert db.executed == 1
    assert db.added == []


def test_taken_username_raises_and_inserts_nothing():
    db = FakeDB(lookups=(None, object()))
    with pytest.raises(auth.UsernameTakenError):
        register(db)
    assert db.executed == 2
    assert db.added == []


def test_premise_the_raw_error_message_contains_the_hash():
    # If this fails, the leak test below would pass for the wrong reason.
    assert SECRET_HASH in str(make_integrity_error("users_email_key"))


@pytest.mark.parametrize(
    "constraint, expected",
    [
        ("users_username_key", auth.UsernameTakenError),
        ("users_email_key", auth.EmailAlreadyRegisteredError),
    ],
)
def test_race_is_translated_by_constraint_name_without_leaking(constraint, expected):
    db = FakeDB(commit_error=make_integrity_error(constraint))
    with pytest.raises(expected) as exc:
        register(db)
    assert db.rolled_back is True
    assert exc.value.__cause__ is None
    assert exc.value.__suppress_context__ is True  # raise ... from None
    assert SECRET_HASH not in str(exc.value)


def test_unknown_constraint_propagates_loudly_after_rollback():
    db = FakeDB(commit_error=make_integrity_error("ck_users_email_lowercase"))
    with pytest.raises(IntegrityError):
        register(db)
    assert db.rolled_back is True


def test_error_without_constraint_info_propagates():
    db = FakeDB(commit_error=make_integrity_error(None))
    with pytest.raises(IntegrityError):
        register(db)
    assert db.rolled_back is True


def test_violated_constraint_reads_the_name_from_the_cause():
    assert (
        auth._violated_constraint(make_integrity_error("users_username_key"))
        == "users_username_key"
    )


def test_violated_constraint_is_none_when_the_driver_gives_no_cause():
    assert auth._violated_constraint(make_integrity_error(None)) is None