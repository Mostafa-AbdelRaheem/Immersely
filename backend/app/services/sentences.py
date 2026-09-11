# app/services/sentences.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sentence import Sentence
from app.schemas.sentence import SentenceCreate, SentenceUpdate
from app.services.embeddings import embed_text
from app.services.tagging import TaggingError, tag_sentence


class SentenceNotFoundError(Exception):
    pass


async def create_sentence(
    db: AsyncSession, user_id: uuid.UUID, sentence_in: SentenceCreate
) -> Sentence:
    embedding = await embed_text(sentence_in.de)

    topics: list[str] = []
    grammar_tag: str | None = None
    try:
        tag_result = await tag_sentence(sentence_in.de)
        topics = [t.value for t in tag_result.topics]
        grammar_tag = tag_result.grammar_tag
    except TaggingError as exc:
        # Best-effort: tagging failures never block sentence creation.
        # TEMPORARY: printing the real error so we can diagnose silent
        # failures instead of guessing.
        print(f"[tagging failed] {exc}")

    new_sentence = Sentence(
        user_id=user_id,
        de=sentence_in.de,
        en=sentence_in.en,
        embedding=embedding,
        topics=topics,
        grammar_tag=grammar_tag,
    )
    db.add(new_sentence)
    await db.commit()
    await db.refresh(new_sentence)

    return new_sentence


async def list_sentences(db: AsyncSession, user_id: uuid.UUID) -> list[Sentence]:
    result = await db.execute(
        select(Sentence)
        .where(Sentence.user_id == user_id)
        .order_by(Sentence.created_at.desc())
    )
    return list(result.scalars().all())


async def get_sentence(
    db: AsyncSession, user_id: uuid.UUID, sentence_id: uuid.UUID
) -> Sentence:
    result = await db.execute(
        select(Sentence).where(
            Sentence.id == sentence_id, Sentence.user_id == user_id
        )
    )
    sentence = result.scalar_one_or_none()
    if sentence is None:
        raise SentenceNotFoundError(f"Sentence {sentence_id} not found")
    return sentence


async def update_sentence(
    db: AsyncSession,
    user_id: uuid.UUID,
    sentence_id: uuid.UUID,
    sentence_in: SentenceUpdate,
) -> Sentence:
    sentence = await get_sentence(db, user_id, sentence_id)

    update_data = sentence_in.model_dump(exclude_unset=True)

    if "topics" in update_data:
        update_data["topics"] = [t.value if hasattr(t, "value") else t for t in update_data["topics"]]

    for field, value in update_data.items():
        setattr(sentence, field, value)

    if "de" in update_data:
        sentence.embedding = await embed_text(update_data["de"])

    await db.commit()
    await db.refresh(sentence)

    return sentence


async def delete_sentence(
    db: AsyncSession, user_id: uuid.UUID, sentence_id: uuid.UUID
) -> None:
    sentence = await get_sentence(db, user_id, sentence_id)
    await db.delete(sentence)
    await db.commit()