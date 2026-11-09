"""Pure builders for the links and messages we email (no I/O, no Settings).

The link carries the token in the URL FRAGMENT (#token=...), which browsers
never send to a server, so it stays out of access logs and Referer headers.
"""

from urllib.parse import quote

from app.services.email_sender import EmailMessage


def build_link(base_url: str, path: str, token: str) -> str:
    """{base_url}/{path}#token={token}. The base URL comes from Settings,
    never from a request's Host header (host-header injection).

    The token is percent-escaped: a no-op for our URL-safe tokens, but a value
    containing "#" or "&" can never break out of the fragment.
    """
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}#token={quote(token, safe='')}"


def describe_minutes(minutes: int) -> str:
    """1440 -> '24 hours', 60 -> '1 hour', 30 -> '30 minutes', 1 -> '1 minute'."""
    if minutes >= 60 and minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours} hour" + ("" if hours == 1 else "s")
    return f"{minutes} minute" + ("" if minutes == 1 else "s")


def verification_message(
    *, to: str, name: str | None, link: str, valid_for_minutes: int
) -> EmailMessage:
    greeting = f"Hi {name}," if name else "Hi there,"
    body = (
        f"{greeting}\n\n"
        "Welcome to Immersely! Please confirm your email address by opening "
        "this link:\n\n"
        f"{link}\n\n"
        f"The link works once and expires in {describe_minutes(valid_for_minutes)}. "
        "If you didn't create this account, you can safely ignore this email.\n"
    )
    return EmailMessage(to=to, subject="Verify your email for Immersely", text_body=body)