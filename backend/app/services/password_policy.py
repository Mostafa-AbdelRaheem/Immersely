"""Pure password-policy checks.

No I/O and no Settings import: the caller passes the limits in, so this
file stays trivially unit-testable (same pattern as correction_logic.py).
"""

from enum import Enum


class PasswordProblem(str, Enum):
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    SAME_AS_EMAIL = "same_as_email"
    # Never produced by check_password (pure, no network): the service adds
    # it after a breached-password lookup so callers see ONE vocabulary.
    BREACHED = "breached"


def check_password(
    password: str, *, email: str, min_length: int, max_bytes: int
) -> list[PasswordProblem]:
    """Return every policy problem with `password` (empty list = acceptable).

    `max_bytes` is measured in BYTES, not characters, because bcrypt counts
    bytes ("ü" is 2). Its value and its ceiling live in Settings.

    Deliberately NOT done: composition rules (NIST says don't), trimming
    (spaces are valid in passphrases), and substring matching (NIST
    compares the whole password against the blocklist).
    """
    problems: list[PasswordProblem] = []

    if len(password) < min_length:
        problems.append(PasswordProblem.TOO_SHORT)
    if len(password.encode("utf-8")) > max_bytes:
        problems.append(PasswordProblem.TOO_LONG)

    local_part = email.split("@", 1)[0]
    if password.casefold() in {email.casefold(), local_part.casefold()}:
        problems.append(PasswordProblem.SAME_AS_EMAIL)

    return problems