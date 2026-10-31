# app/services/topics.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.topics import TOPICS
from app.models.sentence import Sentence
from app.schemas.topics import TopicOverview
from app.services.srs import due_condition


async def get_topic_overview(
    db: AsyncSession, user_id: uuid.UUID
) -> list[TopicOverview]:
    """Return all canonical topics with the user's sentence and due counts.

    One grouped query: unnest(topics) turns each array element into its own
    row, so a sentence tagged with two topics is counted once under each.
    Topics with no sentences are filled in with zeros, in TOPICS order.
    """
    now = datetime.now(timezone.utc)

    # LATERAL makes the dependency on sentences.topics explicit, so SQLAlchemy
    # sees a real join instead of warning about a cartesian product.
    topic_rows = (
        select(func.unnest(Sentence.topics).column_valued("topic"))
        .lateral("t")
    )
    topic_col = topic_rows.c.topic

    stmt = (
        select(
            topic_col,
            func.count().label("sentence_count"),
            func.count().filter(due_condition(now)).label("due_count"),
        )
        .select_from(Sentence)
        .join(topic_rows, true())
        .where(Sentence.user_id == user_id)
        .group_by(topic_col)
    )

    result = await db.execute(stmt)
    counts = {row[0]: (row.sentence_count, row.due_count) for row in result}

    return [
        TopicOverview(
            topic=topic,
            sentence_count=counts.get(topic, (0, 0))[0],
            due_count=counts.get(topic, (0, 0))[1],
        )
        for topic in TOPICS
    ]