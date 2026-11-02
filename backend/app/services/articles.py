# app/services/articles.py
import logging
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.langchain_.article_generation import generate_article
from app.models.article import Article
from app.models.sentence import Sentence
from app.schemas.article_generation import ArticleOutput
from app.services.article_logic import normalize_article, verify_article
from app.services.srs import list_due_sentences

logger = logging.getLogger(__name__)

MAX_ARTICLE_ATTEMPTS = 3


class NoSentencesForTopicError(Exception):
    """The user has no sentences at all under this topic."""


class ArticleGenerationFailedError(Exception):
    """No article passed verification within MAX_ARTICLE_ATTEMPTS."""


class ArticleNotFoundError(Exception):
    """Covers both 'does not exist' and 'belongs to another user'."""


async def pick_source_sentences(
    db: AsyncSession, user_id: uuid.UUID, topic: str
) -> list[Sentence]:
    """Due sentences first (oldest due first), then random non-due sentences
    from the same topic to fill up to settings.read_max_sentences."""
    limit = settings.read_max_sentences
    sentences = await list_due_sentences(db, user_id, topic=topic, limit=limit)

    remaining = limit - len(sentences)
    if remaining > 0:
        stmt = select(Sentence).where(
            Sentence.user_id == user_id, Sentence.topics.any(topic)
        )
        if sentences:
            stmt = stmt.where(Sentence.id.notin_([s.id for s in sentences]))
        stmt = stmt.order_by(func.random()).limit(remaining)
        result = await db.execute(stmt)
        sentences = sentences + list(result.scalars().all())

    if not sentences:
        raise NoSentencesForTopicError(f"No sentences for topic '{topic}'")
    return sentences


async def generate_verified_article(
    topic: str, sentences: list[Sentence]
) -> ArticleOutput:
    supplied_ids = [s.id for s in sentences]
    last_reason = "unknown"

    for attempt in range(1, MAX_ARTICLE_ATTEMPTS + 1):
        try:
            output = await generate_article(topic, sentences)
            output = normalize_article(output)
            reason = verify_article(
                output,
                supplied_ids,
                settings.read_min_chars,
                settings.read_max_chars,
            )
        except Exception as exc:
            last_reason = f"generation call failed: {exc}"
            logger.warning(
                "Article attempt %d/%d failed: %s",
                attempt, MAX_ARTICLE_ATTEMPTS, last_reason,
            )
            continue

        if reason is not None:
            last_reason = f"verification failed: {reason}"
            logger.warning(
                "Article attempt %d/%d failed: %s",
                attempt, MAX_ARTICLE_ATTEMPTS, last_reason,
            )
            continue

        return output

    raise ArticleGenerationFailedError(
        f"Could not generate a valid article for topic '{topic}' after "
        f"{MAX_ARTICLE_ATTEMPTS} attempts. Last failure: {last_reason}"
    )


async def create_article(
    db: AsyncSession, user_id: uuid.UUID, topic: str
) -> Article:
    sentences = await pick_source_sentences(db, user_id, topic)
    output = await generate_verified_article(topic, sentences)

    article = Article(
        user_id=user_id,
        topic=topic,
        title=output.title.strip(),
        text_de=output.text_de.strip(),
        text_en=output.text_en.strip(),
        sentence_ids=[s.id for s in sentences],
        model=settings.groq_model,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


async def list_articles(
    db: AsyncSession, user_id: uuid.UUID, topic: str | None = None
) -> list[Article]:
    stmt = (
        select(Article)
        .where(Article.user_id == user_id)
        .order_by(Article.generated_at.desc())
    )
    if topic is not None:
        stmt = stmt.where(Article.topic == topic)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_article(
    db: AsyncSession, user_id: uuid.UUID, article_id: uuid.UUID
) -> Article:
    result = await db.execute(
        select(Article).where(Article.id == article_id, Article.user_id == user_id)
    )
    article = result.scalar_one_or_none()
    if article is None:
        raise ArticleNotFoundError(str(article_id))
    return article


async def delete_article(
    db: AsyncSession, user_id: uuid.UUID, article_id: uuid.UUID
) -> None:
    article = await get_article(db, user_id, article_id)
    await db.execute(delete(Article).where(Article.id == article.id))
    await db.commit()