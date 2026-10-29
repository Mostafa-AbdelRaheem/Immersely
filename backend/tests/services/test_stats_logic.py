import pytest

from app.services.stats_logic import (
    TierCounts,
    accuracy,
    counts_from_tier_rows,
)


def test_accuracy_matches_real_baseline():
    # The 10 real events from the M7 testing: 5 correct, 5 almost, 0 incorrect.
    assert accuracy(TierCounts(correct=5, almost_correct=5, incorrect=0)) == 0.75


def test_accuracy_empty_is_none_not_zero():
    assert accuracy(TierCounts()) is None


def test_accuracy_extremes():
    assert accuracy(TierCounts(correct=3)) == 1.0
    assert accuracy(TierCounts(incorrect=3)) == 0.0


def test_accuracy_partial_credit_for_almost_correct():
    assert accuracy(TierCounts(almost_correct=2)) == 0.5


def test_counts_add():
    total = TierCounts(1, 2, 3) + TierCounts(4, 5, 6)
    assert total == TierCounts(5, 7, 9)
    assert total.total == 21


def test_counts_from_tier_rows():
    rows = [("correct", 5), ("almost_correct", 5)]
    assert counts_from_tier_rows(rows) == TierCounts(5, 5, 0)


def test_counts_from_tier_rows_sums_duplicate_tiers():
    # e.g. the same tier appearing in several rows (grouped by another column)
    rows = [("correct", 2), ("correct", 3)]
    assert counts_from_tier_rows(rows).correct == 5


def test_counts_from_tier_rows_rejects_unknown_tier():
    with pytest.raises(ValueError):
        counts_from_tier_rows([("perfect", 1)])