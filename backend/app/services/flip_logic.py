# app/services/flip_logic.py
from app.schemas.correction import Tier
from app.schemas.srs import Grade

# Flip cards are self-graded, so there is no AI verdict. The tier column is
# NOT NULL, so the server derives it from the grade the user chose.
_GRADE_TO_TIER: dict[Grade, Tier] = {
    Grade.AGAIN: Tier.INCORRECT,
    Grade.HARD: Tier.ALMOST_CORRECT,
    Grade.GOOD: Tier.CORRECT,
    Grade.EASY: Tier.CORRECT,
}


def grade_to_tier(grade: Grade) -> Tier:
    """Map a self-assigned grade to the tier stored on the review event."""
    return _GRADE_TO_TIER[grade]