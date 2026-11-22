# app/core/levels.py
"""CEFR levels for Conversations: one source of truth.

The Enum is used by request validation (an invalid level is a 422) and the
guidance text is what the partner prompt receives. The guidance is our own
wording (not an official CEFR text) and the numbers are rough targets.
"""
from enum import Enum


class Level(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


DEFAULT_LEVEL = Level.B1

LEVEL_GUIDANCE: dict[Level, str] = {
    Level.A1: (
        "Very short, simple sentences of at most about 8 words. Present tense "
        "only. Only the most common everyday words (greetings, numbers, food, "
        "family). No subordinate clauses. Ask simple questions."
    ),
    Level.A2: (
        "Short sentences of about 8 to 12 words. Mostly present tense, plus the "
        "perfect tense for simple past events and common modal verbs. Everyday "
        "vocabulary. At most one simple subordinate clause (weil, dass)."
    ),
    Level.B1: (
        "Sentences of about 10 to 16 words. Present, perfect and simple future; "
        "the Praeteritum only for sein, haben and modal verbs. Common "
        "subordinate clauses (weil, dass, wenn, obwohl) are fine. Everyday "
        "vocabulary plus common work and travel words. Avoid rare idioms."
    ),
    Level.B2: (
        "Natural sentences of about 12 to 20 words. All common tenses, the "
        "passive, and Konjunktiv II for polite requests and hypotheticals. "
        "Varied connectors and relative clauses. Broader vocabulary with some "
        "common idioms. Clear and conversational, not literary."
    ),
    Level.C1: (
        "Fluent, nuanced German. Complex sentence structures, Konjunktiv I and "
        "II, idiomatic expressions and subtle differences in register. Still "
        "conversational, not academic."
    ),
    Level.C2: (
        "Native-like German: precise and idiomatic, with colloquial phrases and "
        "shifts in register where the situation allows. No simplification."
    ),
}
