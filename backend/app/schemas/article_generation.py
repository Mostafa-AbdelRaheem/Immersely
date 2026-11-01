# app/schemas/article_generation.py
from pydantic import BaseModel, Field


class ArticleOutput(BaseModel):
    """What the LLM returns for one Read article. Mirrors the style of
    schemas/scene_generation.py: a structured-output schema, validated by
    Pydantic, with every field described so the model knows what to fill."""

    title: str = Field(
        ...,
        description="A short German title for the article, at most 60 characters.",
    )
    text_de: str = Field(
        ...,
        description=(
            "The full article in German. Paragraphs are separated by a blank "
            "line. It must naturally include every provided sentence "
            "(near-verbatim, minor conjugation changes allowed) and may add "
            "connecting text so the article reads coherently."
        ),
    )
    text_en: str = Field(
        ...,
        description="A faithful English translation of text_de, with the same paragraph breaks.",
    )
    used_sentence_ids: list[str] = Field(
        ...,
        description=(
            "The ids (as strings) of every provided sentence that appears in "
            "the article. Only ids from the provided list; never invent ids."
        ),
    )