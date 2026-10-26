# app/schemas/correction.py
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.srs import Grade


class Tier(str, Enum):
    CORRECT = "correct"
    ALMOST_CORRECT = "almost_correct"
    INCORRECT = "incorrect"


# --- What the LLM returns (structured output) -------------------------------
# Field descriptions matter here: with_structured_output sends them to the
# model as part of the tool schema, so they double as prompt instructions.

class CorrectionLLMOutput(BaseModel):
    tier: Tier = Field(
        description=(
            "correct: valid German with the right meaning, any phrasing. "
            "almost_correct: recognizable attempt with a fixable grammar error. "
            "incorrect: broken grammar or wrong meaning."
        )
    )
    very_close: bool = Field(
        default=False,
        description=(
            "Only meaningful when tier is 'correct': true if the answer is "
            "fluent and essentially matches the target sentence. "
            "False otherwise."
        ),
    )
    corrected_sentence: str | None = Field(
        default=None,
        description=(
            "Only when tier is 'almost_correct': the learner's own sentence, "
            "minimally corrected. Null otherwise."
        ),
    )
    diff_note: str | None = Field(
        default=None,
        description=(
            "Only when tier is 'almost_correct': one short sentence "
            "explaining what was fixed. Null otherwise."
        ),
    )
    rule_practiced: bool | None = Field(
        default=None,
        description=(
            "Only when tier is 'correct' or 'almost_correct' AND a grammar "
            "rule was provided: does the learner's answer actually use that "
            "rule? Null otherwise."
        ),
    )
    rule_note: str | None = Field(
        default=None,
        description=(
            "Only when rule_practiced is false: one short, friendly sentence "
            "on how the target sentence uses the rule. Null otherwise."
        ),
    )

class GrammarVerdict(str, Enum):
    VALID = "valid"
    FIXABLE_ERRORS = "fixable_errors"
    BROKEN = "broken"


class CorrectionJudgment(BaseModel):
    """What the LLM actually returns. It never picks the tier; code derives
    it from same_intent + grammar_verdict (see correction_logic.derive_tier)."""

    analysis: str = Field(
        description=(
            "2-3 short sentences of reasoning, written BEFORE the verdicts: "
            "which sentence did the learner intend, is that the same message "
            "as the English meaning, and what grammar errors (if any) does "
            "it contain."
        )
    )
    same_intent: bool = Field(
        description=(
            "True if the message the learner INTENDED (ignoring grammar "
            "slips) is the same communicative intent as the English meaning. "
            "False only for a genuinely different or unrecoverable message."
        )
    )
    grammar_verdict: GrammarVerdict = Field(
        description=(
            "valid: no genuine error (alternative valid forms are not errors). "
            "fixable_errors: small genuine errors a teacher would correct. "
            "broken: so broken it cannot be fixed with a small edit."
        )
    )
    very_close: bool = Field(
        default=False,
        description=(
            "Only when same_intent is true and grammar_verdict is valid: "
            "true if the answer is fluent and essentially matches the "
            "target sentence. False otherwise."
        ),
    )
    corrected_sentence: str | None = Field(
        default=None,
        description=(
            "Only when grammar_verdict is fixable_errors: the learner's own "
            "sentence with the minimum change. Null otherwise."
        ),
    )
    diff_note: str | None = Field(
        default=None,
        description=(
            "Only when grammar_verdict is fixable_errors: one short English "
            "sentence on what was fixed. Null otherwise."
        ),
    )
    rule_practiced: bool | None = Field(
        default=None,
        description=(
            "Only when a grammar rule was provided AND same_intent is true "
            "AND grammar_verdict is not broken. Null otherwise."
        ),
    )
    rule_note: str | None = Field(
        default=None,
        description=(
            "Only when rule_practiced is false: one short, friendly English "
            "sentence on how the target sentence uses the rule. Null otherwise."
        ),
    )

# --- API contract for POST /review/{sentence_id}/check ----------------------

class CheckAnswerIn(BaseModel):
    answer: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]


class CheckAnswerOut(BaseModel):
    tier: Tier
    suggested_grade: Grade
    model_answer: str                       # the stored target sentence (de)
    corrected_input: str | None = None      # almost_correct only
    diff_note: str | None = None            # almost_correct only
    rule_practiced: bool | None = None      # None = not evaluated
    rule_note: str | None = None            # only when rule_practiced is False