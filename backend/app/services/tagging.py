# app/services/tagging.py
from app.langchain_.topic_tagging import tag_sentence as _tag_sentence
from app.schemas.tagging import TopicTaggingResult


class TaggingError(Exception):
    pass


async def tag_sentence(de_text: str) -> TopicTaggingResult:
    try:
        return await _tag_sentence(de_text)
    except Exception as exc:
        raise TaggingError(f"Failed to tag sentence: {exc}") from exc