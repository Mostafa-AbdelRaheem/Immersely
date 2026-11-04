# app/schemas/chat_correction.py
from pydantic import BaseModel, Field

from app.schemas.correction import GrammarVerdict


class ChatCorrectionJudgment(BaseModel):
    """What the chat-correction LLM call returns for one learner message.

    Same decomposition as M6's CorrectionJudgment: reasoning is written
    first, then a narrow verdict. There is no target sentence in chat, so
    the only reference is correct German itself.
    """

    analysis: str = Field(
        description=(
            "1-2 short sentences of reasoning, written BEFORE the verdict: "
            "what the learner meant to say and which genuine errors, if "
            "any, the message contains."
        )
    )
    grammar_verdict: GrammarVerdict = Field(
        description=(
            "valid: no genuine error (alternative valid forms, informal "
            "chat style, missing final punctuation and a lowercase first "
            "letter are NOT errors). fixable_errors: small genuine errors "
            "a teacher would correct. broken: so broken that no small edit "
            "fixes it."
        )
    )
    corrected_text: str | None = Field(
        default=None,
        description=(
            "Only when grammar_verdict is fixable_errors: the learner's "
            "own message with the minimum change needed. Null otherwise."
        ),
    )
    note: str | None = Field(
        default=None,
        description=(
            "Only when grammar_verdict is not valid: ONE short English "
            "sentence saying what was fixed (fixable_errors) or a friendly "
            "hint (broken). Null when valid."
        ),
    )