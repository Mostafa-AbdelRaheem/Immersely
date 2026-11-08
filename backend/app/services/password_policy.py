"""Pure password-policy checks.

No I/O and no Settings import: the caller passes the limits in, so this
file stays trivially unit-testable (same pattern as correction_logic.py).
"""

from enum import Enum


class PasswordProblem(str, Enum):
    TOO_SHORT = "too_short"
    SAME_AS_EMAIL = "same_as_email"


def check_password(
    password: str, *, email: str, min_length: int
) -> list[PasswordProblem]:
    """Return every policy problem with `password` (empty list = acceptable).

    Deliberately NOT done: composition rules (NIST says don't), trimming
    (spaces are valid in passphrases), and substring matching (NIST
    compares the whole password against the blocklist).
    """
    problems: list[PasswordProblem] = []

    if len(password) < min_length:
        problems.append(PasswordProblem.TOO_SHORT)

    local_part = email.split("@", 1)[0]
    if password.casefold() in {email.casefold(), local_part.casefold()}:
        problems.append(PasswordProblem.SAME_AS_EMAIL)

    return problems