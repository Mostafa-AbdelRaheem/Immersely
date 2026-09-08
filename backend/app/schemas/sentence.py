# app/schemas/sentence.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SentenceCreate(BaseModel):
    de: str = Field(..., min_length=1, max_length=2000)
    en: str = Field(..., min_length=1, max_length=2000)


class SentenceUpdate(BaseModel):
    de: str | None = Field(None, min_length=1, max_length=2000)
    en: str | None = Field(None, min_length=1, max_length=2000)


class SentenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    de: str
    en: str
    created_at: datetime
    updated_at: datetime