import logging
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api.auth as api_auth
from app.core.db import get_db
from app.main import app
from app.services.email_sender import EmailSendError, get_email_sender
from app.services.password_policy import PasswordProblem

EMAIL = "tester@example.com"
PAYLOAD = {
    "email": EMAIL,
    "password": "zq7-quiet-Orchid-4821-xylophone-ruminate",
    "name": "Tester",
    "username": "tester",
}


def make_user():
    return SimpleNamespace(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        email=EMAIL,
        created_at=datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc),
        username="tester",
        name="Tester",
        email_verified_at=None,
    )


@pytest.fixture
def client(monkeypatch):
    async def fake_db():
        yield None

    async def fake_register(db, user_in):
        return make_user()

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_email_sender] = lambda: object()
    monkeypatch.setattr(api_auth, "register_user", fake_register)
    # Not used as a context manager: the startup DB ping never runs.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sends(monkeypatch):
    calls = []

    async def fake_send(db, sender, user, **kwargs):
        calls.append(user)

    monkeypatch.setattr(api_auth, "send_verification_email", fake_send)
    return calls


def test_registration_sends_the_verification_email(client, sends):
    response = client.post("/auth/register", json=PAYLOAD)
    assert response.status_code == 201
    assert response.json()["username"] == "tester"
    assert len(sends) == 1
    assert sends[0].email == EMAIL


def test_a_failed_send_does_not_fail_registration_and_leaks_nothing(
    client, monkeypatch, caplog
):
    async def failing_send(db, sender, user, **kwargs):
        # The provider's message deliberately echoes the address back.
        raise EmailSendError(f"provider rejected {EMAIL}")

    monkeypatch.setattr(api_auth, "send_verification_email", failing_send)

    with caplog.at_level(logging.WARNING, logger=api_auth.logger.name):
        response = client.post("/auth/register", json=PAYLOAD)

    assert response.status_code == 201
    logged = " ".join(caplog.messages)
    assert "EmailSendError" in logged
    assert EMAIL not in logged
    assert "provider rejected" not in logged


def test_a_rejected_registration_sends_nothing(client, sends, monkeypatch):
    async def rejecting_register(db, user_in):
        raise api_auth.WeakPasswordError([PasswordProblem.TOO_SHORT])

    monkeypatch.setattr(api_auth, "register_user", rejecting_register)

    response = client.post("/auth/register", json=PAYLOAD)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "weak_password"
    assert sends == []


def test_an_unexpected_send_error_is_not_swallowed(client, monkeypatch):
    async def buggy_send(db, sender, user, **kwargs):
        raise RuntimeError("bug")

    monkeypatch.setattr(api_auth, "send_verification_email", buggy_send)

    with pytest.raises(RuntimeError):
        client.post("/auth/register", json=PAYLOAD)