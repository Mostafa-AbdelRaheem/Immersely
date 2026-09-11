# app/services/embeddings.py
import asyncio

from sentence_transformers import SentenceTransformer

_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazily load and cache the embedding model as a module-level singleton."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _encode_sync(text: str) -> list[float]:
    """Blocking call — must only ever run inside asyncio.to_thread()."""
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


async def embed_text(text: str) -> list[float]:
    """Generate a 768-dim embedding for a single piece of text.

    Offloads the blocking sentence-transformers call to a worker thread
    so it doesn't block the event loop.
    """
    return await asyncio.to_thread(_encode_sync, text)