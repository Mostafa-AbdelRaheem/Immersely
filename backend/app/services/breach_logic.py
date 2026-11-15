"""Pure helpers for the Pwned Passwords k-anonymity lookup.

No network and no Settings here: the I/O lives in breached_passwords.py,
so this file is trivially unit-testable (same split as correction_logic.py).
"""

import hashlib


def sha1_prefix_suffix(password: str) -> tuple[str, str]:
    """Return (prefix, suffix) of the password's uppercase SHA-1 hex digest.

    Only the 5-character prefix is ever sent to HIBP; the 35-character
    suffix stays local and is matched against the response. SHA-1 is a
    lookup key here (the protocol requires it), not a security primitive,
    hence usedforsecurity=False.
    """
    digest = (
        hashlib.sha1(password.encode("utf-8"), usedforsecurity=False)
        .hexdigest()
        .upper()
    )
    return digest[:5], digest[5:]


def count_in_range_response(body: str, suffix: str) -> int:
    """Return how many times `suffix` appears in a range response (0 if absent).

    The body is one `SUFFIX:COUNT` pair per line. Padding entries (added by
    the Add-Padding header) always have count 0, so they naturally read as
    "not found". Malformed lines are skipped rather than raising.
    """
    wanted = suffix.upper()
    for line in body.splitlines():
        candidate, _, count = line.partition(":")
        if candidate.strip().upper() != wanted:
            continue
        try:
            return int(count.strip())
        except ValueError:
            continue
    return 0