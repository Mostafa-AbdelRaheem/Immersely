"""Pure password-policy checks.

No I/O and no Settings import: the caller passes the limits in, so this
file stays trivially unit-testable (same pattern as correction_logic.py).
"""

from enum import Enum

# bcrypt only uses the first 72 BYTES of a password, and bcrypt 4.0.1 truncates
# silently (verified in this project's environment), so a longer password must
# be rejected rather than quietly weakened. An algorithm limit, not a tunable
# policy: hence a constant, not a Setting.
BCRYPT_MAX_BYTES = 72
class PasswordProblem(str, Enum):
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    SAME_AS_EMAIL = "same_as_email"
    # Never produced by check_password (pure, no network): the service adds
    # it after a breached-password lookup so callers see ONE vocabulary.
    BREACHED = "breached"


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