# app/schemas/topics.py
from pydantic import BaseModel


class TopicOverview(BaseModel):
    """One card on the topic hub: a topic plus the current user's counts.

    sentence_count: all of the user's sentences tagged with this topic.
    due_count: the subset that is due right now (per srs.due_condition).
    A topic with no sentences is still returned, with both counts at 0.
    """

    topic: str
    sentence_count: int
    due_count: int