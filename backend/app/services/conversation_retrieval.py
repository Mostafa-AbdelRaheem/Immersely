# app/services/conversation_retrieval.py
"""Semantic retrieval of a user's saved sentences for Conversations."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sentence import Sentence
from app.services.embeddings import embed_text


async def find_similar_sentences(
    db: AsyncSession,
    user_id: uuid.UUID,
    query_text: str,
    k: int = 5,
) -> list[tuple[Sentence, float]]:
    """Return up to k of the user's sentences nearest to query_text,
    as (sentence, cosine_distance) pairs, closest first.

    Cosine distance: 0 = same direction, larger = less similar.
    Sentences without an embedding are skipped.
    """
    if not query_text.strip():
        return []

    query_vec = await embed_text(query_text)
    distance = Sentence.embedding.cosine_distance(query_vec)

    stmt = (
        select(Sentence, distance.label("distance"))
        .where(Sentence.user_id == user_id)
        .where(Sentence.embedding.is_not(None))
        .order_by(distance)
        .limit(k)
    )
    result = await db.execute(stmt)
    return [(row.Sentence, float(row.distance)) for row in result.all()]