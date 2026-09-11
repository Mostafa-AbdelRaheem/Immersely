# app/schemas/sentence.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tagging import Topic


class SentenceCreate(BaseModel):
    de: str = Field(..., min_length=1, max_length=2000)
    en: str = Field(..., min_length=1, max_length=2000)


class SentenceUpdate(BaseModel):
    de: str | None = Field(None, min_length=1, max_length=2000)
    en: str | None = Field(None, min_length=1, max_length=2000)
    topics: list[Topic] | None = None
    grammar_tag: str | None = Field(None, max_length=100)


class SentenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    de: str
    en: str
    topics: list[str]
    grammar_tag: str | None
    created_at: datetime
    updated_at: datetime