"""Pure username rules (no I/O, no Settings import: limits are passed in).

Usernames are stored in ONE canonical form (lowercase), so uniqueness needs
no tricks. Call normalize_username() first; check_username() expects its
output, so an uppercase name passed directly is reported as invalid.
"""

import re
from enum import Enum


class UsernameProblem(str, Enum):
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    INVALID_CHARACTERS = "invalid_characters"


# Written out as [a-z0-9_] on purpose: \w and \d also match non-ASCII
# letters/digits in Python 3, which would silently widen the rule.
_ALLOWED = re.compile(r"[a-z0-9_]+")


def normalize_username(raw: str) -> str:
    """Canonical stored form: surrounding whitespace removed, lowercased."""
    return raw.strip().lower()


def check_username(
    username: str, *, min_length: int, max_length: int
) -> list[UsernameProblem]:
    """Return every problem with an already-normalized `username`.

    fullmatch (not match + "$") because "$" would accept a trailing newline.
    An empty string reports only TOO_SHORT, not also INVALID_CHARACTERS.
    """
    problems: list[UsernameProblem] = []

    if len(username) < min_length:
        problems.append(UsernameProblem.TOO_SHORT)
    if len(username) > max_length:
        problems.append(UsernameProblem.TOO_LONG)
    if username and not _ALLOWED.fullmatch(username):
        problems.append(UsernameProblem.INVALID_CHARACTERS)

    return problems