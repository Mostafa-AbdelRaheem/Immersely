# tests/services/test_embeddings_lock.py
import threading
import time

from app.services import embeddings


def test_concurrent_first_calls_build_the_model_once(monkeypatch):
    builds = []

    def slow_constructor(name):
        builds.append(name)
        time.sleep(0.2)  # widens the race window so a missing lock shows up
        return object()

    monkeypatch.setattr(embeddings, "SentenceTransformer", slow_constructor)
    monkeypatch.setattr(embeddings, "_model", None)

    n_threads = 8
    barrier = threading.Barrier(n_threads)
    results = []

    def worker():
        barrier.wait()  # release all threads at the same moment
        results.append(embeddings._get_model())

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(builds) == 1
    assert len(results) == n_threads
    assert all(r is results[0] for r in results)
