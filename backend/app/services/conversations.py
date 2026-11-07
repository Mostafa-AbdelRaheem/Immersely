# app/services/conversations.py
"""One turn of a Conversation: partner reply, correction, and hint chips.

Ungraded: nothing here touches SRS or review_events. The history comes from
the client on every turn (stateless).
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass

from groq import APIConnectionError, APITimeoutError, BadRequestError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.scenarios import SCENARIOS_BY_ID
from app.langchain_.chat_correction import judge_chat_message
from app.langchain_.conversation_partner import generate_partner_reply
from app.models.sentence import Sentence
from app.schemas.chat_correction import ChatCorrectionJudgment
from app.services.chat_logic import (
    ChatInputError,
    ChatOutputError,
    check_partner_reply,
    normalize_chat_correction,
    select_within_cutoff,
    validate_history,
)
from app.services.conversation_retrieval import find_similar_sentences

logger = logging.getLogger(__name__)

# The Groq SDK already retries 429/408/409/5xx twice (max_retries=2), so these
# are the failures that remain AFTER its retries. We add no retry loop of our own.
_BUSY_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError)
# BadRequestError = the structured-output tool-call failures seen in M5/M6.
_CORRECTION_ERRORS = _BUSY_ERRORS + (BadRequestError,)


class UnknownScenarioError(Exception):
    """The scenario id is not in the fixed scenario list."""


class ChatServiceBusyError(Exception):
    """The LLM provider failed (rate limit, timeout, connection) for the partner."""


@dataclass(frozen=True)
class TurnResult:
    partner_reply: str
    correction: ChatCorrectionJudgment | None
    chips: list[Sentence]


async def _no_correction() -> None:
    return None


def _last_partner_line(history: list[tuple[str, str]]) -> str | None:
    for role, text in reversed(history[:-1]):
        if role == "partner":
            return text
    return None


async def run_turn(
    db: AsyncSession,
    user_id: uuid.UUID,
    scenario_id: str,
    raw_history: list[tuple[str, str]],
) -> TurnResult:
    scenario = SCENARIOS_BY_ID.get(scenario_id)
    if scenario is None:
        raise UnknownScenarioError(scenario_id)

    # An empty history is the opening turn; otherwise validate what the client sent.
    if raw_history:
        history = validate_history(
            raw_history,
            settings.chat_max_history_messages,
            settings.chat_max_message_chars,
        )
        if history[-1][0] != "user":
            raise ChatInputError("History must end with a learner message.")
        query = history[-1][1]
    else:
        history = []
        query = scenario.situation

    # 1. Retrieval for the partner (sequential, before any concurrent work).
    found = await find_similar_sentences(
        db, user_id, query, k=settings.chat_max_partner_sentences
    )
    partner_sentences = select_within_cutoff(
        found,
        settings.chat_retrieval_max_distance,
        settings.chat_max_partner_sentences,
    )

    # 2. Partner and corrector are independent: run them together.
    partner_line = _last_partner_line(history) if history else None
    if history and partner_line is not None:
        correction_call = judge_chat_message(
            partner_line=partner_line, learner_message=history[-1][1]
        )
    else:
        correction_call = _no_correction()

    partner_raw, correction_raw = await asyncio.gather(
        generate_partner_reply(scenario, history, partner_sentences),
        correction_call,
        return_exceptions=True,
    )

    # 3. Partner: failure fails the turn.
    if isinstance(partner_raw, _BUSY_ERRORS):
        logger.warning("Partner call failed: %s: %s", type(partner_raw).__name__, partner_raw)
        raise ChatServiceBusyError("The chat service is busy, try again.") from partner_raw
    if isinstance(partner_raw, BaseException):
        raise partner_raw
    partner_reply = check_partner_reply(partner_raw, [s.de for s in partner_sentences])

    # 4. Corrector: best-effort, a failure means correction=None.
    correction: ChatCorrectionJudgment | None = None
    if isinstance(correction_raw, _CORRECTION_ERRORS):
        logger.warning(
            "Correction call failed: %s: %s", type(correction_raw).__name__, correction_raw
        )
    elif isinstance(correction_raw, BaseException):
        raise correction_raw
    elif correction_raw is not None:
        try:
            correction = normalize_chat_correction(correction_raw, history[-1][1])
        except ChatOutputError as exc:
            logger.warning("Correction rejected by guard: %s", exc)

    # 5. Chips: retrieved with the partner's NEW line as the query.
    chip_found = await find_similar_sentences(
        db, user_id, partner_reply, k=settings.chat_max_chips
    )
    chips = select_within_cutoff(
        chip_found,
        settings.chat_retrieval_max_distance,
        settings.chat_max_chips,
    )

    return TurnResult(partner_reply=partner_reply, correction=correction, chips=chips)