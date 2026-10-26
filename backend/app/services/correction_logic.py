# app/services/correction_logic.py
from app.schemas.correction import CorrectionJudgment, CorrectionLLMOutput, GrammarVerdict, Tier
from app.schemas.srs import Grade

class MalformedCorrectionError(Exception):
    """The LLM output parsed against the schema but is inconsistent with its
    own tier, or is missing fields that its tier requires."""


def suggest_grade(tier: Tier, very_close: bool) -> Grade:
    """Tier -> suggested SRS grade. The only place a grade is derived;
    rule_practiced never influences it."""
    if tier is Tier.CORRECT:
        return Grade.EASY if very_close else Grade.GOOD
    if tier is Tier.ALMOST_CORRECT:
        return Grade.HARD
    return Grade.AGAIN


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.strip()
    return text or None


def normalize_correction(
    raw: CorrectionLLMOutput,
    *,
    user_answer: str,
    has_rule: bool,
) -> CorrectionLLMOutput:
    """Enforce tier-consistency on raw LLM output.

    Returns a cleaned copy, or raises MalformedCorrectionError if the output
    can't be trusted (the caller's retry loop should re-ask the model).
    """
    tier = raw.tier

    # incorrect: the model answer is shown instead; nothing else applies.
    if tier is Tier.INCORRECT:
        return CorrectionLLMOutput(tier=tier, very_close=False)

    corrected: str | None = None
    diff_note: str | None = None
    very_close = False

    if tier is Tier.ALMOST_CORRECT:
        corrected = _clean(raw.corrected_sentence)
        diff_note = _clean(raw.diff_note)
        if corrected is None or diff_note is None:
            raise MalformedCorrectionError(
                "almost_correct requires both corrected_sentence and diff_note"
            )
        if corrected == user_answer.strip():
            raise MalformedCorrectionError(
                "almost_correct but corrected_sentence equals the user's answer"
            )
    else:  # Tier.CORRECT
        very_close = raw.very_close

    rule_practiced: bool | None = None
    rule_note: str | None = None
    if has_rule:
        if raw.rule_practiced is None:
            raise MalformedCorrectionError(
                "rule_practiced missing although the sentence has a grammar rule"
            )
        rule_practiced = raw.rule_practiced
        if rule_practiced is False:
            rule_note = _clean(raw.rule_note)

    return CorrectionLLMOutput(
        tier=tier,
        very_close=very_close,
        corrected_sentence=corrected,
        diff_note=diff_note,
        rule_practiced=rule_practiced,
        rule_note=rule_note,
    )

def derive_tier(j: CorrectionJudgment) -> Tier:
    """The tier is derived, never asked for directly."""
    if not j.same_intent or j.grammar_verdict is GrammarVerdict.BROKEN:
        return Tier.INCORRECT
    if j.grammar_verdict is GrammarVerdict.FIXABLE_ERRORS:
        return Tier.ALMOST_CORRECT
    return Tier.CORRECT


def judgment_to_output(j: CorrectionJudgment) -> CorrectionLLMOutput:
    """Bridge into the step 2 shape; normalize_correction then guards it."""
    return CorrectionLLMOutput(
        tier=derive_tier(j),
        very_close=j.very_close,
        corrected_sentence=j.corrected_sentence,
        diff_note=j.diff_note,
        rule_practiced=j.rule_practiced,
        rule_note=j.rule_note,
    )