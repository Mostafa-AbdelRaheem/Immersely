import pytest

from app.services.password_policy import (
    PasswordProblem,
    check_password,
    normalize_password,
)

EMAIL = "mostafa@example.com"
MIN = 8
MAX_BYTES = 72


def problems(
    password: str,
    email: str = EMAIL,
    min_length: int = MIN,
    max_bytes: int = MAX_BYTES,
):
    return check_password(
        password, email=email, min_length=min_length, max_bytes=max_bytes
    )

def test_accepts_password_at_exact_min_length():
    assert problems("x" * MIN) == []


def test_rejects_one_below_min_length():
    assert problems("x" * (MIN - 1)) == [PasswordProblem.TOO_SHORT]


def test_no_composition_rules():
    # NIST: no "must contain a digit/symbol/uppercase". All lowercase passes.
    assert problems("abcdefgh") == []


def test_spaces_are_kept_not_trimmed():
    assert problems("correct horse battery staple") == []


@pytest.mark.parametrize(
    "password",
    [
        "mostafa@example.com",  # the whole email
        "mostafa",  # the local part (below MIN, so also too_short; see next test)
        "MoStAfA@Example.COM",  # case-insensitive
    ],
)
def test_rejects_email_or_local_part(password):
    assert PasswordProblem.SAME_AS_EMAIL in problems(password, min_length=1)


def test_substring_of_email_is_allowed():
    # NIST compares the WHOLE password, not substrings.
    assert problems("mostafa-learns-german") == []


def test_reports_all_problems_at_once():
    assert problems("MOSTAFA") == [
        PasswordProblem.TOO_SHORT,
        PasswordProblem.SAME_AS_EMAIL,
    ]


def test_casefold_handles_german_eszett():
    # "straße".casefold() == "strasse", so these must match.
    assert PasswordProblem.SAME_AS_EMAIL in problems(
        "STRASSE", email="straße@example.com", min_length=1
    )


def test_length_counts_characters_not_bytes():
    # 8 characters, 15 bytes in UTF-8: must pass an 8-character minimum.
    assert problems("ÄÖÜäöüß!") == []


def test_accepts_exactly_the_byte_limit():
    assert problems("a" * MAX_BYTES) == []


def test_rejects_one_byte_over_the_limit():
    assert problems("a" * (MAX_BYTES + 1)) == [PasswordProblem.TOO_LONG]


def test_limit_counts_bytes_not_characters():
    # "ü" is 2 bytes: exactly MAX_BYTES // 2 of them fit, one more does not,
    # even though that is far below MAX_BYTES *characters*.
    assert problems("ü" * (MAX_BYTES // 2)) == []
    assert problems("ü" * (MAX_BYTES // 2 + 1)) == [PasswordProblem.TOO_LONG]


def test_the_limit_is_the_injected_parameter():
    assert problems("a" * 11, max_bytes=10) == [PasswordProblem.TOO_LONG]
    assert problems("a" * 10, max_bytes=10) == []


COMPOSED = "\u00fc"  # "ü" as a single code point
DECOMPOSED = "u\u0308"  # "u" + combining diaeresis: looks identical, different bytes


def test_normalize_makes_composed_and_decomposed_equal():
    assert normalize_password("Gr" + DECOMPOSED + "n") == normalize_password(
        "Gr" + COMPOSED + "n"
    )


def test_normalize_produces_the_composed_form():
    assert normalize_password(DECOMPOSED) == COMPOSED


def test_ascii_is_unchanged():
    assert normalize_password("correct horse battery staple 123!") == (
        "correct horse battery staple 123!"
    )


def test_already_composed_text_is_unchanged():
    assert normalize_password("Straße über Ärger") == "Straße über Ärger"


def test_whitespace_is_not_trimmed():
    assert normalize_password("  spaced  ") == "  spaced  "


def test_compatibility_characters_are_not_folded():
    # NFKC would turn fullwidth "Ａ" into "A" and the "ﬁ" ligature into "fi";
    # NFC must leave both alone.
    assert normalize_password("\uff21") == "\uff21"
    assert normalize_password("\ufb01") == "\ufb01"


def test_normalizing_twice_changes_nothing():
    once = normalize_password(DECOMPOSED)
    assert normalize_password(once) == once


def test_length_is_judged_after_normalizing():
    # 30 decomposed "ü" = 90 bytes as typed (over the limit), but only 60
    # bytes once composed: the check must run on the normalized form.
    typed = DECOMPOSED * 30
    assert problems(typed) == [PasswordProblem.TOO_LONG]
    assert problems(normalize_password(typed)) == []