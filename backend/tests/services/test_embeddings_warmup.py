# tests/services/test_embeddings_warmup.py
import asyncio
import logging

from app.services import embeddings


def test_warm_up_loads_the_model_once(monkeypatch):
    calls = []
    monkeypatch.setattr(embeddings, "_get_model", lambda: calls.append(1))
    assert asyncio.run(embeddings.warm_up_model()) is None
    assert calls == [1]


def test_warm_up_failure_is_swallowed_and_logs_only_the_type(monkeypatch, caplog):
    def boom():
        raise RuntimeError("SECRET-DETAIL-MARKER")

    monkeypatch.setattr(embeddings, "_get_model", boom)
    with caplog.at_level(logging.WARNING, logger=embeddings.logger.name):
        asyncio.run(embeddings.warm_up_model())
    assert "RuntimeError" in caplog.text
    assert "SECRET-DETAIL-MARKER" not in caplog.text
