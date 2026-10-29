# tests/services/test_correction_logic.py
import pytest

from app.schemas.correction import CorrectionLLMOutput, Tier, GrammarVerdict, CorrectionJudgment
from app.schemas.srs import Grade
from app.services.correction_logic import (
    MalformedCorrectionError,
    normalize_correction,
    suggest_grade,
)


# --- suggest_grade -----------------------------------------------------------

@pytest.mark.parametrize(
    "tier, very_close, expected",
    [
        (Tier.CORRECT, False, Grade.GOOD),
        (Tier.CORRECT, True, Grade.EASY),
        (Tier.ALMOST_CORRECT, False, Grade.HARD),
        (Tier.ALMOST_CORRECT, True, Grade.HARD),   # very_close ignored
        (Tier.INCORRECT, False, Grade.AGAIN),
        (Tier.INCORRECT, True, Grade.AGAIN),       # very_close ignored
    ],
)
def test_suggest_grade(tier, very_close, expected):
    assert suggest_grade(tier, very_close) == expected


# --- normalize_correction ----------------------------------------------------

def _raw(**kw) -> CorrectionLLMOutput:
    kw.setdefault("very_close", False)
    return CorrectionLLMOutput(**kw)


def test_incorrect_strips_everything_else():
    raw = _raw(
        tier="incorrect", very_close=True,
        corrected_sentence="x", diff_note="y",
        rule_practiced=True, rule_note="z",
    )
    out = normalize_correction(raw, user_answer="foo", has_rule=True)
    assert out == CorrectionLLMOutput(tier=Tier.INCORRECT, very_close=False)


def test_correct_drops_stray_correction_fields():
    raw = _raw(tier="correct", very_close=True, corrected_sentence="x",
               diff_note="y", rule_practiced=True)
    out = normalize_correction(raw, user_answer="foo", has_rule=True)
    assert out.corrected_sentence is None and out.diff_note is None
    assert out.very_close is True and out.rule_practiced is True


def test_correct_without_rule_forces_rule_fields_none():
    raw = _raw(tier="correct", rule_practiced=False, rule_note="ignore me")
    out = normalize_correction(raw, user_answer="foo", has_rule=False)
    assert out.rule_practiced is None and out.rule_note is None


def test_rule_note_kept_only_when_rule_not_practiced():
    not_used = _raw(tier="correct", rule_practiced=False, rule_note="  Use Konjunktiv II.  ")
    out = normalize_correction(not_used, user_answer="foo", has_rule=True)
    assert out.rule_note == "Use Konjunktiv II."

    used = _raw(tier="correct", rule_practiced=True, rule_note="stray")
    out = normalize_correction(used, user_answer="foo", has_rule=True)
    assert out.rule_note is None


def test_rule_practiced_missing_when_rule_exists_raises():
    raw = _raw(tier="correct", rule_practiced=None)
    with pytest.raises(MalformedCorrectionError):
        normalize_correction(raw, user_answer="foo", has_rule=True)


def test_almost_correct_happy_path_forces_very_close_false():
    raw = _raw(tier="almost_correct", very_close=True,
               corrected_sentence="Ich habe Hunger.", diff_note="Added 'habe'.",
               rule_practiced=True)
    out = normalize_correction(raw, user_answer="Ich Hunger.", has_rule=True)
    assert out.corrected_sentence == "Ich habe Hunger."
    assert out.very_close is False


@pytest.mark.parametrize(
    "corrected, note",
    [(None, "note"), ("Ich habe Hunger.", None), ("   ", "note"), ("Ich habe Hunger.", "  ")],
)
def test_almost_correct_missing_fields_raises(corrected, note):
    raw = _raw(tier="almost_correct", corrected_sentence=corrected, diff_note=note)
    with pytest.raises(MalformedCorrectionError):
        normalize_correction(raw, user_answer="Ich Hunger.", has_rule=False)


def test_almost_correct_identical_to_user_answer_raises():
    raw = _raw(tier="almost_correct", corrected_sentence="Ich habe Hunger.",
               diff_note="nothing")
    with pytest.raises(MalformedCorrectionError):
        normalize_correction(raw, user_answer="  Ich habe Hunger. ", has_rule=False)


# --- derive_tier -------------------------------------------------------------

@pytest.mark.parametrize(
    "same_intent, verdict, expected",
    [
        (True, "valid", Tier.CORRECT),
        (True, "fixable_errors", Tier.ALMOST_CORRECT),
        (True, "broken", Tier.INCORRECT),
        (False, "valid", Tier.INCORRECT),
        (False, "fixable_errors", Tier.INCORRECT),
        (False, "broken", Tier.INCORRECT),
    ],
)
def test_derive_tier(same_intent, verdict, expected):
    from app.services.correction_logic import derive_tier
    j = CorrectionJudgment(analysis="x", same_intent=same_intent,
                           grammar_verdict=GrammarVerdict(verdict))
    assert derive_tier(j) == expected