# tests/services/test_sentence_import_schemas.py
import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.sentence import SentenceCreate, SentenceUpdate
from app.schemas.sentence_import import (
    ImportConfirmIn,
    ImportConfirmRow,
    ImportPreviewOut,
    PreviewRow,
)
from app.services.bulk_tagging_logic import MAX_GRAMMAR_TAG_LEN


def _row(**overrides):
    data = {"de": "Hallo", "en": "Hi"}
    data.update(overrides)
    return data


def _caps(model, field):
    metadata = model.model_fields[field].metadata
    return [m.max_length for m in metadata if hasattr(m, "max_length")]


def test_whitespace_is_stripped():
    row = ImportConfirmRow(**_row(de="  Hallo ", en=" Hi  "))
    assert (row.de, row.en) == ("Hallo", "Hi")


def test_blank_de_is_rejected_after_stripping():
    with pytest.raises(ValidationError):
        ImportConfirmRow(**_row(de="   "))


def test_blank_en_is_rejected_after_stripping():
    with pytest.raises(ValidationError):
        ImportConfirmRow(**_row(en="   "))


def test_de_cap_is_inclusive():
    ImportConfirmRow(**_row(de="a" * 2000))
    with pytest.raises(ValidationError):
        ImportConfirmRow(**_row(de="a" * 2001))


def test_en_over_the_cap_is_rejected():
    with pytest.raises(ValidationError):
        ImportConfirmRow(**_row(en="a" * 2001))


def test_unknown_topic_is_rejected():
    with pytest.raises(ValidationError):
        ImportConfirmRow(**_row(topics=["nonsense"]))


def test_topics_default_to_empty_and_accept_known_values():
    assert ImportConfirmRow(**_row()).topics == []
    assert ImportConfirmRow(**_row(topics=["weather"])).topics[0].value == "weather"


def test_blank_grammar_tag_becomes_none():
    assert ImportConfirmRow(**_row(grammar_tag="   ")).grammar_tag is None
    assert ImportConfirmRow(**_row(grammar_tag="")).grammar_tag is None


def test_grammar_tag_is_trimmed_and_capped():
    assert ImportConfirmRow(**_row(grammar_tag=" perfekt ")).grammar_tag == "perfekt"
    with pytest.raises(ValidationError):
        ImportConfirmRow(**_row(grammar_tag="a" * (MAX_GRAMMAR_TAG_LEN + 1)))


def test_grammar_tag_cap_matches_the_rest_of_the_app():
    assert _caps(ImportConfirmRow, "grammar_tag") == [MAX_GRAMMAR_TAG_LEN]
    assert _caps(SentenceUpdate, "grammar_tag") == [MAX_GRAMMAR_TAG_LEN]


def test_sentence_length_cap_matches_sentence_create():
    for field in ("de", "en"):
        assert _caps(ImportConfirmRow, field) == _caps(SentenceCreate, field)


def test_confirm_needs_at_least_one_sentence():
    with pytest.raises(ValidationError):
        ImportConfirmIn(sentences=[])


def test_confirm_row_limit_comes_from_settings():
    limit = settings.bulk_import_max_rows
    ImportConfirmIn(sentences=[_row()] * limit)
    with pytest.raises(ValidationError):
        ImportConfirmIn(sentences=[_row()] * (limit + 1))


def test_preview_out_serializes_a_row():
    row = PreviewRow(
        row_number=2, de="Hallo", en="Hi", topics=["weather"], grammar_tag=None,
        tagged=True, issues=[], has_blocking_issue=False,
    )
    dumped = ImportPreviewOut(rows=[row]).model_dump()
    assert dumped["rows"][0]["row_number"] == 2
    assert dumped["rows"][0]["tagged"] is True
