# app/services/chat_logic.py
"""Pure input guards for Conversations. No DB, no LLM, no settings access."""

VALID_ROLES = ("user", "partner")


class ChatInputError(Exception):
    """The client sent a history or message the server refuses to use."""


def sanitize_text(text: str) -> str:
    """Remove angle brackets (they could close a prompt tag) and trim."""
    return text.replace("<", "").replace(">", "").strip()


def validate_history(
    history: list[tuple[str, str]],
    max_messages: int,
    max_chars: int,
) -> list[tuple[str, str]]:
    """Return a cleaned copy of the history, or raise ChatInputError."""
    if not history:
        raise ChatInputError("History is empty.")
    if len(history) > max_messages:
        raise ChatInputError(f"History has more than {max_messages} messages.")

    cleaned: list[tuple[str, str]] = []
    for role, text in history:
        if role not in VALID_ROLES:
            raise ChatInputError(f"Unknown role: {role!r}.")
        clean = sanitize_text(text)
        if not clean:
            raise ChatInputError("A message is empty.")
        if len(clean) > max_chars:
            raise ChatInputError(f"A message is longer than {max_chars} characters.")
        cleaned.append((role, clean))
    return cleaned