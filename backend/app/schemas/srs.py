# app/schemas/srs.py
from enum import Enum

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SRSState(str, Enum):
    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"


class Grade(str, Enum):
    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"




class GradeIn(BaseModel):
    grade: Grade


class SentenceWithSRS(BaseModel):
    """Like SentenceRead, plus the SRS fields — kept separate so the M2
    SentenceRead schema doesn't change shape for existing endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    de: str
    en: str
    topics: list[str]
    grammar_tag: str | None
    srs_due: datetime
    srs_interval_days: int
    srs_ease: float
    srs_reps: int
    srs_lapses: int
    srs_state: str
    created_at: datetime
    updated_at: datetime


class DueCountOut(BaseModel):
    count: int