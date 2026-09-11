# app/schemas/tagging.py
from enum import Enum

from pydantic import BaseModel, Field

from app.core.topics import TOPICS

# Built dynamically from TOPICS so the enum and the source list can never
# drift out of sync with each other.
Topic = Enum("Topic", {t.upper(): t for t in TOPICS}, type=str)


class TopicTaggingResult(BaseModel):
    topics: list[Topic] = Field(
        ...,
        description="One or more topics from the fixed list that best match the sentence's meaning and context.",
    )
    grammar_tag: str | None = Field(
        None,
        description="A short snake_case label for the main German grammar concept this sentence demonstrates, e.g. 'subjunctive_ii', 'perfekt', 'dative_case'. Null if no single grammar concept stands out.",
    )
    suggested_new_topic: str | None = Field(
        None,
        description="If none of the fixed topics fit this sentence well, suggest a new topic name here for manual review. Null if an existing topic fits adequately.",
    )