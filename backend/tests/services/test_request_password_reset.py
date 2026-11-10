import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import app.services.password_reset as pr

NOW = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
EMAIL = "mostafa@example.com"
USER = SimpleNamespace(id=uuid.uuid4(), email=EMAIL, name="Mostafa")


def request(email=EMAIL):
    return asyncio.run(pr.request_password_reset(object(), email, now=NOW))


@pytest.fixture
def world(monkeypatch):
    """Patch the lookups AS SEEN BY password_reset.py; record issue_token calls."""
    state = SimpleNamespace(user=USER, last=None, issued=[])

    async def fake_find(db, email):
        return state.user

    async def fake_last(db, user_id):
        return state.last

    async def fake_issue(db, user_id, purpose, *, now=None):
        state.issued.append((user_id, purpose.value, now))
        return "RAWTOKEN"

    monkeypatch.setattr(pr, "_find_user_by_email", fake_find)
    monkeypatch.setattr(pr, "_last_reset_issued_at", fake_last)
    monkeypatch.setattr(pr, "issue_token", fake_issue)
    monkeypatch.setattr(pr.settings, "reset_password_cooldown_s", 60)
    monkeypatch.setattr(pr.settings, "reset_password_token_ttl_minutes", 30)
    monkeypatch.setattr(pr.settings, "frontend_base_url", "http://localhost:5173")
    return state


def test_unknown_email_returns_none_and_issues_nothing(world):
    world.user = None
    assert request() is None
    assert world.issued == []


def test_inside_the_cooldown_returns_none_and_issues_nothing(world):
    world.last = NOW - timedelta(seconds=59)
    assert request() is None
    assert world.issued == []


def test_first_request_issues_a_token_and_builds_the_message(world):
    msg = request()
    assert world.issued == [(USER.id, "reset_password", NOW)]
    assert msg.to == EMAIL
    assert "Reset" in msg.subject
    assert "http://localhost:5173/reset-password#token=RAWTOKEN" in msg.text_body
    assert "30 minutes" in msg.text_body


def test_outside_the_cooldown_issues_again(world):
    world.last = NOW - timedelta(seconds=60)  # exactly at the boundary = over
    assert request() is not None
    assert len(world.issued) == 1


def test_cooldown_length_comes_from_settings(world, monkeypatch):
    monkeypatch.setattr(pr.settings, "reset_password_cooldown_s", 120)
    world.last = NOW - timedelta(seconds=90)
    assert request() is None  # would have been allowed under the 60 s default
    assert world.issued == []