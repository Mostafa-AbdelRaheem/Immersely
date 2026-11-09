import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import postgresql

import app.services.email_tokens as svc
from app.core.security import hash_token
from app.models.email_token import EmailToken
from app.schemas.email_token import TokenPurpose

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDB:
    """Records statements; execute() returns `result_value` as the RETURNING row."""

    def __init__(self, result_value=None):
        self.result_value = result_value
        self.statements = []
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        self.statements.append(stmt)
        return FakeResult(self.result_value)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


def params_of(stmt):
    return list(stmt.compile(dialect=postgresql.dialect()).params.values())


def issue(db, purpose=TokenPurpose.VERIFY_EMAIL):
    return asyncio.run(svc.issue_token(db, USER_ID, purpose, now=NOW))


def consume(db, raw="raw-token", purpose=TokenPurpose.VERIFY_EMAIL):
    return asyncio.run(svc.consume_token(db, raw, purpose, now=NOW))


def test_issue_returns_the_raw_token_and_stores_only_its_hash():
    db = FakeDB()
    raw = issue(db)
    row = db.added[0]
    assert isinstance(row, EmailToken)
    assert row.token_hash == hash_token(raw)
    assert raw != row.token_hash


def test_issue_sets_user_purpose_and_verification_expiry(monkeypatch):
    monkeypatch.setattr(svc.settings, "verify_email_token_ttl_minutes", 90)
    db = FakeDB()
    issue(db)
    row = db.added[0]
    assert row.user_id == USER_ID
    assert row.purpose == "verify_email"
    assert row.expires_at == NOW + timedelta(minutes=90)


def test_reset_tokens_use_the_reset_lifetime(monkeypatch):
    monkeypatch.setattr(svc.settings, "reset_password_token_ttl_minutes", 7)
    db = FakeDB()
    issue(db, TokenPurpose.RESET_PASSWORD)
    row = db.added[0]
    assert row.purpose == "reset_password"
    assert row.expires_at == NOW + timedelta(minutes=7)


def test_issue_supersedes_older_unused_tokens_in_a_single_commit():
    db = FakeDB()
    issue(db)
    assert len(db.statements) == 1
    params = params_of(db.statements[0])
    assert USER_ID in params
    assert "verify_email" in params
    assert NOW in params  # used_at is set to "now" on the older tokens
    assert db.commits == 1


def test_consume_returns_the_user_id_and_commits():
    db = FakeDB(result_value=USER_ID)
    assert consume(db) == USER_ID
    assert db.commits == 1


def test_consume_raises_when_no_row_matches_and_does_not_commit():
    db = FakeDB(result_value=None)
    with pytest.raises(svc.InvalidTokenError):
        consume(db)
    assert db.commits == 0


def test_consume_sends_the_hash_never_the_raw_token():
    db = FakeDB(result_value=USER_ID)
    consume(db, raw="the-raw-token")
    params = params_of(db.statements[0])
    assert hash_token("the-raw-token") in params
    assert "the-raw-token" not in params
    assert "verify_email" in params
    assert NOW in params


@pytest.mark.parametrize("purpose", list(TokenPurpose))
def test_every_purpose_has_a_positive_lifetime(purpose):
    assert svc._ttl(purpose) > timedelta(0)

def peek(db, raw="raw-token", purpose=TokenPurpose.VERIFY_EMAIL):
    return asyncio.run(svc.peek_token(db, raw, purpose, now=NOW))


def test_consume_can_leave_the_commit_to_the_caller():
    db = FakeDB(result_value=USER_ID)
    result = asyncio.run(
        svc.consume_token(
            db, "raw-token", TokenPurpose.VERIFY_EMAIL, now=NOW, commit=False
        )
    )
    assert result == USER_ID
    assert db.commits == 0


def test_consume_with_commit_false_still_raises_on_a_bad_token():
    db = FakeDB(result_value=None)
    with pytest.raises(svc.InvalidTokenError):
        asyncio.run(
            svc.consume_token(
                db, "raw-token", TokenPurpose.VERIFY_EMAIL, now=NOW, commit=False
            )
        )
    assert db.commits == 0


def test_peek_returns_the_user_id_and_changes_nothing():
    db = FakeDB(result_value=USER_ID)
    assert peek(db) == USER_ID
    assert db.commits == 0
    assert db.added == []


def test_peek_raises_when_no_row_matches():
    with pytest.raises(svc.InvalidTokenError):
        peek(FakeDB(result_value=None))


def test_peek_is_a_select_not_an_update():
    db = FakeDB(result_value=USER_ID)
    peek(db)
    sql = str(db.statements[0].compile(dialect=postgresql.dialect())).upper()
    assert sql.lstrip().startswith("SELECT")
    assert "UPDATE" not in sql


def test_peek_sends_the_hash_the_purpose_and_the_clock():
    db = FakeDB(result_value=USER_ID)
    peek(db, raw="the-raw-token", purpose=TokenPurpose.RESET_PASSWORD)
    params = params_of(db.statements[0])
    assert hash_token("the-raw-token") in params
    assert "the-raw-token" not in params
    assert "reset_password" in params
    assert NOW in params