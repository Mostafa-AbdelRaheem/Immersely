# app/langchain_/topic_tagging.py
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.topics import TOPICS
from app.schemas.tagging import TopicTaggingResult

_TOPIC_LIST_TEXT = ", ".join(TOPICS)

_SYSTEM_PROMPT = f"""You are a German language-learning assistant. Given a \
German sentence, classify it against a fixed set of topics and identify its \
main grammar concept.

Available topics (choose only from this list): {_TOPIC_LIST_TEXT}

Rules:
- Assign one or more topics that genuinely fit the sentence's meaning. Do \
not force-fit an unrelated topic.
- If none of the available topics fit well, still pick the closest one(s), \
but also set suggested_new_topic to a short snake_case name for a topic \
you think is missing.
- grammar_tag should name the single most notable grammar concept in the \
sentence (e.g. tense, case, mood), or be null if nothing stands out.
"""

_chain = None


def _get_chain():
    global _chain
    if _chain is None:
        llm = ChatGroq(
            model="qwen/qwen3.6-27b",
            api_key=settings.groq_api_key,
            temperature=0,
            reasoning_effort="none",
            reasoning_format="hidden",
        )
        _chain = llm.with_structured_output(TopicTaggingResult)
    return _chain


async def tag_sentence(de_text: str) -> TopicTaggingResult:
    chain = _get_chain()
    return await chain.ainvoke(
        [
            ("system", _SYSTEM_PROMPT),
            ("human", de_text),
        ]
    )