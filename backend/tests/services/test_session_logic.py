# tests/services/test_session_logic.py
import pytest

from app.services.session_logic import resolve_method


@pytest.mark.parametrize(
    "topic, method, expected",
    [
        ("shopping", None, "scene"),      # original behavior
        (None, None, "typed"),            # original behavior
        ("shopping", "typed", "typed"),   # new: typed for one topic
        (None, "typed", "typed"),
        ("shopping", "scene", "scene"),
    ],
)
def test_resolve_method(topic, method, expected):
    assert resolve_method(topic, method) == expected


def test_scene_without_topic_is_an_error():
    with pytest.raises(ValueError):
        resolve_method(None, "scene")