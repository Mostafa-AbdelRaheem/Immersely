import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

import app.services.email_verification as svc
from app.schemas.email_token import TokenPurpose
from app.services.email_sender import EmailSendError
from app.services.email_tokens import InvalidTokenError

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


class FakeSender:
    def __init__(self):
        self.sent = []

    async def send(self, message):
        self.sent.append(message)


class FailingSender:
    async def send(self, message):
        raise EmailSendError("provider down")


class FakeDB:
    def __init__(self):
        self.statements = []
        self.commits = 0

    async def execute(self, stmt):
        self.statements.append(stmt)

    async def commit(self):
        self.commits += 1


def make_user(**overrides):
    fields = dict(
        id=USER_ID, email="mostafa@example.com", name="Mostafa", email_verified_at=None
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


@pytest.fixture(autouse=True)
def pinned_settings(monkeypatch):
    monkeypatch.setattr(svc.settings, "frontend_base_url", "https://app.example.test")
    monkeypatch.setattr(svc.settings, "verify_email_token_ttl_minutes", 120)


@pytest.fixture
def issued(monkeypatch):
    calls = []

    async def fake_issue(db, user_id, purpose, *, now=None):
        calls.append((user_id, purpose, now))
        return "RAW-TOKEN-123"

    monkeypatch.setattr(svc, "issue_token", fake_issue)
    return calls


@pytest.fixture
def consumed(monkeypatch):
    calls = []

    async def fake_consume(db, raw, purpose, *, now=None):
        calls.append((raw, purpose, now))
        return USER_ID

    monkeypatch.setattr(svc, "consume_token", fake_consume)
    return calls


def send(user, sender):
    asyncio.run(svc.send_verification_email(FakeDB(), sender, user, now=NOW))


def verify(db, raw="raw-token"):
    asyncio.run(svc.verify_email(db, raw, now=NOW))


def test_send_emails_the_link_to_the_user(issued):
    sender = FakeSender()
    send(make_user(), sender)
    message = sender.sent[0]
    assert message.to == "mostafa@example.com"
    assert "https://app.example.test/verify-email#token=RAW-TOKEN-123" in message.text_body
    assert "Hi Mostafa," in message.text_body
    assert "2 hours" in message.text_body  # the lifetime follows the setting


def test_send_issues_a_verification_token_for_that_user(issued):
    send(make_user(), FakeSender())
    assert issued == [(USER_ID, TokenPurpose.VERIFY_EMAIL, NOW)]


def test_send_refuses_an_already_verified_user(issued):
    sender = FakeSender()
    with pytest.raises(svc.EmailAlreadyVerifiedError):
        send(make_user(email_verified_at=NOW), sender)
    assert issued == []
    assert sender.sent == []


def test_send_failure_propagates_so_the_route_can_decide(issued):
    with pytest.raises(EmailSendError):
        send(make_user(), FailingSender())


def test_verify_consumes_a_verify_email_token(consumed):
    verify(FakeDB(), raw="the-token")
    assert consumed == [("the-token", TokenPurpose.VERIFY_EMAIL, NOW)]


def test_verify_marks_the_user_only_where_still_unverified(consumed):
    db = FakeDB()
    verify(db)
    assert db.commits == 1
    compiled = db.statements[0].compile(dialect=postgresql.dialect())
    assert "email_verified_at IS NULL" in str(compiled)
    assert USER_ID in compiled.params.values()
    assert NOW in compiled.params.values()


def test_verify_with_a_bad_token_touches_no_user(monkeypatch):
    async def failing_consume(db, raw, purpose, *, now=None):
        raise InvalidTokenError("nope")

    monkeypatch.setattr(svc, "consume_token", failing_consume)
    db = FakeDB()
    with pytest.raises(InvalidTokenError):
        verify(db)
    assert db.statements == []
    assert db.commits == 0