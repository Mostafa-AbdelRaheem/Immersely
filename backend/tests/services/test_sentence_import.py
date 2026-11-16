# tests/services/test_sentence_import.py
import asyncio
import io

import pytest
from openpyxl import Workbook

from app.core.config import settings
from app.schemas.bulk_tagging import BatchTagItem, BatchTaggingResult
from app.schemas.sentence import SentenceCreate
from app.services.bulk_import_logic import MissingColumnsError, TooManyRowsError, normalize_for_dedupe
from app.services.bulk_import_reader import InvalidSpreadsheetError
from app.services.bulk_tagging import MAX_ATTEMPTS_PER_CHUNK
from app.services.sentence_import import MAX_TEXT_LEN, build_preview


class MappedTagger:
    """Fake chain: tags each text by lookup, so a wrong row mapping shows up."""

    def __init__(self, topic_by_text=None, grammar_tag=None):
        self.topic_by_text = topic_by_text or {}
        self.grammar_tag = grammar_tag
        self.calls = []

    async def __call__(self, items):
        self.calls.append(list(items))
        return BatchTaggingResult(
            items=[
                BatchTagItem(
                    index=label,
                    topics=[self.topic_by_text.get(text, "weather")],
                    grammar_tag=self.grammar_tag,
                )
                for label, text in items
            ]
        )


class SilentTagger:
    """Fake chain that never returns any item (every attempt is a miss)."""

    def __init__(self):
        self.calls = []

    async def __call__(self, items):
        self.calls.append(list(items))
        return BatchTaggingResult(items=[])


def _xlsx(rows):
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _preview(rows, tagger, existing=frozenset()):
    return asyncio.run(build_preview(_xlsx(rows), existing_keys=existing, tag_fn=tagger))


def test_happy_path_returns_tagged_rows_with_real_row_numbers():
    out = _preview([["de", "en"], ["Hallo", "Hi"], ["Welt", "World"]], MappedTagger())
    assert [r.row_number for r in out.rows] == [2, 3]
    assert all(r.tagged and r.topics == ["weather"] and r.issues == [] for r in out.rows)
    assert not any(r.has_blocking_issue for r in out.rows)


def test_blocking_rows_are_not_sent_to_the_tagger():
    tagger = MappedTagger()
    out = _preview([["de", "en"], ["Hallo", "Hi"], ["", "x"]], tagger)
    assert tagger.calls == [[(1, "Hallo")]]
    blocked = out.rows[1]
    assert (blocked.tagged, blocked.topics, blocked.has_blocking_issue) == (False, [], True)
    assert blocked.issues == ["empty_de"]


def test_duplicate_rows_are_still_tagged():
    tagger = MappedTagger()
    out = _preview([["de", "en"], ["Hallo", "a"], ["hallo", "b"]], tagger)
    assert len(tagger.calls[0]) == 2
    assert out.rows[1].issues == ["duplicate_in_file"]
    assert out.rows[1].tagged and not out.rows[1].has_blocking_issue


def test_duplicate_of_existing_sentence_is_flagged():
    existing = {normalize_for_dedupe("Hallo")}
    out = _preview([["de", "en"], ["HALLO", "Hi"]], MappedTagger(), existing)
    assert out.rows[0].issues == ["duplicate_existing"]
    assert out.rows[0].tagged


def test_tagging_failure_gives_untagged_row_not_an_error():
    tagger = SilentTagger()
    out = _preview([["de", "en"], ["Hallo", "Hi"]], tagger)
    assert len(tagger.calls) == MAX_ATTEMPTS_PER_CHUNK
    row = out.rows[0]
    assert (row.tagged, row.topics, row.grammar_tag) == (False, [], None)
    assert (row.de, row.en) == ("Hallo", "Hi")


def test_grammar_tag_is_passed_through():
    out = _preview([["de", "en"], ["Hallo", "Hi"]], MappedTagger(grammar_tag="perfekt"))
    assert out.rows[0].grammar_tag == "perfekt"


def test_tags_map_to_the_right_rows_when_a_blocked_row_is_in_the_middle():
    tagger = MappedTagger({"Hallo": "weather", "Welt": "housing"})
    out = _preview([["de", "en"], ["Hallo", "a"], ["", "b"], ["Welt", "c"]], tagger)
    assert [r.row_number for r in out.rows] == [2, 3, 4]
    assert [r.tagged for r in out.rows] == [True, False, True]
    assert out.rows[0].topics == ["weather"]
    assert out.rows[2].topics == ["housing"]


def test_over_long_cell_is_blocking_and_untagged():
    tagger = MappedTagger()
    out = _preview([["de", "en"], ["a" * (MAX_TEXT_LEN + 1), "x"]], tagger)
    assert tagger.calls == []
    assert out.rows[0].issues == ["too_long_de"]
    assert out.rows[0].has_blocking_issue and not out.rows[0].tagged


def test_header_only_file_returns_no_rows_and_makes_no_calls():
    tagger = MappedTagger()
    assert _preview([["de", "en"]], tagger).rows == []
    assert tagger.calls == []


def test_missing_column_propagates():
    with pytest.raises(MissingColumnsError) as exc:
        _preview([["de", "other"], ["Hallo", "x"]], MappedTagger())
    assert exc.value.missing == ["en"]


def test_too_many_rows_propagates(monkeypatch):
    monkeypatch.setattr(settings, "bulk_import_max_rows", 2)
    rows = [["de", "en"], ["a", "1"], ["b", "2"], ["c", "3"]]
    with pytest.raises(TooManyRowsError):
        _preview(rows, MappedTagger())


def test_non_xlsx_propagates():
    with pytest.raises(InvalidSpreadsheetError) as exc:
        asyncio.run(build_preview(b"nope", existing_keys=frozenset(), tag_fn=MappedTagger()))
    assert exc.value.code == "unreadable"


def test_upload_over_the_limit_propagates(monkeypatch):
    monkeypatch.setattr(settings, "bulk_import_max_upload_bytes", 10)
    with pytest.raises(InvalidSpreadsheetError) as exc:
        _preview([["de", "en"], ["Hallo", "Hi"]], MappedTagger())
    assert exc.value.code == "too_large"


def test_max_text_len_matches_sentence_create():
    for field in ("de", "en"):
        metadata = SentenceCreate.model_fields[field].metadata
        caps = [m.max_length for m in metadata if hasattr(m, "max_length")]
        assert caps == [MAX_TEXT_LEN]
