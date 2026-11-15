import asyncio
import uuid
from types import SimpleNamespace

import pytest

import app.services.auth as auth

CURRENT = "zq7-quiet-Orchid-4821-xylophone-ruminate"
NEW = "mango-Harbor-7734-lantern-quartz-bridge"


class FakeDB:
    def __init__(self, commit_error=None):
        self.commit_error = commit_error
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def make_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="mostafa@example.com",
        name="Mostafa",
        hashed_password="H:" + CURRENT,
    )


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(auth.settings, "hibp_enabled", True)
    monkeypatch.setattr(auth.settings, "password_min_length", 8)
    monkeypatch.setattr(auth.settings, "password_max_bytes", 72)
    # Fake bcrypt: the "hash" of p is "H:" + p, so wrong passwords really fail.
    monkeypatch.setattr(auth, "verify_password", lambda p, h: h == "H:" + p)
    monkeypatch.setattr(auth, "hash_password", lambda p: "H:" + p)

    state = SimpleNamespace(breach_calls=[], revoke_calls=[])

    async def fake_breach(password, *, timeout_s):
        state.breach_calls.append(password)
        return False

    async def fake_revoke(db, user_id, **kwargs):
        state.revoke_calls.append((user_id, kwargs))
        return 1

    monkeypatch.setattr(auth, "is_password_breached", fake_breach)
    monkeypatch.setattr(auth, "revoke_user_refresh_tokens", fake_revoke)
    return state


def change(db, user, current=CURRENT, new=NEW, **kwargs):
    return asyncio.run(auth.change_password(db, user, current, new, **kwargs))


def test_wrong_current_password_changes_nothing(fakes):
    db, user = FakeDB(), make_user()
    with pytest.raises(auth.CurrentPasswordIncorrectError):
        change(db, user, current="not-the-password")
    assert user.hashed_password == "H:" + CURRENT
    assert db.commits == 0
    assert fakes.breach_calls == []
    assert fakes.revoke_calls == []


def test_same_password_is_rejected_without_any_work(fakes):
    db, user = FakeDB(), make_user()
    with pytest.raises(auth.SamePasswordError):
        change(db, user, new=CURRENT)
    assert db.commits == 0
    assert fakes.breach_calls == []
    assert fakes.revoke_calls == []


def test_weak_new_password_changes_nothing(fakes):
    db, user = FakeDB(), make_user()
    with pytest.raises(auth.WeakPasswordError):
        change(db, user, new="short")
    assert user.hashed_password == "H:" + CURRENT
    assert db.commits == 0
    assert fakes.revoke_calls == []


def test_success_sets_hash_revokes_others_and_commits_once(fakes):
    db, user = FakeDB(), make_user()
    notice = change(db, user, keep_token_hash="keep-me")
    assert user.hashed_password == "H:" + NEW
    assert db.commits == 1
    assert len(fakes.revoke_calls) == 1
    user_id, kwargs = fakes.revoke_calls[0]
    assert user_id == user.id
    assert kwargs["except_token_hash"] == "keep-me"
    assert kwargs["commit"] is False  # one transaction, owned by the service
    assert notice.to == "mostafa@example.com"


def test_no_kept_hash_means_every_session_is_revoked(fakes):
    change(FakeDB(), make_user())
    assert fakes.revoke_calls[0][1]["except_token_hash"] is None


def test_new_password_is_normalized_before_hashing():
    user = make_user()
    change(FakeDB(), user, new="mango-Harbor-7734-u\u0308-lantern")  # u + combining mark
    assert user.hashed_password == "H:" + "mango-Harbor-7734-\u00fc-lantern"


def test_failed_commit_rolls_back_and_propagates():
    db = FakeDB(commit_error=RuntimeError("db down"))
    with pytest.raises(RuntimeError):
        change(db, make_user())
    assert db.rollbacks == 1