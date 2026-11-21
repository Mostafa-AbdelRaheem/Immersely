# app/services/bulk_tagging.py
"""Batch topic tagging for bulk import (N5c): chunking + per-chunk retries.

Never raises for tagging problems: a sentence that could not be tagged comes
back as None, and the caller shows it as untagged (best-effort, like single
sentence creation).
"""
import logging
from collections.abc import Awaitable, Callable, Sequence

from app.core.config import settings
from app.langchain_.batch_tagging import tag_batch
from app.schemas.bulk_tagging import BatchTaggingResult
from app.services.bulk_tagging_logic import TagOutcome, reconcile

logger = logging.getLogger(__name__)

# Internal safety valve (not a tunable setting): LLM calls per chunk.
MAX_ATTEMPTS_PER_CHUNK = 3

TagBatchFn = Callable[[Sequence[tuple[int, str]]], Awaitable[BatchTaggingResult]]


async def _tag_chunk(
    texts: Sequence[str], tag_fn: TagBatchFn, chunk_number: int
) -> list[TagOutcome | None]:
    # Labels are 1-based and local to this chunk.
    labelled = {label: text for label, text in enumerate(texts, start=1)}
    accepted: dict[int, TagOutcome] = {}
    pending = sorted(labelled)

    for attempt in range(1, MAX_ATTEMPTS_PER_CHUNK + 1):
        if not pending:
            break
        try:
            result = await tag_fn([(label, labelled[label]) for label in pending])
        except Exception as exc:
            # Groq tool/schema failures, 429s and timeouts all land here.
            logger.warning(
                "batch tagging call failed: chunk=%d attempt=%d error=%s",
                chunk_number,
                attempt,
                type(exc).__name__,
            )
            continue
        newly_accepted, pending = reconcile(pending, result.items)
        accepted.update(newly_accepted)

    if pending:
        logger.warning(
            "batch tagging: chunk=%d left %d sentence(s) untagged",
            chunk_number,
            len(pending),
        )
    return [accepted.get(label) for label in sorted(labelled)]


async def tag_sentences(
    texts: Sequence[str],
    *,
    chunk_size: int | None = None,
    tag_fn: TagBatchFn = tag_batch,
) -> list[TagOutcome | None]:
    """One entry per input text, in order: a TagOutcome, or None if untagged."""
    size = chunk_size if chunk_size is not None else settings.bulk_tag_chunk_size
    if size < 1:
        raise ValueError("chunk_size must be at least 1")

    outcomes: list[TagOutcome | None] = []
    for chunk_number, start in enumerate(range(0, len(texts), size), start=1):
        outcomes.extend(await _tag_chunk(texts[start : start + size], tag_fn, chunk_number))
    return outcomes
