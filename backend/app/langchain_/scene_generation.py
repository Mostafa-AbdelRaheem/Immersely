# app/langchain_/scene_generation.py
from app.models.sentence import Sentence

from langchain_groq import ChatGroq

from app.core.config import settings
from app.schemas.scene_generation import SceneGenerationOutput
from app.schemas.scene_generation import SceneSemanticVerificationOutput

_SYSTEM_PROMPT = """You are a German language-learning content writer. You \
build short scenes (a dialogue between 2+ speakers, or a short narrative/\
monologue — your choice, whichever fits the sentences better) that weave \
together a set of required German target sentences.

Rules:
- Every target sentence MUST appear in the scene, each as its own line, \
worded near-verbatim to the original — minor conjugation changes (e.g. \
tense agreement, pronoun agreement with context) are allowed, but do not \
change the sentence's core wording, vocabulary, or meaning.
- For every line that is a target sentence, set target_sentence_id to that \
sentence's id (given below). For every other line (connective narration, \
a second speaker's replies, filler for natural flow), set \
target_sentence_id to null.
- You may optionally use the provided padding sentences for extra flavor \
and natural flow. Padding sentences are optional and do not need their own \
target_sentence_id — if you use one, still set target_sentence_id to null \
for that line, since padding is never a target.
- Keep the scene short and natural — roughly {target_count} to \
{max_lines} lines total.
- Every line needs both a German (text_de) and English (text_en) version.
- Write entirely in the requested topic's everyday register, suitable for \
a language learner.

Topic: {topic}

Required target sentences (id: German text):
{targets_block}

Optional padding sentences for flavor only (id: German text):
{padding_block}
"""


def _format_sentence_block(sentences: list[Sentence]) -> str:
    if not sentences:
        return "(none)"
    return "\n".join(f"- {s.id}: {s.de}" for s in sentences)


def build_scene_prompt(
    topic: str, targets: list[Sentence], padding: list[Sentence]
) -> list[tuple[str, str]]:
    system = _SYSTEM_PROMPT.format(
        topic=topic,
        target_count=len(targets),
        max_lines=len(targets) * 3,
        targets_block=_format_sentence_block(targets),
        padding_block=_format_sentence_block(padding),
    )
    return [("system", system), ("human", "Generate the scene now.")]

# app/langchain_/scene_generation.py  (the _get_chain/generate_scene part)


_chain = None


def _get_chain():
    global _chain
    if _chain is None:
        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            api_key=settings.groq_api_key,
            temperature=0.7,
            reasoning_effort="low",
            reasoning_format="hidden",
        )
        _chain = llm.with_structured_output(SceneGenerationOutput)
    return _chain


async def generate_scene(
    topic: str, targets: list[Sentence], padding: list[Sentence]
) -> SceneGenerationOutput:
    chain = _get_chain()
    messages = build_scene_prompt(topic, targets, padding)
    return await chain.ainvoke(messages)



_SEMANTIC_CHECK_SYSTEM_PROMPT = """You are checking whether generated \
dialogue lines faithfully preserve the meaning of required target \
sentences. Minor conjugation or tense changes (e.g. to fit dialogue \
context) are allowed and should still count as preserved. A line only \
fails if its core meaning, vocabulary, or intent has meaningfully changed \
from the original target sentence.

For each pair below (target sentence id, original German, generated \
line), decide if the meaning was preserved.
"""

_verification_chain = None


def _get_verification_chain():
    global _verification_chain
    if _verification_chain is None:
        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            api_key=settings.groq_api_key,
            temperature=0,
            reasoning_effort="low",
            reasoning_format="hidden",
        )
        _verification_chain = llm.with_structured_output(
            SceneSemanticVerificationOutput
        )
    return _verification_chain


async def verify_semantic_preservation(
    targets: list[Sentence], generated: SceneGenerationOutput
) -> SceneSemanticVerificationOutput:
    """Checks, for each line claiming a target id, whether that line's
    text_de still preserves the target sentence's meaning."""
    target_by_id = {str(t.id): t for t in targets}
    pairs = [
        (target_by_id[line.target_sentence_id], line)
        for line in generated.lines
        if line.target_sentence_id in target_by_id
    ]

    if not pairs:
        return SceneSemanticVerificationOutput(results=[])

    pairs_block = "\n".join(
        f"- id: {target.id}\n  original: {target.de}\n  generated_line: {line.text_de}"
        for target, line in pairs
    )

    chain = _get_verification_chain()
    return await chain.ainvoke(
        [
            ("system", _SEMANTIC_CHECK_SYSTEM_PROMPT),
            ("human", pairs_block),
        ]
    )