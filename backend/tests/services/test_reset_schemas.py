import pytest
from pydantic import ValidationError

from app.schemas.user import (
    MAX_PASSWORD_INPUT_CHARS,
    ForgotPasswordIn,
    ResetPasswordIn,
)


def test_forgot_email_is_lowercased():
    assert ForgotPasswordIn(email="Mostafa@Example.COM").email == "mostafa@example.com"


def test_forgot_rejects_a_malformed_email():
    with pytest.raises(ValidationError):
        ForgotPasswordIn(email="not-an-email")


def test_reset_token_is_stripped_and_must_not_be_empty():
    assert ResetPasswordIn(token="  abc  ", new_password="x").token == "abc"
    with pytest.raises(ValidationError):
        ResetPasswordIn(token="   ", new_password="x")


def test_reset_password_is_never_stripped():
    body = ResetPasswordIn(token="abc", new_password="  spaced out  ")
    assert body.new_password == "  spaced out  "


def test_reset_password_cap_boundary():
    ok = "a" * MAX_PASSWORD_INPUT_CHARS
    assert ResetPasswordIn(token="abc", new_password=ok).new_password == ok
    with pytest.raises(ValidationError):
        ResetPasswordIn(token="abc", new_password=ok + "a")


def test_the_cap_stays_above_the_72_byte_rule():
    assert MAX_PASSWORD_INPUT_CHARS > 72