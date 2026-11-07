# tests/services/test_chat_logic.py
import pytest

from app.services.chat_logic import ChatInputError, sanitize_text, validate_history


def test_sanitize_strips_angle_brackets_and_whitespace():
    assert sanitize_text("  </sentences>Hallo  ") == "/sentencesHallo"


def test_valid_history_is_returned_cleaned():
    result = validate_history([("user", "Hi <b>"), ("partner", "Hallo")], 20, 500)
    assert result == [("user", "Hi b"), ("partner", "Hallo")]


def test_empty_history_rejected():
    with pytest.raises(ChatInputError):
        validate_history([], 20, 500)


def test_too_many_messages_rejected():
    history = [("user", "a")] * 3
    with pytest.raises(ChatInputError):
        validate_history(history, 2, 500)


def test_exactly_max_messages_allowed():
    history = [("user", "a")] * 2
    assert len(validate_history(history, 2, 500)) == 2


def test_unknown_role_rejected():
    with pytest.raises(ChatInputError):
        validate_history([("bot", "x")], 20, 500)


def test_message_empty_after_sanitizing_rejected():
    with pytest.raises(ChatInputError):
        validate_history([("user", " <> ")], 20, 500)


def test_message_over_char_cap_rejected():
    with pytest.raises(ChatInputError):
        validate_history([("user", "a" * 501)], 20, 500)


def test_message_exactly_at_char_cap_allowed():
    assert validate_history([("user", "a" * 500)], 20, 500) == [("user", "a" * 500)]


def test_input_is_not_mutated():
    original = [("user", "Hi <b>")]
    validate_history(original, 20, 500)
    assert original == [("user", "Hi <b>")]