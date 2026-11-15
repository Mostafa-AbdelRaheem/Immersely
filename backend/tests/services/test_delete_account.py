import asyncio
import uuid
from types import SimpleNamespace

import pytest

import app.services.auth as auth

PASSWORD = "zq7-quiet-Orchid-4821-xylophone-ruminate"


class FakeDB:
    def __init__(self, rowcount=1, commit_error=None):
        self.rowcount = rowcount
        self.commit_error = commit_error
        self.executes = 0
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement):
        self.executes += 1
        return SimpleNamespace(rowcount=self.rowcount)

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
        hashed_password="H:" + PASSWORD,
    )


@pytest.fixture(autouse=True)
def fake_bcrypt(monkeypatch):
    monkeypatch.setattr(auth, "verify_password", lambda p, h: h == "H:" + p)


def delete(db, user, password=PASSWORD):
    return asyncio.run(auth.delete_account(db, user, password))


def test_wrong_password_executes_nothing():
    db = FakeDB()
    with pytest.raises(auth.CurrentPasswordIncorrectError):
        delete(db, make_user(), password="not-the-password")
    assert db.executes == 0
    assert db.commits == 0


def test_success_commits_once_and_addresses_the_notice():
    db = FakeDB()
    notice = delete(db, make_user())
    assert db.executes == 1
    assert db.commits == 1
    assert db.rollbacks == 0
    assert notice.to == "mostafa@example.com"
    assert "Hi Mostafa," in notice.text_body


def test_unexpected_rowcount_rolls_back_and_raises():
    db = FakeDB(rowcount=0)
    with pytest.raises(RuntimeError):
        delete(db, make_user())
    assert db.commits == 0
    assert db.rollbacks == 1


def test_failed_commit_rolls_back_and_propagates():
    db = FakeDB(commit_error=RuntimeError("db down"))
    with pytest.raises(RuntimeError):
        delete(db, make_user())
    assert db.rollbacks == 1