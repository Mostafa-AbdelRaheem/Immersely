# tests/services/test_bulk_import_parse_rows.py
import pytest

from app.services.bulk_import_logic import (
    ISSUE_DUPLICATE_EXISTING,
    ISSUE_DUPLICATE_IN_FILE,
    ISSUE_EMPTY_DE,
    ISSUE_EMPTY_EN,
    ISSUE_TOO_LONG_DE,
    ISSUE_TOO_LONG_EN,
    MissingColumnsError,
    TooManyRowsError,
    normalize_for_dedupe,
    parse_rows,
)

HEADER = ("de", "en")


def _parse(rows, *, max_rows=100, max_len=2000, existing=frozenset()):
    return parse_rows(rows, max_rows=max_rows, max_len=max_len, existing_keys=existing)


def test_finds_columns_case_insensitively_and_ignores_extras():
    rows = [("  EN ", "note", "De"), ("Hi", "x", "Hallo")]
    [row] = _parse(rows)
    assert (row.row_number, row.de, row.en, row.issues) == (2, "Hallo", "Hi", ())


def test_missing_en_header_names_only_en():
    with pytest.raises(MissingColumnsError) as exc:
        _parse([("de", "other")])
    assert exc.value.missing == ["en"]


def test_empty_sheet_reports_both_missing():
    with pytest.raises(MissingColumnsError) as exc:
        _parse([])
    assert exc.value.missing == ["de", "en"]


def test_blank_rows_skipped_and_row_numbers_stay_real():
    rows = [HEADER, ("a", "b"), (None, None), ("  ", ""), ("c", "d")]
    assert [r.row_number for r in _parse(rows)] == [2, 5]


def test_short_row_missing_trailing_cell_is_empty_en():
    [row] = _parse([HEADER, ("Hallo",)])
    assert row.en == ""
    assert row.issues == (ISSUE_EMPTY_EN,)


def test_non_text_cell_becomes_trimmed_string():
    [row] = _parse([HEADER, (2024, " year ")])
    assert (row.de, row.en) == ("2024", "year")


def test_whitespace_only_de_is_blocking_empty_de():
    [row] = _parse([HEADER, ("   ", "Hi")])
    assert row.issues == (ISSUE_EMPTY_DE,)
    assert row.has_blocking_issue


def test_too_long_flags_each_side():
    [row] = _parse([HEADER, ("abcdef", "abcdefg")], max_len=5)
    assert row.issues == (ISSUE_TOO_LONG_DE, ISSUE_TOO_LONG_EN)


def test_length_exactly_at_limit_is_ok():
    [row] = _parse([HEADER, ("abcde", "vwxyz")], max_len=5)
    assert row.issues == ()


def test_first_duplicate_in_file_stays_clean_and_later_is_a_warning():
    rows = [HEADER, ("Ich bin hier", "a"), ("  ich   BIN hier ", "b")]
    first, second = _parse(rows)
    assert first.issues == ()
    assert second.issues == (ISSUE_DUPLICATE_IN_FILE,)
    assert not second.has_blocking_issue


def test_duplicate_of_existing_sentence_is_flagged():
    existing = {normalize_for_dedupe("Ich bin hier")}
    [row] = _parse([HEADER, ("ICH bin hier", "a")], existing=existing)
    assert row.issues == (ISSUE_DUPLICATE_EXISTING,)


def test_both_duplicate_flags_can_apply():
    existing = {normalize_for_dedupe("Hallo")}
    first, second = _parse(
        [HEADER, ("Hallo", "a"), ("hallo", "b")], existing=existing
    )
    assert first.issues == (ISSUE_DUPLICATE_EXISTING,)
    assert second.issues == (ISSUE_DUPLICATE_IN_FILE, ISSUE_DUPLICATE_EXISTING)


def test_too_many_rows_raises_with_count_and_limit():
    rows = [HEADER] + [(f"a{i}", "b") for i in range(3)]
    with pytest.raises(TooManyRowsError) as exc:
        _parse(rows, max_rows=2)
    assert (exc.value.count, exc.value.limit) == (3, 2)


def test_blank_rows_do_not_count_toward_the_row_limit():
    rows = [HEADER, ("x", "y"), (None, None), ("z", "w")]
    assert len(_parse(rows, max_rows=2)) == 2