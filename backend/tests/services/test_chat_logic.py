# tests/services/test_chat_logic.py
import pytest

from app.schemas.chat_correction import ChatCorrectionJudgment
from app.schemas.correction import GrammarVerdict
from app.services.chat_logic import (
    ChatInputError,
    ChatOutputError,
    check_partner_reply,
    normalize_chat_correction,
    sanitize_text,
    validate_history,
)


# ---------- input guards ----------

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


# ---------- normalize_chat_correction ----------

def make(verdict, corrected=None, note=None):
    return ChatCorrectionJudgment(
        analysis="a",
        grammar_verdict=verdict,
        corrected_text=corrected,
        note=note,
    )


def test_fixable_returns_sanitized_correction():
    j = make(GrammarVerdict.FIXABLE_ERRORS, "Er arbeitet.<", "Verb ending.")
    result = normalize_chat_correction(j, "Er arbeiten.")
    assert result.corrected_text == "Er arbeitet."


def test_fixable_keeps_note():
    j = make(GrammarVerdict.FIXABLE_ERRORS, "Er arbeitet.", "Verb ending.")
    assert normalize_chat_correction(j, "Er arbeiten.").note == "Verb ending."


def test_fixable_without_correction_raises():
    with pytest.raises(ChatOutputError):
        normalize_chat_correction(make(GrammarVerdict.FIXABLE_ERRORS), "Er arbeiten.")


def test_fixable_with_blank_correction_raises():
    with pytest.raises(ChatOutputError):
        normalize_chat_correction(make(GrammarVerdict.FIXABLE_ERRORS, "  "), "Er arbeiten.")


def test_fixable_identical_correction_raises():
    with pytest.raises(ChatOutputError):
        normalize_chat_correction(
            make(GrammarVerdict.FIXABLE_ERRORS, "Er arbeiten."), "Er arbeiten."
        )


def test_fixable_identical_ignoring_whitespace_raises():
    with pytest.raises(ChatOutputError):
        normalize_chat_correction(
            make(GrammarVerdict.FIXABLE_ERRORS, " Er arbeiten. "), "Er arbeiten."
        )


def test_valid_drops_correction_and_note():
    j = make(GrammarVerdict.VALID, "x", "y")
    result = normalize_chat_correction(j, "Hi")
    assert result.corrected_text is None
    assert result.note is None


def test_broken_drops_correction_but_keeps_note():
    j = make(GrammarVerdict.BROKEN, "x", "Try a full sentence.")
    result = normalize_chat_correction(j, "Hi")
    assert result.corrected_text is None
    assert result.note == "Try a full sentence."


def test_normalize_does_not_mutate_input():
    j = make(GrammarVerdict.VALID, "x", "y")
    normalize_chat_correction(j, "Hi")
    assert j.corrected_text == "x"
    assert j.note == "y"


# ---------- check_partner_reply ----------

SAVED = ["Ich habe eine Aufgabe bis Freitag."]


def test_reply_is_returned_cleaned():
    assert check_partner_reply("  Hallo <b>Welt  ", []) == "Hallo bWelt"


def test_empty_reply_rejected():
    with pytest.raises(ChatOutputError):
        check_partner_reply("   ", [])


def test_reply_of_only_brackets_rejected():
    with pytest.raises(ChatOutputError):
        check_partner_reply("<>", [])


def test_verbatim_saved_sentence_rejected():
    with pytest.raises(ChatOutputError):
        check_partner_reply("Ich habe eine Aufgabe bis Freitag, sagt er.", SAVED)


def test_verbatim_check_ignores_case_and_final_punctuation():
    with pytest.raises(ChatOutputError):
        check_partner_reply("ICH HABE EINE AUFGABE BIS FREITAG!", SAVED)


def test_partial_overlap_is_allowed():
    reply = "Gerne! Ich habe heute eine Aufgabe bis Freitag."
    assert check_partner_reply(reply, SAVED) == reply


def test_short_saved_sentence_is_not_checked():
    assert check_partner_reply("Ja, gerne, sagt er.", ["Ja, gerne."]) == "Ja, gerne, sagt er."


def test_four_word_saved_sentence_is_checked():
    with pytest.raises(ChatOutputError):
        check_partner_reply("Ich bin sehr müde, sagt er.", ["Ich bin sehr müde."])


def test_three_word_saved_sentence_is_not_checked():
    reply = "Ich bin müde, sagt er."
    assert check_partner_reply(reply, ["Ich bin müde."]) == reply