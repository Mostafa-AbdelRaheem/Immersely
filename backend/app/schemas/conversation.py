# app/schemas/conversation.py
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.correction import GrammarVerdict


class ChatMessageIn(BaseModel):
    role: Literal["user", "partner"]
    text: str


class TurnRequest(BaseModel):
    scenario_id: str
    history: list[ChatMessageIn] = []


class ChipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    de: str
    en: str


class CorrectionRead(BaseModel):
    verdict: GrammarVerdict
    corrected_text: str | None = None
    note: str | None = None


class TurnResponse(BaseModel):
    partner_reply: str
    correction: CorrectionRead | None = None
    chips: list[ChipRead]


class ScenarioRead(BaseModel):
    id: str
    title: str