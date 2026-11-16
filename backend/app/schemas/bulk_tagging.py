# app/schemas/bulk_tagging.py
from pydantic import BaseModel, Field

from app.schemas.tagging import Topic


class BatchTagItem(BaseModel):
    """The model's answer for ONE sentence in a chunk."""

    index: int = Field(
        ...,
        description="The label of the sentence this answer belongs to, copied exactly from the input.",
    )
    topics: list[Topic] = Field(
        ...,
        description="One or more topics from the fixed list that best match this sentence.",
    )
    grammar_tag: str | None = Field(
        None,
        description="A short snake_case label for the main German grammar concept, e.g. 'perfekt'. Null if none stands out.",
    )


class BatchTaggingResult(BaseModel):
    """Wrapper object: structured output needs one top-level object."""

    items: list[BatchTagItem] = Field(
        ...,
        description="Exactly one item per input sentence, each with its own index.",
    )