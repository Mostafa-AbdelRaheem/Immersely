# app/services/sentences.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sentence import Sentence
from app.schemas.sentence import SentenceCreate, SentenceUpdate


class SentenceNotFoundError(Exception):
    pass


async def create_sentence(
    db: AsyncSession, user_id: uuid.UUID, sentence_in: SentenceCreate
) -> Sentence:
    new_sentence = Sentence(
        user_id=user_id,
        de=sentence_in.de,
        en=sentence_in.en,
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
    for field, value in update_data.items():
        setattr(sentence, field, value)

    await db.commit()
    await db.refresh(sentence)

    return sentence


async def delete_sentence(
    db: AsyncSession, user_id: uuid.UUID, sentence_id: uuid.UUID
) -> None:
    sentence = await get_sentence(db, user_id, sentence_id)
    await db.delete(sentence)
    await db.commit()