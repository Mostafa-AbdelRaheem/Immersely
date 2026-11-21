# tests/services/test_embeddings.py
import asyncio

import numpy as np

from app.services import embeddings


class FakeModel:
    """Fake SentenceTransformer: row i encodes the text's length, so order is checkable."""

    def __init__(self):
        self.calls = []

    def encode(self, texts, convert_to_numpy=True):
        self.calls.append(texts)
        return np.array([[float(len(t)), 0.5] for t in texts])


def _install(monkeypatch):
    model = FakeModel()
    loads = []

    def fake_get_model():
        loads.append(1)
        return model

    monkeypatch.setattr(embeddings, "_get_model", fake_get_model)
    return model, loads


def test_empty_input_returns_empty_without_loading_model(monkeypatch):
    model, loads = _install(monkeypatch)
    assert asyncio.run(embeddings.embed_texts([])) == []
    assert loads == []
    assert model.calls == []


def test_model_called_once_with_whole_list(monkeypatch):
    model, _ = _install(monkeypatch)
    texts = ["a", "bb", "ccc"]
    asyncio.run(embeddings.embed_texts(texts))
    assert model.calls == [texts]


def test_results_keep_input_order_and_are_plain_lists(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(embeddings.embed_texts(["ccc", "a", "bb"]))
    assert result == [[3.0, 0.5], [1.0, 0.5], [2.0, 0.5]]
    assert isinstance(result, list) and isinstance(result[0], list)
