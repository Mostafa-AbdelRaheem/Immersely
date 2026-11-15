import asyncio
import dataclasses

import pytest

from app.services import email_sender
from app.services.email_sender import (
    ConsoleEmailSender,
    EmailMessage,
    UnknownEmailBackendError,
    build_email_sender,
    get_email_sender,
)

MESSAGE = EmailMessage(
    to="mostafa@example.com",
    subject="Verify your email",
    text_body="Open https://example.test/verify#abc",
)


def test_console_sender_prints_recipient_subject_and_body(capsys):
    asyncio.run(ConsoleEmailSender().send(MESSAGE))
    out = capsys.readouterr().out
    assert "To:      mostafa@example.com" in out
    assert "Subject: Verify your email" in out
    assert "Open https://example.test/verify#abc" in out


def test_build_console_backend():
    assert isinstance(build_email_sender("console"), ConsoleEmailSender)


@pytest.mark.parametrize("backend", ["smtp", "Console", ""])
def test_unknown_backend_raises_instead_of_falling_back(backend):
    with pytest.raises(UnknownEmailBackendError):
        build_email_sender(backend)


def test_message_is_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        MESSAGE.to = "someone-else@example.com"


def test_get_email_sender_follows_the_setting(monkeypatch):
    monkeypatch.setattr(email_sender.settings, "email_backend", "console")
    assert isinstance(get_email_sender(), ConsoleEmailSender)


def test_get_email_sender_with_a_bad_setting_raises(monkeypatch):
    monkeypatch.setattr(email_sender.settings, "email_backend", "nope")
    with pytest.raises(UnknownEmailBackendError):
        get_email_sender()