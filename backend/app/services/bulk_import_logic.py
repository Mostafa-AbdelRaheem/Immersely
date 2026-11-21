# app/services/bulk_import_logic.py
"""Pure logic for bulk sentence import (N5c).

No DB, no LLM, no HTTP, no openpyxl: plain Python in, plain Python out, so
every rule here is cheap to unit-test.
"""
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

# Format invariants (not tunable settings): the template builder and the
# parser both import these, so the two can never drift apart.
HEADER_DE = "de"
HEADER_EN = "en"

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_for_dedupe(text: str) -> str:
    """Key used to decide whether two sentences are 'the same'.

    NFC -> collapse whitespace -> trim -> casefold. Punctuation is kept on
    purpose. casefold() maps 'ß' to 'ss', so 'Straße' and 'Strasse' match.
    """
    composed = unicodedata.normalize("NFC", text)
    collapsed = _WHITESPACE_RE.sub(" ", composed).strip()
    return collapsed.casefold()


# Issue codes attached to a parsed row. Blocking ones mean the row cannot be
# saved as it stands (the user must fix or remove it). Duplicates are only
# warnings, because keeping a duplicate on purpose is a legitimate choice.
ISSUE_EMPTY_DE = "empty_de"
ISSUE_EMPTY_EN = "empty_en"
ISSUE_TOO_LONG_DE = "too_long_de"
ISSUE_TOO_LONG_EN = "too_long_en"
ISSUE_DUPLICATE_IN_FILE = "duplicate_in_file"
ISSUE_DUPLICATE_EXISTING = "duplicate_existing"

BLOCKING_ISSUES = frozenset(
    {ISSUE_EMPTY_DE, ISSUE_EMPTY_EN, ISSUE_TOO_LONG_DE, ISSUE_TOO_LONG_EN}
)


class MissingColumnsError(Exception):
    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"Missing required column(s): {', '.join(missing)}")
        self.missing = missing


class TooManyRowsError(Exception):
    def __init__(self, count: int, limit: int) -> None:
        super().__init__(f"{count} rows exceeds the limit of {limit}")
        self.count = count
        self.limit = limit


@dataclass(frozen=True)
class ParsedRow:
    row_number: int  # the real spreadsheet row (header is row 1)
    de: str
    en: str
    issues: tuple[str, ...]

    @property
    def has_blocking_issue(self) -> bool:
        return any(code in BLOCKING_ISSUES for code in self.issues)


def _cell_text(value: Any) -> str:
    """Blank cell -> '', anything else -> str(value).strip()."""
    if value is None:
        return ""
    return str(value).strip()


def _find_column(header: Sequence[Any], name: str) -> int | None:
    for index, cell in enumerate(header):
        if _cell_text(cell).casefold() == name:
            return index
    return None


def _cell_at(row: Sequence[Any], index: int) -> str:
    # Read-only sheets can return short rows: a missing cell counts as blank.
    return _cell_text(row[index]) if index < len(row) else ""


def parse_rows(
    raw_rows: Sequence[Sequence[Any]],
    *,
    max_rows: int,
    max_len: int,
    existing_keys: set[str] | frozenset[str],
) -> list[ParsedRow]:
    """Turn raw spreadsheet rows (header first) into ParsedRows with issues.

    existing_keys holds normalize_for_dedupe() keys of the user's saved
    sentences; the caller builds it, so this function never touches the DB.
    """
    if not raw_rows:
        raise MissingColumnsError([HEADER_DE, HEADER_EN])

    header = raw_rows[0]
    de_col = _find_column(header, HEADER_DE)
    en_col = _find_column(header, HEADER_EN)
    missing = [
        name
        for name, col in ((HEADER_DE, de_col), (HEADER_EN, en_col))
        if col is None
    ]
    if missing:
        raise MissingColumnsError(missing)

    # Pass 1: keep rows with text in at least one of our two columns, each
    # with its real spreadsheet row number (header is row 1, data starts at 2).
    kept: list[tuple[int, str, str]] = []
    for row_number, row in enumerate(raw_rows[1:], start=2):
        de = _cell_at(row, de_col)
        en = _cell_at(row, en_col)
        if de or en:
            kept.append((row_number, de, en))

    if len(kept) > max_rows:
        raise TooManyRowsError(len(kept), max_rows)

    # Pass 2: attach issues. The first copy of a sentence stays clean.
    seen: set[str] = set()
    parsed: list[ParsedRow] = []
    for row_number, de, en in kept:
        issues: list[str] = []
        if not de:
            issues.append(ISSUE_EMPTY_DE)
        elif len(de) > max_len:
            issues.append(ISSUE_TOO_LONG_DE)
        if not en:
            issues.append(ISSUE_EMPTY_EN)
        elif len(en) > max_len:
            issues.append(ISSUE_TOO_LONG_EN)
        if de:
            key = normalize_for_dedupe(de)
            if key in seen:
                issues.append(ISSUE_DUPLICATE_IN_FILE)
            else:
                seen.add(key)
            if key in existing_keys:
                issues.append(ISSUE_DUPLICATE_EXISTING)
        parsed.append(ParsedRow(row_number, de, en, tuple(issues)))
    return parsed