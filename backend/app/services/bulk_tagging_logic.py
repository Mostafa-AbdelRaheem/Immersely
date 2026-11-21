# app/services/bulk_tagging_logic.py
"""Pure logic for batch topic tagging (N5c): no LLM, no DB, no I/O."""
from collections import Counter
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass

from app.schemas.bulk_tagging import BatchTagItem

# Mirrors the cap on SentenceUpdate.grammar_tag (a test guards against drift).
MAX_GRAMMAR_TAG_LEN = 100


@dataclass(frozen=True)
class TagOutcome:
    topics: tuple[str, ...]
    grammar_tag: str | None


def normalize_grammar_tag(value: str | None) -> str | None:
    """Trim; blank or over-long values become None (never truncated)."""
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed or len(trimmed) > MAX_GRAMMAR_TAG_LEN:
        return None
    return trimmed


def normalize_topics(topics: Iterable) -> tuple[str, ...]:
    """Plain strings, duplicates removed, first-seen order kept."""
    unique: dict[str, None] = {}
    for topic in topics:
        unique.setdefault(getattr(topic, "value", topic), None)
    return tuple(unique)


def reconcile(
    sent_indices: Collection[int], items: Sequence[BatchTagItem]
) -> tuple[dict[int, TagOutcome], list[int]]:
    """Split a model reply into (accepted by label, sorted missing labels)."""
    wanted = set(sent_indices)
    counts = Counter(item.index for item in items if item.index in wanted)

    accepted: dict[int, TagOutcome] = {}
    for item in items:
        if item.index not in wanted or counts[item.index] != 1:
            continue  # never sent, or answered more than once
        topics = normalize_topics(item.topics)
        if not topics:
            continue  # empty topics violate the prompt: treat as missing
        accepted[item.index] = TagOutcome(
            topics=topics, grammar_tag=normalize_grammar_tag(item.grammar_tag)
        )

    missing = sorted(wanted - accepted.keys())
    return accepted, missing