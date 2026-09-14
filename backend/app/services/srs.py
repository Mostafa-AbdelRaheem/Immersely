
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sentence import Sentence
from app.services.sentences import get_sentence  # raises SentenceNotFoundError# app/services/srs.py
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from app.schemas.srs import Grade, SRSState
from datetime import timezone as _tz  # already imported above, just noting it's reused
from sqlalchemy import func, select


@dataclass(frozen=True)
class SRSFields:
    due: datetime
    interval_days: int
    ease: float
    reps: int
    lapses: int
    state: SRSState


MIN_EASE = 1.3
EASE_DELTA_AGAIN = -0.20
FIRST_LEARNING_STEP_MINUTES = 10


def _handle_again(fields: SRSFields, now: datetime) -> SRSFields:
    is_lapse = fields.state == SRSState.REVIEW
    return replace(
        fields,
        due=now + timedelta(minutes=FIRST_LEARNING_STEP_MINUTES),
        interval_days=0,
        ease=max(MIN_EASE, fields.ease + EASE_DELTA_AGAIN),
        reps=0,
        lapses=fields.lapses + (1 if is_lapse else 0),
        state=SRSState.RELEARNING if is_lapse else SRSState.LEARNING,
    )


LEARNING_STEPS_MINUTES = [10, 24 * 60]
GRADUATING_INTERVAL_DAYS = 1
EASY_GRADUATING_INTERVAL_DAYS = 4
EASE_DELTA_EASY = 0.15


def _handle_learning_step(fields: SRSFields, grade: Grade, now: datetime) -> SRSFields:
    state = SRSState.LEARNING if fields.state == SRSState.NEW else fields.state
    current_step = min(fields.reps, len(LEARNING_STEPS_MINUTES) - 1)

    if grade == Grade.HARD:
        return replace(
            fields,
            due=now + timedelta(minutes=LEARNING_STEPS_MINUTES[current_step]),
            interval_days=0,
            state=state,
        )

    if grade == Grade.EASY:
        return replace(
            fields,
            due=now + timedelta(days=EASY_GRADUATING_INTERVAL_DAYS),
            interval_days=EASY_GRADUATING_INTERVAL_DAYS,
            ease=fields.ease + EASE_DELTA_EASY,
            reps=1,
            state=SRSState.REVIEW,
        )

    if fields.reps >= len(LEARNING_STEPS_MINUTES) - 1:
        return replace(
            fields,
            due=now + timedelta(days=GRADUATING_INTERVAL_DAYS),
            interval_days=GRADUATING_INTERVAL_DAYS,
            reps=1,
            state=SRSState.REVIEW,
        )
    return replace(
        fields,
        due=now + timedelta(minutes=LEARNING_STEPS_MINUTES[fields.reps]),
        reps=fields.reps + 1,
        state=state,
    )

HARD_INTERVAL_MULTIPLIER = 1.2
EASY_INTERVAL_BONUS = 1.3
EASE_DELTA_HARD = -0.15


def _handle_review(fields: SRSFields, grade: Grade, now: datetime) -> SRSFields:
    if grade == Grade.HARD:
        interval = max(1, round(fields.interval_days * HARD_INTERVAL_MULTIPLIER))
        ease = max(MIN_EASE, fields.ease + EASE_DELTA_HARD)
    elif grade == Grade.EASY:
        interval = max(1, round(fields.interval_days * fields.ease * EASY_INTERVAL_BONUS))
        ease = fields.ease + EASE_DELTA_EASY
    else:  # GOOD
        interval = max(1, round(fields.interval_days * fields.ease))
        ease = fields.ease

    return replace(
        fields,
        due=now + timedelta(days=interval),
        interval_days=interval,
        ease=ease,
        reps=fields.reps + 1,
        state=SRSState.REVIEW,
    )

def update_srs(fields: SRSFields, grade: Grade, now: datetime | None = None) -> SRSFields:
    """Return the next SRS state for `fields` given `grade`. Pure — no I/O,
    never mutates `fields`, same inputs always give the same output."""
    now = now or datetime.now(timezone.utc)

    if grade == Grade.AGAIN:
        return _handle_again(fields, now)

    if fields.state in (SRSState.NEW, SRSState.LEARNING, SRSState.RELEARNING):
        return _handle_learning_step(fields, grade, now)

    return _handle_review(fields, grade, now)


def _srs_fields_from_sentence(sentence: Sentence) -> SRSFields:
    return SRSFields(
        due=sentence.srs_due,
        interval_days=sentence.srs_interval_days,
        ease=sentence.srs_ease,
        reps=sentence.srs_reps,
        lapses=sentence.srs_lapses,
        state=SRSState(sentence.srs_state),
    )


def _apply_srs_fields_to_sentence(sentence: Sentence, fields: SRSFields) -> None:
    sentence.srs_due = fields.due
    sentence.srs_interval_days = fields.interval_days
    sentence.srs_ease = fields.ease
    sentence.srs_reps = fields.reps
    sentence.srs_lapses = fields.lapses
    sentence.srs_state = fields.state.value


async def grade_sentence(
    db: AsyncSession, user_id: uuid.UUID, sentence_id: uuid.UUID, grade: Grade
) -> Sentence:
    sentence = await get_sentence(db, user_id, sentence_id)

    current = _srs_fields_from_sentence(sentence)
    updated = update_srs(current, grade)
    _apply_srs_fields_to_sentence(sentence, updated)

    await db.commit()
    await db.refresh(sentence)
    return sentence



async def list_due_sentences(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic: str | None = None,
    limit: int = 50,
) -> list[Sentence]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(Sentence)
        .where(Sentence.user_id == user_id, Sentence.srs_due <= now)
        .order_by(Sentence.srs_due.asc())
        .limit(limit)
    )
    if topic is not None:
        stmt = stmt.where(Sentence.topics.any(topic))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_due_sentences(
    db: AsyncSession, user_id: uuid.UUID, topic: str | None = None
) -> int:
    now = datetime.now(timezone.utc)
    stmt = (
        select(func.count())
        .select_from(Sentence)
        .where(Sentence.user_id == user_id, Sentence.srs_due <= now)
    )
    if topic is not None:
        stmt = stmt.where(Sentence.topics.any(topic))
    result = await db.execute(stmt)
    return result.scalar_one()