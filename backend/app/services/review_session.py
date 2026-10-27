# app/services/review_session.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_event import ReviewEvent
from app.models.scene import Scene
from app.models.sentence import Sentence
from app.schemas.correction import Tier
from app.schemas.review_session import ReviewGradeIn
from app.services.srs import apply_grade_to_sentence


class InvalidSceneError(Exception):
    """Scene doesn't exist, isn't the user's, or doesn't contain the sentence."""


async def _ensure_scene_covers_sentence(
    db: AsyncSession,
    user_id: uuid.UUID,
    sentence_id: uuid.UUID,
    scene_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.user_id == user_id)
    )
    scene = result.scalar_one_or_none()
    if scene is None or sentence_id not in scene.sentence_ids:
        raise InvalidSceneError()


async def record_review(
    db: AsyncSession,
    user_id: uuid.UUID,
    sentence_id: uuid.UUID,
    payload: ReviewGradeIn,
) -> Sentence:
    """Apply the final grade to the sentence and log the review event in ONE
    transaction. Raises SentenceNotFoundError (from services.sentences) or
    InvalidSceneError before anything is written."""
    if payload.scene_id is not None:
        await _ensure_scene_covers_sentence(db, user_id, sentence_id, payload.scene_id)

    sentence = await apply_grade_to_sentence(db, user_id, sentence_id, payload.grade)

    event = ReviewEvent(
        user_id=user_id,
        sentence_id=sentence_id,
        scene_id=payload.scene_id,
        mode="free_production" if payload.scene_id is not None else "isolated",
        user_input=payload.user_input,
        tier=payload.tier.value,
        corrected_input=payload.corrected_input,
        rule_practiced=(
            None if payload.tier == Tier.INCORRECT else payload.rule_practiced
        ),
        grade=payload.grade.value,
    )
    db.add(event)

    await db.commit()
    await db.refresh(sentence)
    return sentence