# app/schemas/review_session.py
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.schemas.correction import Tier
from app.schemas.srs import Grade, SRSState


class ReviewGradeIn(BaseModel):
    """Sent when the user clicks Continue: the FINAL grade (suggested or
    overridden) plus the result of the earlier /check call. Mode is not
    sent — the server derives it from whether scene_id is present."""
    model_config = ConfigDict(extra="forbid")

    grade: Grade
    tier: Tier
    user_input: str = Field(..., min_length=1, max_length=500)
    corrected_input: str | None = Field(default=None, max_length=500)
    rule_practiced: bool | None = None
    scene_id: uuid.UUID | None = None


class ReviewGradeOut(BaseModel):
    """The sentence's new SRS state after the grade was applied."""
    model_config = ConfigDict(from_attributes=True)

    srs_due: datetime
    srs_interval_days: int
    srs_state: SRSState


class SessionStartIn(BaseModel):
    """topic given -> scene mode; topic null/omitted -> isolated mode (all)."""
    model_config = ConfigDict(extra="forbid")

    topic: str | None = Field(default=None, min_length=1, max_length=100)
    max_targets: int = Field(
        default_factory=lambda: settings.scene_max_targets, ge=1, le=20
    )


class ChunkTargetOut(BaseModel):
    """Deliberately has NO German text: the answer is checked server-side
    against Sentence.de. hint_en is the English translation — hidden behind
    a 'Show hint' button in scene mode, shown as the cue in isolated mode."""
    model_config = ConfigDict(from_attributes=True)

    sentence_id: uuid.UUID
    speaker: str | None
    hint_en: str


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filler_lines: list[str]
    target: ChunkTargetOut | None


class SessionStartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mode: Literal["scene", "isolated"]
    topic: str | None
    scene_id: uuid.UUID | None
    chunks: list[ChunkOut]