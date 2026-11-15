import re

import pytest

from app.services.breach_logic import count_in_range_response, sha1_prefix_suffix

# SHA-1("password") = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
SUFFIX = "1E4C9B93F3F0682250B6CF8331B7EE68FD8"


def test_known_vector_splits_into_prefix_and_suffix():
    assert sha1_prefix_suffix("password") == ("5BAA6", SUFFIX)


def test_prefix_and_suffix_are_uppercase_hex_of_right_length():
    prefix, suffix = sha1_prefix_suffix("any password at all")
    assert re.fullmatch(r"[0-9A-F]{5}", prefix)
    assert re.fullmatch(r"[0-9A-F]{35}", suffix)


def test_unicode_encodings_hash_differently_without_normalization():
    # Documents current behavior: "ü" composed vs "u" + combining diaeresis
    # are different byte strings. Normalization must happen BEFORE this call.
    assert sha1_prefix_suffix("\u00fc") != sha1_prefix_suffix("u\u0308")


def test_hit_returns_its_count():
    body = f"0018A45C4D1DEF81644B54AB7F969B88D65:1\r\n{SUFFIX}:3"
    assert count_in_range_response(body, SUFFIX) == 3


def test_padded_zero_count_entry_reads_as_not_found():
    assert count_in_range_response(f"{SUFFIX}:0", SUFFIX) == 0


def test_absent_suffix_returns_zero():
    assert count_in_range_response("0018A45C4D1DEF81644B54AB7F969B88D65:1", SUFFIX) == 0


def test_match_is_case_insensitive():
    assert count_in_range_response(f"{SUFFIX}:5", SUFFIX.lower()) == 5


@pytest.mark.parametrize("newline", ["\r\n", "\n"])
def test_handles_both_line_endings(newline):
    body = f"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:1{newline}{SUFFIX}:9{newline}"
    assert count_in_range_response(body, SUFFIX) == 9


def test_malformed_line_is_skipped_and_a_later_valid_one_still_found():
    body = f"not a valid line\n{SUFFIX}:oops\n{SUFFIX}:7"
    assert count_in_range_response(body, SUFFIX) == 7


def test_non_integer_count_alone_returns_zero():
    assert count_in_range_response(f"{SUFFIX}:oops", SUFFIX) == 0


def test_empty_body_returns_zero():
    assert count_in_range_response("", SUFFIX) == 0