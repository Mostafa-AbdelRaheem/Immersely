import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr

# Emails are stored lowercase (the DB enforces it). Normalizing at the schema
# boundary means every schema that uses this type agrees, with no per-service
# reminders needed.
NormalizedEmail = Annotated[EmailStr, AfterValidator(str.lower)]



class UserCreate(BaseModel):
    email: NormalizedEmail
    password: str


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


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str