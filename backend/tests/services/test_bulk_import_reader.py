# tests/services/test_bulk_import_reader.py
import io
import zipfile

import pytest
from openpyxl import Workbook

from app.services.bulk_import_reader import (
    MAX_UNCOMPRESSED_BYTES,
    InvalidSpreadsheetError,
    _collect_rows,
    _is_blank_row,
    read_xlsx_rows,
)

LIMIT = 1_000_000


def _save(workbook):
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _xlsx_bytes(rows):
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    return _save(workbook)


def _code_of(callable_):
    with pytest.raises(InvalidSpreadsheetError) as exc:
        callable_()
    return exc.value.code


# --- _collect_rows / _is_blank_row: pure, no files ---


def test_collect_keeps_rows_in_order():
    rows = [("a",), ("b",)]
    assert _collect_rows(rows, max_rows=10, max_blank_run=3) == rows


def test_collect_keeps_blank_rows_in_the_middle():
    rows = [("a",), (None,), ("b",)]
    assert len(_collect_rows(rows, max_rows=10, max_blank_run=3)) == 3


def test_collect_stops_after_a_run_of_blank_rows():
    rows = [("a",)] + [(None,)] * 10 + [("late",)]
    out = _collect_rows(rows, max_rows=100, max_blank_run=3)
    assert out == [("a",), (None,), (None,), (None,)]


def test_collect_blank_run_resets_when_data_appears():
    rows = [(None,), (None,), ("a",), (None,), (None,), ("b",)]
    assert len(_collect_rows(rows, max_rows=100, max_blank_run=3)) == 6


def test_collect_raises_when_over_the_cap():
    rows = [("a",)] * 4
    assert _code_of(lambda: _collect_rows(rows, max_rows=3, max_blank_run=3)) == "sheet_too_long"


def test_collect_exactly_at_the_cap_is_ok():
    rows = [("a",)] * 3
    assert len(_collect_rows(rows, max_rows=3, max_blank_run=3)) == 3


def test_blank_row_rules():
    assert _is_blank_row((None, "  ", ""))
    assert _is_blank_row(())
    assert not _is_blank_row((None, "x"))
    assert not _is_blank_row((0,))


# --- read_xlsx_rows: real .xlsx bytes built in memory ---


def test_round_trip_returns_row_tuples():
    data = _xlsx_bytes([["de", "en"], ["Hallo", "Hi"]])
    assert read_xlsx_rows(data, max_upload_bytes=LIMIT) == [("de", "en"), ("Hallo", "Hi")]


def test_only_the_first_sheet_is_read():
    workbook = Workbook()
    workbook.active.append(["de", "en"])
    workbook.create_sheet("Instructions").append(["ignore", "me"])
    assert read_xlsx_rows(_save(workbook), max_upload_bytes=LIMIT) == [("de", "en")]


def test_number_cells_pass_through_unchanged():
    rows = read_xlsx_rows(_xlsx_bytes([["de", "en"], [2024, "year"]]), max_upload_bytes=LIMIT)
    assert rows[1] == (2024, "year")


def test_formulas_are_never_evaluated():
    rows = read_xlsx_rows(_xlsx_bytes([["de", "en"], ["=1+1", "x"]]), max_upload_bytes=LIMIT)
    assert rows[1][0] in (None, "=1+1")  # never the computed 2


def test_non_zip_bytes_are_unreadable():
    assert _code_of(lambda: read_xlsx_rows(b"not a zip", max_upload_bytes=LIMIT)) == "unreadable"
    assert _code_of(lambda: read_xlsx_rows(b"", max_upload_bytes=LIMIT)) == "unreadable"


def test_a_zip_that_is_not_a_workbook_is_unreadable():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("hello.txt", "hi")
    assert _code_of(lambda: read_xlsx_rows(buffer.getvalue(), max_upload_bytes=LIMIT)) == "unreadable"


def test_over_the_upload_cap_is_too_large():
    data = _xlsx_bytes([["de", "en"]])
    assert _code_of(lambda: read_xlsx_rows(data, max_upload_bytes=10)) == "too_large"


def test_small_upload_that_expands_hugely_is_too_large():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("big.bin", b"\0" * (MAX_UNCOMPRESSED_BYTES + 1))
    data = buffer.getvalue()
    assert len(data) < LIMIT  # passes the upload cap, so the second guard must fire
    assert _code_of(lambda: read_xlsx_rows(data, max_upload_bytes=LIMIT)) == "too_large"
