# tests/services/test_bulk_import_logic.py
from app.services.bulk_import_logic import normalize_for_dedupe


def test_trims_and_collapses_spaces():
    assert normalize_for_dedupe("  Ich   bin  hier ") == "ich bin hier"


def test_collapses_tabs_newlines_and_nbsp():
    assert normalize_for_dedupe("a\u00a0b\tc\nd") == "a b c d"


def test_is_case_insensitive():
    assert normalize_for_dedupe("ICH bin") == normalize_for_dedupe("ich BIN")


def test_nfc_composed_and_decomposed_match():
    composed = "\u00fc"  # one code point: u with diaeresis
    decomposed = "u\u0308"  # 'u' plus combining diaeresis
    assert composed != decomposed
    assert normalize_for_dedupe(composed) == normalize_for_dedupe(decomposed)


def test_eszett_and_ss_match():
    # Deliberate: casefold() treats these as the same sentence.
    assert normalize_for_dedupe("Stra\u00dfe") == normalize_for_dedupe("STRASSE")


def test_blank_becomes_empty_string():
    assert normalize_for_dedupe("") == ""
    assert normalize_for_dedupe("   \t\n") == ""


def test_punctuation_stays_significant():
    assert normalize_for_dedupe("Hallo.") != normalize_for_dedupe("Hallo")


def test_different_sentences_differ():
    assert normalize_for_dedupe("Ich bin hier") != normalize_for_dedupe("Ich bin da")