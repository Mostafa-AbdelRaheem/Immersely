"""Outgoing email behind a tiny interface.

Services depend on EmailSender (anything with an async send()), never on a
provider. build_email_sender() picks the implementation from a backend name,
and an unknown name RAISES instead of falling back: a typo must never
silently turn "send real email" into "print to a console".
"""

from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings


class EmailSendError(Exception):
    """A provider could not deliver a message (normalized, like TaggingError)."""


class UnknownEmailBackendError(Exception):
    pass


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailSender:
    """Development sender: prints the message (links included) to stdout.

    print(flush=True) rather than logging, so it shows up whatever the
    logging configuration is. Never use this where real users register.
    """

    async def send(self, message: EmailMessage) -> None:
        print(
            "\n================ EMAIL (console backend) ================\n"
            f"To:      {message.to}\n"
            f"Subject: {message.subject}\n"
            "\n"
            f"{message.text_body}\n"
            "=========================================================\n",
            flush=True,
        )


def build_email_sender(backend: str) -> EmailSender:
    if backend == "console":
        return ConsoleEmailSender()
    raise UnknownEmailBackendError(f"Unknown email backend: {backend!r}")


def get_email_sender() -> EmailSender:
    """Sender for the configured backend (usable as a FastAPI dependency)."""
    return build_email_sender(settings.email_backend)