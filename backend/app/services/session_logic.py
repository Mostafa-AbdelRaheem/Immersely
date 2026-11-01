# app/services/session_logic.py
from typing import Literal

Method = Literal["scene", "typed"]


def resolve_method(topic: str | None, method: Method | None) -> Method:
    """Decide which kind of session to run.

    method omitted: a topic means scene mode (the original behavior), no topic
    means typed isolated sentences. An explicit method wins, except that a
    scene needs a topic.
    """
    if method is None:
        return "scene" if topic is not None else "typed"
    if method == "scene" and topic is None:
        raise ValueError("scene mode requires a topic")
    return method