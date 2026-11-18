# tests/services/test_confirm_import.py
import asyncio
import uuid

import pytest

from app.schemas.sentence_import import ImportConfirmRow
from app.services.sentence_import import confirm_import


class FakeSession:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add_all(self, items):
        self.added.extend(items)

    async def commit(self):
        self.commits += 1


class FakeEmbed:
    """Row i gets vector [i, i, ...] so a wrong pairing is visible."""

    def __init__(self, short_by=0):
        self.calls = []
        self.short_by = short_by

    async def __call__(self, texts):
        self.calls.append(list(texts))
        return [[float(i)] * 3 for i in range(len(texts) - self.short_by)]


class FailingEmbed:
    async def __call__(self, texts):
        raise RuntimeError("model exploded")


def _rows():
    return [
        ImportConfirmRow(de="Hallo Welt", en="Hello world", topics=["weather"], grammar_tag="greeting"),
        ImportConfirmRow(de="Guten Morgen", en="Good morning"),
    ]


def test_embeds_once_in_file_order_and_commits_once():
    db, embed, user_id = FakeSession(), FakeEmbed(), uuid.uuid4()
    result = asyncio.run(confirm_import(db, user_id, _rows(), embed_fn=embed))
    assert embed.calls == [["Hallo Welt", "Guten Morgen"]]
    assert db.commits == 1
    assert db.added == result
    assert [s.de for s in result] == ["Hallo Welt", "Guten Morgen"]


def test_fields_and_vectors_are_paired_per_row():
    db, user_id = FakeSession(), uuid.uuid4()
    result = asyncio.run(confirm_import(db, user_id, _rows(), embed_fn=FakeEmbed()))
    first, second = result
    assert first.user_id == user_id and second.user_id == user_id
    assert first.en == "Hello world"
    assert first.topics == ["weather"]
    assert first.grammar_tag == "greeting"
    assert first.embedding == [0.0] * 3
    assert second.topics == [] and second.grammar_tag is None
    assert second.embedding == [1.0] * 3


def test_embed_failure_leaves_session_untouched():
    db = FakeSession()
    with pytest.raises(RuntimeError):
        asyncio.run(confirm_import(db, uuid.uuid4(), _rows(), embed_fn=FailingEmbed()))
    assert db.added == [] and db.commits == 0


def test_vector_count_mismatch_raises_and_commits_nothing():
    db = FakeSession()
    with pytest.raises(ValueError):
        asyncio.run(confirm_import(db, uuid.uuid4(), _rows(), embed_fn=FakeEmbed(short_by=1)))
    assert db.added == [] and db.commits == 0
