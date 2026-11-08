import pytest

from app.services.username_policy import (
    UsernameProblem,
    check_username,
    normalize_username,
)

MIN, MAX = 3, 20


def problems(username: str):
    return check_username(username, min_length=MIN, max_length=MAX)


def test_normalize_strips_whitespace_and_lowercases():
    assert normalize_username("  MoStAfA \n") == "mostafa"


def test_accepts_exact_min_and_max_length():
    assert problems("a" * MIN) == []
    assert problems("a" * MAX) == []


def test_rejects_one_below_min():
    assert problems("a" * (MIN - 1)) == [UsernameProblem.TOO_SHORT]


def test_rejects_one_above_max():
    assert problems("a" * (MAX + 1)) == [UsernameProblem.TOO_LONG]


@pytest.mark.parametrize("username", ["mostafa", "user_1", "_x_", "123", "a_b_c"])
def test_accepts_valid_usernames(username):
    assert problems(username) == []


@pytest.mark.parametrize(
    "username",
    ["has space", "dash-ed", "dot.ted", "ümlaut", "name\n", "Upper", "at@sign"],
)
def test_rejects_invalid_characters(username):
    assert problems(username) == [UsernameProblem.INVALID_CHARACTERS]


def test_non_ascii_digits_are_rejected():
    # str.isdigit() / \d would accept these; [0-9] must not.
    assert problems("\u0661\u0662\u0663") == [UsernameProblem.INVALID_CHARACTERS]


def test_empty_string_reports_only_too_short():
    assert problems("") == [UsernameProblem.TOO_SHORT]


def test_reports_all_problems_at_once():
    assert problems("A!") == [
        UsernameProblem.TOO_SHORT,
        UsernameProblem.INVALID_CHARACTERS,
    ]


def test_normalized_input_passes():
    assert problems(normalize_username("  Mostafa_4 ")) == []


def test_normalizing_does_not_make_invalid_characters_valid():
    assert problems(normalize_username("Has Space")) == [
        UsernameProblem.INVALID_CHARACTERS
    ]