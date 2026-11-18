# app/services/sentence_import.py
"""Bulk import preview (N5c): upload bytes -> rows the user can review. Saves nothing.

build_preview() has no DB access: the caller supplies the dedupe keys of the
user's saved sentences. Read/parse errors propagate (the route maps them to
HTTP codes). Tagging problems never raise: that row comes back tagged=False.
"""
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.langchain_.batch_tagging import tag_batch
from app.models.sentence import Sentence
from app.schemas.sentence_import import ImportConfirmRow, ImportPreviewOut, PreviewRow
from app.services.bulk_import_logic import ParsedRow, normalize_for_dedupe, parse_rows
from app.services.bulk_import_reader import read_xlsx_rows
from app.services.bulk_tagging import TagBatchFn, tag_sentences
from app.services.bulk_tagging_logic import TagOutcome
from app.services.embeddings import embed_texts

# Same cap as SentenceCreate (a test guards against drift).
MAX_TEXT_LEN = 2000


def _to_preview_row(row: ParsedRow, outcome: TagOutcome | None) -> PreviewRow:
    return PreviewRow(
        row_number=row.row_number,
        de=row.de,
        en=row.en,
        topics=list(outcome.topics) if outcome else [],
        grammar_tag=outcome.grammar_tag if outcome else None,
        tagged=outcome is not None,
        issues=list(row.issues),
        has_blocking_issue=row.has_blocking_issue,
    )


async def build_preview(
    data: bytes,
    *,
    existing_keys: set[str] | frozenset[str],
    tag_fn: TagBatchFn = tag_batch,
) -> ImportPreviewOut:
    # The reader is blocking (zip + XML parsing), so keep it off the event loop.
    raw_rows = await asyncio.to_thread(
        read_xlsx_rows, data, max_upload_bytes=settings.bulk_import_max_upload_bytes
    )
    parsed = parse_rows(
        raw_rows,
        max_rows=settings.bulk_import_max_rows,
        max_len=MAX_TEXT_LEN,
        existing_keys=existing_keys,
    )

    # Rows that cannot be saved as they stand are not worth LLM tokens.
    # Duplicate-flagged rows ARE tagged: the user may knowingly keep them.
    taggable = [row for row in parsed if not row.has_blocking_issue]
    outcomes = await tag_sentences([row.de for row in taggable], tag_fn=tag_fn)
    outcome_by_row = {
        row.row_number: outcome for row, outcome in zip(taggable, outcomes, strict=True)
    }

    return ImportPreviewOut(
        rows=[_to_preview_row(row, outcome_by_row.get(row.row_number)) for row in parsed]
    )


async def load_existing_keys(db: AsyncSession, user_id: uuid.UUID) -> set[str]:
    """Dedupe keys of the user's saved sentences. Selects only `de`, never embeddings."""
    result = await db.execute(select(Sentence.de).where(Sentence.user_id == user_id))
    return {normalize_for_dedupe(de) for de in result.scalars().all()}


async def confirm_import(
    db: AsyncSession,
    user_id: uuid.UUID,
    rows: list[ImportConfirmRow],
    *,
    embed_fn=embed_texts,
) -> list[Sentence]:
    """Save the reviewed rows in ONE transaction (all or nothing).

    Embeddings are computed first, in one batched call, before the session is
    touched: if that fails, nothing was added. Returns the new sentences in
    file order. Duplicates are not re-checked (the user saw the warnings).
    """
    vectors = await embed_fn([row.de for row in rows])
    sentences = [
        Sentence(
            user_id=user_id,
            de=row.de,
            en=row.en,
            topics=[topic.value for topic in row.topics],
            grammar_tag=row.grammar_tag,
            embedding=vector,
        )
        for row, vector in zip(rows, vectors, strict=True)
    ]
    db.add_all(sentences)
    await db.commit()
    return sentences
