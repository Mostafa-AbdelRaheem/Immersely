import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import app.services.password_reset as pr
from app.services.auth import WeakPasswordError
from app.services.email_tokens import InvalidTokenError
from app.services.password_policy import PasswordProblem

NOW = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
USER = SimpleNamespace(id=uuid.uuid4(), email="mostafa@example.com", name="Mostafa")


class FakeDB:
    def __init__(self, events):
        self.events = events

    async def execute(self, stmt):
        self.events.append("update_user")

    async def commit(self):
        self.events.append("commit")

    async def rollback(self):
        self.events.append("rollback")


def run_reset(world, token="RAW", password="whatever"):
    return asyncio.run(pr.reset_password(world.db, token, password, now=NOW))


@pytest.fixture
def world(monkeypatch):
    w = SimpleNamespace(events=[], user=USER, hashed_inputs=[], consume_kwargs=None)
    w.db = FakeDB(w.events)
    w.peek_error = None
    w.validate_error = None
    w.consume_error = None
    w.revoke_error = None
    w.consume_returns = USER.id

    async def fake_peek(db, raw, purpose, *, now=None):
        w.events.append("peek")
        if w.peek_error:
            raise w.peek_error
        return USER.id

    async def fake_load(db, user_id):
        w.events.append("load")
        return w.user

    async def fake_validate(raw_password, *, email):
        w.events.append("validate")
        if w.validate_error:
            raise w.validate_error
        return "NORMALIZED"

    def fake_hash(password):
        w.events.append("hash")
        w.hashed_inputs.append(password)
        return "HASHED"

    async def fake_consume(db, raw, purpose, *, commit=True, now=None):
        w.events.append("consume")
        w.consume_kwargs = {"commit": commit}
        if w.consume_error:
            raise w.consume_error
        return w.consume_returns

    async def fake_revoke(db, user_id, *, now=None, commit=True):
        w.events.append("revoke")
        w.revoke_kwargs = {"commit": commit}
        if w.revoke_error:
            raise w.revoke_error
        return 2

    monkeypatch.setattr(pr, "peek_token", fake_peek)
    monkeypatch.setattr(pr, "_load_user_by_id", fake_load)
    monkeypatch.setattr(pr, "validate_new_password", fake_validate)
    monkeypatch.setattr(pr, "hash_password", fake_hash)
    monkeypatch.setattr(pr, "consume_token", fake_consume)
    monkeypatch.setattr(pr, "revoke_user_refresh_tokens", fake_revoke)
    return w


def test_happy_path_runs_in_the_designed_order(world):
    msg = run_reset(world)
    assert world.events == [
        "peek", "load", "validate", "hash", "consume",
        "update_user", "revoke", "commit",
    ]
    assert msg.to == USER.email
    assert "changed" in msg.subject
    assert "http" not in msg.text_body  # a security notice carries no link


def test_everything_inside_the_transaction_defers_its_commit(world):
    run_reset(world)
    assert world.consume_kwargs == {"commit": False}
    assert world.revoke_kwargs == {"commit": False}
    assert world.events.count("commit") == 1


def test_the_normalized_password_is_what_gets_hashed(world):
    run_reset(world, password="raw-input")
    assert world.hashed_inputs == ["NORMALIZED"]


def test_weak_password_does_not_burn_the_token(world):
    world.validate_error = WeakPasswordError([PasswordProblem.TOO_SHORT])
    with pytest.raises(WeakPasswordError):
        run_reset(world)
    assert "consume" not in world.events
    assert "commit" not in world.events


def test_bad_token_stops_before_anything_else(world):
    world.peek_error = InvalidTokenError("bad")
    with pytest.raises(InvalidTokenError):
        run_reset(world)
    assert world.events == ["peek"]


def test_user_missing_after_peek_is_an_invalid_token(world):
    world.user = None
    with pytest.raises(InvalidTokenError):
        run_reset(world)
    assert "consume" not in world.events


def test_losing_the_claim_race_rolls_back_and_changes_nothing(world):
    world.consume_error = InvalidTokenError("lost the race")
    with pytest.raises(InvalidTokenError):
        run_reset(world)
    assert "update_user" not in world.events
    assert "commit" not in world.events
    assert world.events[-1] == "rollback"


def test_a_failure_while_revoking_rolls_the_whole_unit_back(world):
    world.revoke_error = RuntimeError("db hiccup")
    with pytest.raises(RuntimeError):
        run_reset(world)
    assert "commit" not in world.events
    assert world.events[-1] == "rollback"


def test_a_claim_for_a_different_user_is_rejected(world):
    world.consume_returns = uuid.uuid4()
    with pytest.raises(InvalidTokenError):
        run_reset(world)
    assert "commit" not in world.events
    assert world.events[-1] == "rollback"