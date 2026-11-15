import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api.auth as api_auth
from app.core.db import get_db
from app.core.limiter import limiter
from app.main import app
from app.services.auth import WeakPasswordError
from app.services.email_sender import EmailMessage, EmailSendError, get_email_sender
from app.services.email_tokens import InvalidTokenError
from app.services.password_policy import PasswordProblem

EMAIL = "tester@example.com"
MESSAGE = EmailMessage(to=EMAIL, subject="subject", text_body="body")


class RecordingSender:
    def __init__(self):
        self.sent = []
        self.error = None

    async def send(self, message):
        if self.error:
            raise self.error
        self.sent.append(message)


@pytest.fixture
def world(monkeypatch):
    limiter.reset()  # slowapi counters are per process; every test shares one fake IP
    sender = RecordingSender()
    w = SimpleNamespace(
        sender=sender,
        reset_message=None,  # what request_password_reset returns
        reset_error=None,  # what reset_password raises
        reset_calls=[],
    )

    async def fake_db():
        yield None

    async def fake_request(db, email, **kwargs):
        return w.reset_message

    async def fake_reset(db, token, new_password, **kwargs):
        w.reset_calls.append((token, new_password))
        if w.reset_error:
            raise w.reset_error
        return MESSAGE

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_email_sender] = lambda: sender
    monkeypatch.setattr(api_auth, "request_password_reset", fake_request)
    monkeypatch.setattr(api_auth, "reset_password", fake_reset)
    # Not used as a context manager: the startup DB ping never runs.
    w.client = TestClient(app)
    yield w
    app.dependency_overrides.clear()
    limiter.reset()


def test_forgot_password_returns_the_same_body_and_sends_nothing_for_none(world):
    world.reset_message = None  # unknown email OR cooldown
    response = world.client.post("/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 200
    assert response.json() == api_auth.FORGOT_PASSWORD_RESPONSE
    assert world.sender.sent == []


def test_forgot_password_sends_in_the_background_with_an_identical_response(world):
    world.reset_message = MESSAGE
    response = world.client.post("/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 200
    assert response.json() == api_auth.FORGOT_PASSWORD_RESPONSE
    assert world.sender.sent == [MESSAGE]


def test_forgot_password_rejects_a_malformed_email(world):
    response = world.client.post("/auth/forgot-password", json={"email": "nope"})
    assert response.status_code == 422


def test_a_failed_background_send_does_not_change_the_response_or_leak(
    world, caplog
):
    world.reset_message = MESSAGE
    world.sender.error = EmailSendError(f"provider rejected {EMAIL}")
    with caplog.at_level(logging.WARNING):
        response = world.client.post("/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 200
    assert response.json() == api_auth.FORGOT_PASSWORD_RESPONSE
    assert "EmailSendError" in caplog.text
    assert EMAIL not in caplog.text  # class name only


def test_forgot_password_is_limited_to_three_per_minute(world):
    codes = [
        world.client.post("/auth/forgot-password", json={"email": EMAIL}).status_code
        for _ in range(4)
    ]
    assert codes == [200, 200, 200, 429]


def test_reset_password_success_updates_and_sends_the_notice(world):
    response = world.client.post(
        "/auth/reset-password", json={"token": "abc", "new_password": "pw"}
    )
    assert response.status_code == 200
    assert response.json() == {"detail": "Password updated"}
    assert world.sender.sent == [MESSAGE]


def test_reset_password_invalid_token_is_a_400_with_a_code_and_sends_nothing(world):
    world.reset_error = InvalidTokenError("bad")
    response = world.client.post(
        "/auth/reset-password", json={"token": "abc", "new_password": "pw"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": {"code": "invalid_token"}}
    assert world.sender.sent == []


def test_reset_password_weak_password_is_a_422_with_problem_codes(world):
    world.reset_error = WeakPasswordError([PasswordProblem.TOO_SHORT])
    response = world.client.post(
        "/auth/reset-password", json={"token": "abc", "new_password": "pw"}
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": {"code": "weak_password", "problems": ["too_short"]}
    }
    assert world.sender.sent == []


def test_reset_password_strips_the_token_but_never_the_password(world):
    world.client.post(
        "/auth/reset-password",
        json={"token": "  abc  ", "new_password": "  keep me  "},
    )
    assert world.reset_calls == [("abc", "  keep me  ")]


def test_reset_password_requires_both_fields(world):
    response = world.client.post("/auth/reset-password", json={"token": "abc"})
    assert response.status_code == 422
    assert world.reset_calls == []