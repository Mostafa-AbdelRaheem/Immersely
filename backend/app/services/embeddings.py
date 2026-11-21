# app/services/embeddings.py
import asyncio
import logging
import threading

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def _get_model() -> SentenceTransformer:
    """Lazily load and cache the embedding model as a module-level singleton."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _encode_sync(text: str) -> list[float]:
    """Blocking call — must only ever run inside asyncio.to_thread()."""
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def _encode_many_sync(texts: list[str]) -> list[list[float]]:
    """Blocking batch call — must only ever run inside asyncio.to_thread()."""
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


async def embed_text(text: str) -> list[float]:
    """Generate a 768-dim embedding for a single piece of text.

    Offloads the blocking sentence-transformers call to a worker thread
    so it doesn't block the event loop.
    """
    return await asyncio.to_thread(_encode_sync, text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate 768-dim embeddings for many texts in one batched model call.

    Returns one vector per input, in input order. An empty input returns []
    without loading the model or starting a thread.
    """
    if not texts:
        return []
    return await asyncio.to_thread(_encode_many_sync, texts)


async def warm_up_model() -> None:
    """Load the model in a worker thread so the first real request is fast.

    Never raises: on failure the model simply stays lazy and loads on first use.
    Logs only the exception type.
    """
    try:
        await asyncio.to_thread(_get_model)
    except Exception as exc:
        logger.warning("embedding model warm-up failed: %s", type(exc).__name__)
