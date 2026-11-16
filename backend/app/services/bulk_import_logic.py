# app/services/bulk_import_logic.py
"""Pure logic for bulk sentence import (N5c).

No DB, no LLM, no HTTP, no openpyxl: plain Python in, plain Python out, so
every rule here is cheap to unit-test.
"""
import re
import unicodedata

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