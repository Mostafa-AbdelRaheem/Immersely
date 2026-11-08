import pytest

from app.services.password_policy import PasswordProblem, check_password

EMAIL = "mostafa@example.com"
MIN = 8


def problems(password: str, email: str = EMAIL, min_length: int = MIN):
    return check_password(password, email=email, min_length=min_length)


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