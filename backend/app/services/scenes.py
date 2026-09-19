# app/services/scenes.py
# app/services/scenes.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.sentence import Sentence
from app.models.scene import Scene
from app.schemas.scene_generation import SceneGenerationOutput
from app.services.srs import list_due_sentences
from app.services.scene_verification import generate_verified_scene


class NoDueSentencesError(Exception):
    """Raised when a scene is requested for a topic with no due sentences."""
    pass


async def get_padding_sentences(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    exclude_ids: list[uuid.UUID],
    limit: int | None = None,
) -> list[Sentence]:
    """Non-due sentences from the same topic, for dialogue flavor only.
    Never graded, never shown as review items (§2.2 padding rule)."""
    limit = limit if limit is not None else settings.scene_max_padding
    if limit <= 0:
        return []

    now = datetime.now(timezone.utc)
    stmt = (
        select(Sentence)
        .where(
            Sentence.user_id == user_id,
            Sentence.topics.any(topic),
            Sentence.srs_due > now,
        )
        .order_by(func.random())
        .limit(limit)
    )
    if exclude_ids:
        stmt = stmt.where(Sentence.id.notin_(exclude_ids))

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_scene_source_sentences(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    max_targets: int,
) -> tuple[list[Sentence], list[Sentence]]:
    """Returns (target_sentences, padding_sentences) for a topic.

    Targets are due sentences, capped at max_targets, oldest-due first
    (reuses the M4 due-query). Padding is non-due, same-topic, for flow
    only — never graded. Raises NoDueSentencesError if there's nothing
    due, since a scene with zero targets isn't a review scene.
    """
    targets = await list_due_sentences(db, user_id, topic=topic, limit=max_targets)
    if not targets:
        raise NoDueSentencesError(f"No due sentences for topic '{topic}'")

    target_ids = [s.id for s in targets]
    padding = await get_padding_sentences(db, user_id, topic, exclude_ids=target_ids)

    return targets, padding



async def find_reusable_scene(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    current_target_ids: list[uuid.UUID],
) -> Scene | None:
    """Returns the most recent scene for this topic if it's still valid per
    the regeneration policy (§2.2): reused until either the due-sentence
    set changes, or review_count_since_generated exceeds the configured
    threshold — whichever comes first. Returns None if no scene exists or
    it's no longer valid (caller should generate a fresh one)."""
    result = await db.execute(
        select(Scene)
        .where(Scene.user_id == user_id, Scene.topic == topic)
        .order_by(Scene.generated_at.desc())
        .limit(1)
    )
    scene = result.scalar_one_or_none()
    if scene is None:
        return None

    if set(scene.sentence_ids) != set(current_target_ids):
        return None  # due-sentence set changed

    if scene.review_count_since_generated >= settings.scene_max_reviews_before_regen:
        return None  # scene aged out

    return scene


# app/services/scenes.py  (add)



def _build_scene_texts_and_map(
    generated: SceneGenerationOutput,
) -> tuple[str, str, dict[str, int]]:
    """Assembles the full German/English dialogue text from lines, and a
    map of target_sentence_id -> line position (0-indexed), for lines that
    are actual targets. Padding/connective lines are excluded from the map
    since they're never graded (§2.2 padding rule)."""
    text_de_lines: list[str] = []
    text_en_lines: list[str] = []
    line_sentence_map: dict[str, int] = {}

    for position, line in enumerate(generated.lines):
        prefix = f"{line.speaker}: " if line.speaker else ""
        text_de_lines.append(f"{prefix}{line.text_de}")
        text_en_lines.append(f"{prefix}{line.text_en}")
        if line.target_sentence_id is not None:
            line_sentence_map[line.target_sentence_id] = position

    return "\n".join(text_de_lines), "\n".join(text_en_lines), line_sentence_map


async def create_scene(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    targets: list[Sentence],
    padding: list[Sentence],
    generated: SceneGenerationOutput,
    model: str,
) -> Scene:
    """Persists a verified generated scene. Caller is responsible for
    running generate_verified_scene first — this function does no
    generation or verification itself, only persistence (service-layer
    separation: orchestration vs. data access stay distinct)."""
    text_de, text_en, line_sentence_map = _build_scene_texts_and_map(generated)

    scene = Scene(
        user_id=user_id,
        topic=topic,
        sentence_ids=[s.id for s in targets],
        padding_sentence_ids=[s.id for s in padding],
        text_de=text_de,
        text_en=text_en,
        line_sentence_map=line_sentence_map,
        model=model,
    )
    db.add(scene)
    await db.commit()
    await db.refresh(scene)
    return scene

# app/services/scenes.py  (add)

async def get_or_create_scene(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    max_targets: int,
    model: str = "openai/gpt-oss-20b",
) -> Scene:
    """Entry point for scene retrieval: reuses a cached scene if still
    valid per the regeneration policy (§2.2), otherwise generates,
    verifies, and persists a fresh one. Raises NoDueSentencesError if
    there's nothing due for this topic, or SceneVerificationFailedError
    if generation can't produce a verified scene within the retry budget.
    """
    targets, padding = await get_scene_source_sentences(db, user_id, topic, max_targets)
    target_ids = [s.id for s in targets]

    cached = await find_reusable_scene(db, user_id, topic, target_ids)
    if cached is not None:
        return cached

    generated = await generate_verified_scene(topic, targets, padding)
    return await create_scene(db, user_id, topic, targets, padding, generated, model=model)