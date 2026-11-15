import pytest
from pydantic import ValidationError

from app.core.config import Settings

REQUIRED = {
    "database_url": "postgresql+asyncpg://u:p@localhost/db",
    "jwt_secret_key": "x",
    "groq_api_key": "x",
}


def build(**overrides):
    # _env_file=None: ignore the developer's real .env so the test is hermetic.
    return Settings(_env_file=None, **REQUIRED, **overrides)


def test_password_max_bytes_defaults_to_the_bcrypt_limit():
    assert build().password_max_bytes == 72


def test_password_max_bytes_may_be_lowered():
    assert build(password_max_bytes=64).password_max_bytes == 64


@pytest.mark.parametrize("bad", [0, 73, 1000])
def test_password_max_bytes_outside_1_to_72_is_rejected(bad):
    with pytest.raises(ValidationError):
        build(password_max_bytes=bad)

def test_email_token_settings_defaults():
    s = build()
    assert s.verify_email_token_ttl_minutes == 1440
    assert s.reset_password_token_ttl_minutes == 30
    assert s.frontend_base_url == "http://localhost:5173"


def test_reset_token_lifetime_is_capped_at_24_hours():
    assert build(reset_password_token_ttl_minutes=1440).reset_password_token_ttl_minutes == 1440
    with pytest.raises(ValidationError):
        build(reset_password_token_ttl_minutes=1441)


@pytest.mark.parametrize(
    "field", ["verify_email_token_ttl_minutes", "reset_password_token_ttl_minutes"]
)
def test_token_lifetimes_must_be_positive(field):
    with pytest.raises(ValidationError):
        build(**{field: 0})