# tests/services/test_bulk_tagging.py
import asyncio
import logging

import pytest

from app.core.config import settings
from app.schemas.bulk_tagging import BatchTagItem, BatchTaggingResult
from app.services.bulk_tagging import MAX_ATTEMPTS_PER_CHUNK, tag_sentences


class ScriptedTagger:
    """Fake chain: each call consumes the next scripted reply."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def __call__(self, items):
        self.calls.append(list(items))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return BatchTaggingResult(items=reply)


def _item(index, topic="weather", tag=None):
    return BatchTagItem(index=index, topics=[topic], grammar_tag=tag)


def _run(texts, replies, chunk_size=None):
    fake = ScriptedTagger(replies)
    out = asyncio.run(tag_sentences(texts, chunk_size=chunk_size, tag_fn=fake))
    return out, fake


def test_all_good_on_first_try():
    out, fake = _run(["a", "b", "c"], [[_item(1), _item(2), _item(3)]])
    assert len(out) == 3 and all(o is not None for o in out)
    assert len(fake.calls) == 1


def test_empty_input_makes_no_calls():
    out, fake = _run([], [])
    assert out == [] and fake.calls == []


def test_chunks_restart_labels_and_keep_order():
    replies = [
        [_item(1, "weather"), _item(2, "housing")],
        [_item(1, "shopping"), _item(2, "education")],
        [_item(1, "work_and_career")],
    ]
    out, fake = _run(["a", "b", "c", "d", "e"], replies, chunk_size=2)
    assert fake.calls == [
        [(1, "a"), (2, "b")],
        [(1, "c"), (2, "d")],
        [(1, "e")],
    ]
    assert [o.topics[0] for o in out] == [
        "weather", "housing", "shopping", "education", "work_and_career",
    ]


def test_missing_label_is_retried_alone():
    out, fake = _run(["a", "b", "c"], [[_item(1), _item(3)], [_item(2)]])
    assert all(o is not None for o in out)
    assert fake.calls[1] == [(2, "b")]


def test_duplicate_label_is_retried():
    replies = [[_item(1), _item(2), _item(2, "housing")], [_item(2), _item(3)]]
    out, fake = _run(["a", "b", "c"], replies)
    assert all(o is not None for o in out)
    assert fake.calls[1] == [(2, "b"), (3, "c")]


def test_exception_then_success():
    out, fake = _run(["a"], [RuntimeError("boom"), [_item(1)]])
    assert out[0] is not None
    assert fake.calls[0] == fake.calls[1] == [(1, "a")]


def test_gives_up_after_max_attempts():
    out, fake = _run(["a"], [[]] * MAX_ATTEMPTS_PER_CHUNK)
    assert out == [None]
    assert len(fake.calls) == MAX_ATTEMPTS_PER_CHUNK


def test_every_attempt_raising_returns_none_without_raising():
    out, fake = _run(["a"], [RuntimeError("x")] * MAX_ATTEMPTS_PER_CHUNK)
    assert out == [None]
    assert len(fake.calls) == MAX_ATTEMPTS_PER_CHUNK


def test_failed_chunk_does_not_stop_later_chunks():
    replies = [[]] * MAX_ATTEMPTS_PER_CHUNK + [[_item(1)]]
    out, _ = _run(["a", "b", "c"], replies, chunk_size=2)
    assert out[0] is None and out[1] is None
    assert out[2] is not None


def test_partial_result_is_kept_when_retries_run_out():
    replies = [[_item(1)]] + [[]] * (MAX_ATTEMPTS_PER_CHUNK - 1)
    out, fake = _run(["a", "b"], replies)
    assert out[0] is not None and out[1] is None
    assert fake.calls[1] == [(2, "b")]


def test_label_accepted_earlier_is_not_overwritten_by_a_retry():
    replies = [[_item(1, "weather")], [_item(1, "housing"), _item(2, "shopping")]]
    out, fake = _run(["a", "b"], replies)
    assert out[0].topics == ("weather",)
    assert out[1].topics == ("shopping",)
    assert fake.calls[1] == [(2, "b")]


def test_chunk_size_below_one_is_rejected():
    with pytest.raises(ValueError):
        _run(["a"], [], chunk_size=0)


def test_default_chunk_size_comes_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "bulk_tag_chunk_size", 2)
    replies = [[_item(1), _item(2)], [_item(1)]]
    out, fake = _run(["a", "b", "c"], replies)
    assert len(fake.calls) == 2
    assert all(o is not None for o in out)


def test_log_names_the_error_type_but_never_the_sentence_text(caplog):
    caplog.set_level(logging.WARNING)
    out, _ = _run(["geheimer Satz"], [ValueError("x")] * MAX_ATTEMPTS_PER_CHUNK)
    assert out == [None]
    assert "ValueError" in caplog.text
    assert "geheimer Satz" not in caplog.text
