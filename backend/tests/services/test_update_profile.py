import asyncio
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

import app.services.auth as auth
from app.services.username_policy import UsernameProblem

SECRET = "SECRET-ROW-DO-NOT-LEAK"


class FakeCause(Exception):
    """Shaped like asyncpg's UniqueViolationError (see the register tests)."""

    def __init__(self, constraint_name):
        super().__init__("unique violation")
        self.constraint_name = constraint_name


def make_integrity_error(constraint_name):
    orig = Exception("driver wrapper")
    if constraint_name is not None:
        orig.__cause__ = FakeCause(constraint_name)
    return IntegrityError("UPDATE users ...", {"username": SECRET}, orig)


class FakeResult:
    def __init__(self, row):
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class FakeDB:
    """`lookups` feeds the pre-check SELECT results in order. An unexpected
    extra query raises IndexError, so the query count is part of the contract."""

    def __init__(self, lookups=(), commit_error=None):
        self._lookups = list(lookups)
        self.commit_error = commit_error
        self.executed = 0
        self.committed = False
        self.rolled_back = False
        self.refreshed = []

    async def execute(self, stmt):
        self.executed += 1
        return FakeResult(self._lookups.pop(0))

    async def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        self.refreshed.append(obj)


def make_user(username="legacy.name", name="Old Name"):
    return SimpleNamespace(id=uuid.uuid4(), username=username, name=name)


def update(db, user, **kwargs):
    return asyncio.run(auth.update_profile(db, user, **kwargs))


@pytest.fixture(autouse=True)
def pinned_limits(monkeypatch):
    monkeypatch.setattr(auth.settings, "username_min_length", 3)
    monkeypatch.setattr(auth.settings, "username_max_length", 20)


def test_name_only_update_leaves_a_legacy_username_untouched():
    db = FakeDB()  # any query would raise IndexError
    user = make_user(username="legacy.name")  # a dot: invalid under today's rules
    result = update(db, user, name="New Name")
    assert result.name == "New Name"
    assert result.username == "legacy.name"
    assert db.executed == 0
    assert db.committed is True


def test_unchanged_username_is_a_noop_with_no_query():
    db = FakeDB()
    user = make_user(username="mostafa")
    update(db, user, username="  MoStAfA ")  # normalizes to the same value
    assert user.username == "mostafa"
    assert db.executed == 0


def test_changed_username_is_normalized_and_stored():
    db = FakeDB(lookups=(None,))
    user = make_user(username="mostafa")
    update(db, user, username="  NewName ")
    assert user.username == "newname"
    assert db.executed == 1


def test_taken_username_raises_and_changes_nothing():
    db = FakeDB(lookups=(object(),))
    user = make_user(username="mostafa")
    with pytest.raises(auth.UsernameTakenError):
        update(db, user, username="someone_else", name="Ignored")
    assert user.username == "mostafa"
    assert user.name == "Old Name"
    assert db.committed is False


def test_invalid_username_is_rejected_before_any_query():
    db = FakeDB()
    with pytest.raises(auth.InvalidUsernameError) as exc:
        update(db, make_user(), username="a!")
    assert exc.value.problems == [
        UsernameProblem.TOO_SHORT,
        UsernameProblem.INVALID_CHARACTERS,
    ]
    assert db.executed == 0
    assert db.committed is False


def test_race_on_the_username_constraint_becomes_username_taken():
    db = FakeDB(
        lookups=(None,), commit_error=make_integrity_error("users_username_key")
    )
    with pytest.raises(auth.UsernameTakenError) as exc:
        update(db, make_user(username="mostafa"), username="newname")
    assert db.rolled_back is True
    assert exc.value.__cause__ is None
    assert exc.value.__suppress_context__ is True
    assert SECRET not in str(exc.value)


def test_unknown_constraint_propagates_loudly_after_rollback():
    db = FakeDB(commit_error=make_integrity_error("ck_users_username_lowercase"))
    with pytest.raises(IntegrityError):
        update(db, make_user(), name="Whatever")
    assert db.rolled_back is True


def test_user_is_refreshed_after_a_successful_commit():
    db = FakeDB()
    user = make_user()
    update(db, user, name="New Name")
    assert db.refreshed == [user]