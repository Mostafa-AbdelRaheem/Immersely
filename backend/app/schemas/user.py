import uuid
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    model_validator,
)

# Emails are stored lowercase (the DB enforces it). Normalizing at the schema
# boundary means every schema that uses this type agrees, with no per-service
# reminders needed.
NormalizedEmail = Annotated[EmailStr, AfterValidator(str.lower)]



class UserCreate(BaseModel):
    email: NormalizedEmail
    password: str
     # Display name: required for new accounts, trimmed, Unicode allowed.
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
    ]
    # Normalized and validated in the service (see username_policy.py).
    username: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime
    username: str
    name: str | None = None
    email_verified_at: datetime | None = None


class UserLogin(BaseModel):
    email: NormalizedEmail
    password: str

class VerifyEmailIn(BaseModel):
    # Tokens are 43 characters; 200 is a sanity cap on what we will even hash.
    token: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]

# Payload sanity cap, NOT the password rule. The real limit (72 bytes) lives in
# Settings and the policy; this only stops a huge body being normalized.
# It must stay well above 72 so oversized passwords still get a `too_long`
# problem code instead of a generic 422.
MAX_PASSWORD_INPUT_CHARS = 1024


class ForgotPasswordIn(BaseModel):
    email: NormalizedEmail


class ResetPasswordIn(BaseModel):
    token: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    # No strip_whitespace: the password policy has no trimming, and a trimmed
    # value would hash differently from what the user typed at registration.
    new_password: Annotated[str, StringConstraints(max_length=MAX_PASSWORD_INPUT_CHARS)]

class ProfileUpdateIn(BaseModel):
    """PATCH /auth/me body. Only fields the client sent are applied.

    Rejects an empty body and an explicit null: both are almost certainly a
    client bug (e.g. someone who thinks null clears the field).
    """

    name: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
        ]
        | None
    ) = None
    # Normalized and validated in the service (see username_policy.py).
    username: str | None = None

    @model_validator(mode="after")
    def _at_least_one_real_value(self):
        if not self.model_fields_set:
            raise ValueError("nothing to update")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self