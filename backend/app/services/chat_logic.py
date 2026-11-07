# app/services/chat_logic.py
"""Pure guards for Conversations. No DB, no LLM, no settings access.

Input guards protect us from the client (ChatInputError); output guards
protect us from the model (ChatOutputError).
"""
from app.schemas.chat_correction import ChatCorrectionJudgment
from app.schemas.correction import GrammarVerdict

VALID_ROLES = ("user", "partner")

# Saved sentences shorter than this (in words) are too generic to count as
# "copied verbatim" (e.g. "Ja, gerne." appears naturally in many replies).
MIN_WORDS_FOR_LEAK_CHECK = 4


class ChatInputError(Exception):
    """The client sent a history or message the server refuses to use."""


class ChatOutputError(Exception):
    """The model returned output that is inconsistent or unusable."""


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


def normalize_chat_correction(
    judgment: ChatCorrectionJudgment,
    learner_message: str,
) -> ChatCorrectionJudgment:
    """Make the correction consistent with its verdict, or raise.

    fixable_errors needs a real, different corrected_text (else the model
    contradicted itself: raise). valid/broken must carry no correction, and
    valid must carry no note: those are dropped, since the verdict is the
    signal we trust.
    """
    verdict = judgment.grammar_verdict
    corrected = judgment.corrected_text
    note = judgment.note

    if verdict == GrammarVerdict.FIXABLE_ERRORS:
        corrected = sanitize_text(corrected) if corrected else ""
        if not corrected:
            raise ChatOutputError("fixable_errors without a corrected_text.")
        if corrected == learner_message.strip():
            raise ChatOutputError("corrected_text is identical to the message.")
    else:
        corrected = None
        if verdict == GrammarVerdict.VALID:
            note = None

    return judgment.model_copy(update={"corrected_text": corrected, "note": note})


def check_partner_reply(reply: str, saved_sentences: list[str]) -> str:
    """Return the cleaned partner reply, or raise ChatOutputError."""
    clean = sanitize_text(reply)
    if not clean:
        raise ChatOutputError("Partner reply is empty.")

    haystack = clean.lower()
    for sentence in saved_sentences:
        needle = sentence.strip().rstrip(".!?").strip().lower()
        if len(needle.split()) >= MIN_WORDS_FOR_LEAK_CHECK and needle in haystack:
            raise ChatOutputError("Partner reply copies a saved sentence verbatim.")
    return clean