"""Breached-password lookup against Pwned Passwords (k-anonymity).

Only the first 5 hex characters of the password's SHA-1 ever leave this
process. The caller passes the timeout in (no Settings import), and tests
inject an httpx.AsyncClient with a MockTransport, so no network is needed.
"""

import logging

import httpx

from app.services.breach_logic import count_in_range_response, sha1_prefix_suffix

logger = logging.getLogger(__name__)

HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/"
# HIBP rejects requests without a User-Agent.
USER_AGENT = "immersely-password-check"


async def count_breaches(password: str, *, client: httpx.AsyncClient) -> int:
    """How many times HIBP has seen `password` (0 = not found).

    Raises httpx.HTTPError on timeouts, connection problems or non-2xx.
    """
    prefix, suffix = sha1_prefix_suffix(password)
    response = await client.get(
        f"{HIBP_RANGE_URL}{prefix}",
        headers={"User-Agent": USER_AGENT, "Add-Padding": "true"},
    )
    response.raise_for_status()
    return count_in_range_response(response.text, suffix)


async def is_password_breached(
    password: str,
    *,
    timeout_s: float,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """True only when HIBP positively reports the password as breached.

    Fails OPEN: if the lookup cannot complete (timeout, network error,
    bad status), log a warning and return False so registration is never
    blocked by a third-party outage. Only httpx errors are swallowed; a
    real bug should still surface. If `client` is given, its own timeout
    applies and `timeout_s` is ignored.
    """
    try:
        if client is not None:
            count = await count_breaches(password, client=client)
        else:
            async with httpx.AsyncClient(timeout=timeout_s) as own_client:
                count = await count_breaches(password, client=own_client)
    except httpx.HTTPError as exc:
        # Class name only: never the message/URL (it carries a hash prefix).
        logger.warning("HIBP check skipped (fail-open): %s", type(exc).__name__)
        return False
    return count > 0