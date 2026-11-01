# app/services/article_logic.py
"""Pure verification for generated Read articles. No DB, no LLM, no I/O,
so every rule is unit-tested without mocks."""
import uuid

from app.schemas.article_generation import ArticleOutput


def verify_article(
    output: ArticleOutput,
    supplied_ids: list[uuid.UUID],
    min_chars: int,
    max_chars: int,
) -> str | None:
    """Returns None if the article passes, otherwise a short reason."""
    text_de = output.text_de.strip()
    if not output.title.strip():
        return "empty title"
    if not text_de:
        return "empty text_de"
    if not output.text_en.strip():
        return "empty text_en"

    length = len(text_de)
    if length < min_chars:
        return f"too short: {length} chars (min {min_chars})"
    if length > max_chars:
        return f"too long: {length} chars (max {max_chars})"

    supplied = {str(i) for i in supplied_ids}
    used = set(output.used_sentence_ids)

    invented = used - supplied
    if invented:
        return f"invented ids: {sorted(invented)}"

    missing = supplied - used
    if missing:
        return f"missing ids: {sorted(missing)}"

    return None