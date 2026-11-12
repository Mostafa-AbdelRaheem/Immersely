import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects import postgresql

from app.services.sessions import revoke_user_refresh_tokens

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
USER_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


class FakeResult:
    def __init__(self, rowcount):
        self.rowcount = rowcount


class FakeDB:
    def __init__(self, rowcount=0):
        self.rowcount = rowcount
        self.statements = []
        self.commits = 0

    async def execute(self, stmt):
        self.statements.append(stmt)
        return FakeResult(self.rowcount)

    async def commit(self):
        self.commits += 1


def revoke(db, **kwargs):
    return asyncio.run(revoke_user_refresh_tokens(db, USER_ID, now=NOW, **kwargs))


def test_revokes_only_this_users_unrevoked_tokens():
    db = FakeDB(rowcount=2)
    revoke(db)
    compiled = db.statements[0].compile(dialect=postgresql.dialect())
    assert "revoked_at IS NULL" in str(compiled)
    assert USER_ID in compiled.params.values()
    assert NOW in compiled.params.values()


def test_commits_by_default():
    db = FakeDB()
    revoke(db)
    assert db.commits == 1


def test_can_leave_the_commit_to_the_caller():
    db = FakeDB()
    revoke(db, commit=False)
    assert db.commits == 0


def test_returns_how_many_tokens_were_revoked():
    assert revoke(FakeDB(rowcount=3)) == 3
    assert revoke(FakeDB(rowcount=0)) == 0


def test_can_spare_one_token_by_hash():
    db = FakeDB(rowcount=1)
    revoke(db, except_token_hash="keep-me-hash")
    compiled = db.statements[0].compile(dialect=postgresql.dialect())
    assert "token_hash !=" in str(compiled)
    assert "keep-me-hash" in compiled.params.values()


def test_no_exception_clause_when_no_hash_is_given():
    db = FakeDB()
    revoke(db)
    compiled = db.statements[0].compile(dialect=postgresql.dialect())
    assert "token_hash" not in str(compiled)