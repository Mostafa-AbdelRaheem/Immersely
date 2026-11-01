# tests/services/test_article_logic.py
import uuid

from app.schemas.article_generation import ArticleOutput
from app.services.article_logic import verify_article

MIN_CHARS = 100
MAX_CHARS = 200


def _ids(n: int) -> list[uuid.UUID]:
    return [uuid.uuid4() for _ in range(n)]


def _article(ids, *, title="Titel", text_de=None, text_en="English text", used=None):
    return ArticleOutput(
        title=title,
        text_de=text_de if text_de is not None else "x" * 150,
        text_en=text_en,
        used_sentence_ids=[str(i) for i in (ids if used is None else used)],
    )


def _verify(output, ids):
    return verify_article(output, ids, MIN_CHARS, MAX_CHARS)


def test_valid_article_passes():
    ids = _ids(3)
    assert _verify(_article(ids), ids) is None


def test_too_short_fails():
    ids = _ids(2)
    reason = _verify(_article(ids, text_de="x" * 99), ids)
    assert reason is not None and "too short" in reason


def test_too_long_fails():
    ids = _ids(2)
    reason = _verify(_article(ids, text_de="x" * 201), ids)
    assert reason is not None and "too long" in reason


def test_length_boundaries_are_inclusive():
    ids = _ids(1)
    assert _verify(_article(ids, text_de="x" * MIN_CHARS), ids) is None
    assert _verify(_article(ids, text_de="x" * MAX_CHARS), ids) is None


def test_invented_id_fails():
    ids = _ids(2)
    stranger = uuid.uuid4()
    reason = _verify(_article(ids, used=[*ids, stranger]), ids)
    assert reason is not None and "invented" in reason


def test_missing_id_fails():
    ids = _ids(3)
    reason = _verify(_article(ids, used=ids[:2]), ids)
    assert reason is not None and "missing" in reason


def test_empty_title_fails():
    ids = _ids(1)
    reason = _verify(_article(ids, title="   "), ids)
    assert reason == "empty title"


def test_surrounding_whitespace_does_not_count_toward_length():
    ids = _ids(1)
    padded = "\n\n" + "x" * 99 + "   \n"  # 99 real chars, 106 raw
    reason = _verify(_article(ids, text_de=padded), ids)
    assert reason is not None and "too short" in reason