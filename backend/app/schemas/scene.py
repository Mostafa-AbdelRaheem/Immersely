# app/schemas/scene.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


class SceneRequest(BaseModel):
    """Input for requesting a scene: which topic, how many due sentences
    to include at most (mirrors the session-size cap used for isolated
    review in M7, kept here so scene size is bounded too)."""
    topic: str = Field(..., min_length=1, max_length=100)
    max_targets: int = Field(
        default_factory=lambda: settings.scene_max_targets, ge=1, le=20
    )


class SceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: str
    sentence_ids: list[uuid.UUID]
    padding_sentence_ids: list[uuid.UUID]
    text_de: str
    text_en: str
    line_sentence_map: dict[str, int]
    generated_at: datetime
    review_count_since_generated: int
    model: str