# app/services/bulk_import_reader.py
"""Read an uploaded .xlsx into raw row tuples for parse_rows (N5c).

This is the only place untrusted binary data is parsed, so it is defensive:
size checks run before openpyxl opens anything, the sheet is streamed
(read_only) and formulas are never evaluated (data_only). The code is
blocking: async routes should call it through asyncio.to_thread.
"""
import io
import zipfile
from collections.abc import Iterable, Sequence
from typing import Any

from openpyxl import load_workbook

# Safety valves against hostile files (not tunable settings). The user-facing
# row limit is Settings.bulk_import_max_rows, applied later by parse_rows.
MAX_UNCOMPRESSED_BYTES = 20_000_000
MAX_SCANNED_ROWS = 5_000
MAX_CONSECUTIVE_BLANK_ROWS = 100


class InvalidSpreadsheetError(Exception):
    """Not a readable, acceptable .xlsx. Carries a short code, never parser text."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _is_blank_row(row: Sequence[Any]) -> bool:
    return all(
        cell is None or (isinstance(cell, str) and not cell.strip()) for cell in row
    )


def _collect_rows(
    rows: Iterable[Sequence[Any]], *, max_rows: int, max_blank_run: int
) -> list[Sequence[Any]]:
    """Materialize rows, bounded. Blank rows are kept so row numbers stay real;
    a long run of blank rows is treated as the end of the data."""
    collected: list[Sequence[Any]] = []
    blank_run = 0
    for row in rows:
        if len(collected) >= max_rows:
            raise InvalidSpreadsheetError("sheet_too_long")
        collected.append(row)
        if _is_blank_row(row):
            blank_run += 1
            if blank_run >= max_blank_run:
                break
        else:
            blank_run = 0
    return collected


def read_xlsx_rows(data: bytes, *, max_upload_bytes: int) -> list[Sequence[Any]]:
    """First sheet of an .xlsx as raw row tuples (header row included)."""
    if len(data) > max_upload_bytes:
        raise InvalidSpreadsheetError("too_large")

    # Read the zip's table of contents only (nothing is extracted).
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            declared_total = sum(entry.file_size for entry in archive.infolist())
    except zipfile.BadZipFile:
        raise InvalidSpreadsheetError("unreadable") from None
    if declared_total > MAX_UNCOMPRESSED_BYTES:
        raise InvalidSpreadsheetError("too_large")

    workbook = None
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        sheet = workbook.worksheets[0]
        return _collect_rows(
            sheet.iter_rows(values_only=True),
            max_rows=MAX_SCANNED_ROWS,
            max_blank_run=MAX_CONSECUTIVE_BLANK_ROWS,
        )
    except InvalidSpreadsheetError:
        raise
    except Exception:
        # openpyxl raises many types for bad files; never surface its text.
        raise InvalidSpreadsheetError("unreadable") from None
    finally:
        if workbook is not None:
            workbook.close()
