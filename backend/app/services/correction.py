# app/services/correction.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.langchain_.correction import grade_answer
from app.models.sentence import Sentence
from app.schemas.correction import CheckAnswerOut
from app.services.correction_logic import (
    MalformedCorrectionError,
    judgment_to_output,
    normalize_correction,
    suggest_grade,
)

MAX_GRADING_ATTEMPTS = 3  # module constant: internal safety valve, not .env-tunable


class SentenceNotFoundError(Exception):
    """Raised when sentence_id doesn't exist or doesn't belong to the user."""


class CorrectionFailedError(Exception):
    """Raised when grading couldn't produce a trustworthy result within the
    retry budget — either Groq kept failing, or the model's output kept
    failing normalize_correction's consistency checks."""


def _sanitize_answer(answer: str) -> str:
    """Defense in depth on top of the prompt's 'treat as data' instruction:
    strip characters that could break the <learner_answer> tag boundary.
    Length is already capped by CheckAnswerIn's max_length."""
    return answer.replace("<", "").replace(">", "").strip()


async def _get_owned_sentence(
    db: AsyncSession, user_id: uuid.UUID, sentence_id: uuid.UUID
) -> Sentence:
    result = await db.execute(
        select(Sentence).where(Sentence.id == sentence_id, Sentence.user_id == user_id)
    )
    sentence = result.scalar_one_or_none()
    if sentence is None:
        raise SentenceNotFoundError(f"Sentence {sentence_id} not found")
    return sentence


async def check_answer(
    db: AsyncSession,
    user_id: uuid.UUID,
    sentence_id: uuid.UUID,
    raw_answer: str,
) -> CheckAnswerOut:
    """Grades a learner's answer against the stored target sentence.

    Compute-only: does not log a review_event or touch SRS state (deferred
    to M7, see the M6 handoff's design-question discussion). Raises
    SentenceNotFoundError if the sentence isn't the user's, or
    CorrectionFailedError if grading can't produce a trustworthy result
    within MAX_GRADING_ATTEMPTS.
    """
    sentence = await _get_owned_sentence(db, user_id, sentence_id)
    answer = _sanitize_answer(raw_answer)
    has_rule = sentence.grammar_tag is not None

    last_error: Exception | None = None
    for attempt in range(1, MAX_GRADING_ATTEMPTS + 1):
        try:
            judgment = await grade_answer(
                target_de=sentence.de,
                target_en=sentence.en,
                user_answer=answer,
                grammar_tag=sentence.grammar_tag,
            )
            raw_output = judgment_to_output(judgment)
            cleaned = normalize_correction(
                raw_output, user_answer=answer, has_rule=has_rule
            )
        except Exception as e:
            # Broad catch by design (mirrors M5's generate_verified_scene):
            # covers Groq BadRequestError/transient failures AND our own
            # MalformedCorrectionError from normalize_correction.
            last_error = e
            continue

        return CheckAnswerOut(
            tier=cleaned.tier,
            suggested_grade=suggest_grade(cleaned.tier, cleaned.very_close),
            model_answer=sentence.de,
            corrected_input=cleaned.corrected_sentence,
            diff_note=cleaned.diff_note,
            rule_practiced=cleaned.rule_practiced,
            rule_note=cleaned.rule_note,
        )

    raise CorrectionFailedError(
        f"Grading failed after {MAX_GRADING_ATTEMPTS} attempts: {last_error}"
    )