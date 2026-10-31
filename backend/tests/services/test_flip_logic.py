# tests/services/test_flip_logic.py
import pytest

from app.schemas.correction import Tier
from app.schemas.srs import Grade
from app.services.flip_logic import grade_to_tier


@pytest.mark.parametrize(
    "grade, expected",
    [
        (Grade.AGAIN, Tier.INCORRECT),
        (Grade.HARD, Tier.ALMOST_CORRECT),
        (Grade.GOOD, Tier.CORRECT),
        (Grade.EASY, Tier.CORRECT),
    ],
)
def test_grade_to_tier(grade, expected):
    assert grade_to_tier(grade) == expected


def test_every_grade_has_a_tier():
    # Guards against adding a Grade later and forgetting the mapping.
    for grade in Grade:
        assert isinstance(grade_to_tier(grade), Tier)