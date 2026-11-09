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



def password_reset_message(
    *, to: str, name: str | None, link: str, valid_for_minutes: int
) -> EmailMessage:
    greeting = f"Hi {name}," if name else "Hi there,"
    body = (
        f"{greeting}\n\n"
        "We received a request to reset your Immersely password. Open this link "
        "to choose a new one:\n\n"
        f"{link}\n\n"
        f"The link works once and expires in {describe_minutes(valid_for_minutes)}. "
        "If you didn't request this, you can safely ignore this email: your "
        "password will not change.\n"
    )
    return EmailMessage(to=to, subject="Reset your Immersely password", text_body=body)


def password_changed_message(*, to: str, name: str | None) -> EmailMessage:
    """Notice after a successful reset. Deliberately contains NO link: a
    clickable link in a security notice is what phishing emails imitate."""
    greeting = f"Hi {name}," if name else "Hi there,"
    body = (
        f"{greeting}\n\n"
        "The password for your Immersely account was just changed. For your "
        "security, other devices will be asked to sign in again shortly.\n\n"
        "If this was you, no action is needed. If it wasn't, request a new "
        "password reset from the sign-in page right away.\n"
    )
    return EmailMessage(
        to=to, subject="Your Immersely password was changed", text_body=body
    )