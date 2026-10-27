# app/services/session_start.py
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scene import Scene
from app.models.sentence import Sentence
from app.services.scenes import NoDueSentencesError, get_or_create_scene
from app.services.session_chunks import (
    Chunk,
    ChunkTarget,
    MalformedSceneError,
    build_scene_chunks,
)
from app.services.srs import list_due_sentences


@dataclass(frozen=True)
class SessionPlan:
    mode: Literal["scene", "isolated"]
    topic: str | None
    scene_id: uuid.UUID | None
    chunks: list[Chunk]


async def _start_isolated(
    db: AsyncSession, user_id: uuid.UUID, max_targets: int
) -> SessionPlan:
    sentences = await list_due_sentences(db, user_id, limit=max_targets)
    if not sentences:
        raise NoDueSentencesError("No due sentences")

    chunks = [
        Chunk(
            filler_lines=[],
            target=ChunkTarget(sentence_id=s.id, speaker=None, hint_en=s.en),
        )
        for s in sentences
    ]
    return SessionPlan(mode="isolated", topic=None, scene_id=None, chunks=chunks)


async def _start_scene(
    db: AsyncSession, user_id: uuid.UUID, topic: str, max_targets: int
) -> SessionPlan:
    scene = await get_or_create_scene(db, user_id, topic, max_targets=max_targets)

    # Copy what we need before the commit below, in case attributes expire.
    scene_id = scene.id
    text_de = scene.text_de
    line_sentence_map = dict(scene.line_sentence_map)
    sentence_ids = list(scene.sentence_ids)

    result = await db.execute(
        select(Sentence).where(
            Sentence.user_id == user_id, Sentence.id.in_(sentence_ids)
        )
    )
    en_by_id = {s.id: s.en for s in result.scalars().all()}

    chunks = build_scene_chunks(text_de, line_sentence_map, en_by_id)

    planned = {c.target.sentence_id for c in chunks if c.target is not None}
    if planned != set(sentence_ids):
        raise MalformedSceneError("Scene targets don't match its sentence list")

    # Count this session against the scene's reuse budget (once per session).
    await db.execute(
        update(Scene)
        .where(Scene.id == scene_id, Scene.user_id == user_id)
        .values(
            review_count_since_generated=Scene.review_count_since_generated + 1
        )
    )
    await db.commit()

    return SessionPlan(mode="scene", topic=topic, scene_id=scene_id, chunks=chunks)


async def start_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic: str | None,
    max_targets: int,
) -> SessionPlan:
    """topic given -> scene mode; topic None ("all") -> isolated mode.
    Raises NoDueSentencesError, SceneVerificationFailedError (from M5) or
    MalformedSceneError."""
    if topic is None:
        return await _start_isolated(db, user_id, max_targets)
    return await _start_scene(db, user_id, topic, max_targets)