from enum import Enum


class TokenPurpose(str, Enum):
    """What a single-use email token is for (stored in email_tokens.purpose)."""

    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"