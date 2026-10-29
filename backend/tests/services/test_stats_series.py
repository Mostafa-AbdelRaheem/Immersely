from datetime import date

import pytest

from app.services.stats_logic import TierCounts, build_daily_series

D = date


def test_fills_empty_days_with_none_accuracy():
    rows = [(D(2026, 10, 20), "correct", 2), (D(2026, 10, 23), "incorrect", 1)]
    series = build_daily_series(rows, start=D(2026, 10, 20), end=D(2026, 10, 23))

    assert [p.day for p in series] == [
        D(2026, 10, 20), D(2026, 10, 21), D(2026, 10, 22), D(2026, 10, 23),
    ]
    assert [p.accuracy for p in series] == [1.0, None, None, 0.0]


def test_real_data_single_day():
    rows = [(D(2026, 10, 27), "correct", 5), (D(2026, 10, 27), "almost_correct", 5)]
    series = build_daily_series(rows, start=D(2026, 10, 26), end=D(2026, 10, 28))

    assert len(series) == 3
    assert series[0].counts == TierCounts()          # 26th: nothing
    assert series[1].counts == TierCounts(5, 5, 0)   # 27th: the real events
    assert series[1].accuracy == 0.75
    assert series[2].accuracy is None                # 28th: nothing yet


def test_rows_outside_range_are_ignored():
    rows = [(D(2026, 10, 1), "correct", 9), (D(2026, 10, 27), "correct", 1)]
    series = build_daily_series(rows, start=D(2026, 10, 27), end=D(2026, 10, 27))
    assert len(series) == 1
    assert series[0].counts.total == 1


def test_multiple_tier_rows_same_day_are_combined():
    rows = [
        (D(2026, 10, 27), "correct", 1),
        (D(2026, 10, 27), "almost_correct", 1),
        (D(2026, 10, 27), "incorrect", 2),
    ]
    series = build_daily_series(rows, start=D(2026, 10, 27), end=D(2026, 10, 27))
    assert series[0].counts == TierCounts(1, 1, 2)
    assert series[0].accuracy == 0.375  # (1 + 0.5) / 4


def test_single_day_range_with_no_rows():
    series = build_daily_series([], start=D(2026, 10, 28), end=D(2026, 10, 28))
    assert len(series) == 1
    assert series[0].accuracy is None


def test_end_before_start_raises():
    with pytest.raises(ValueError):
        build_daily_series([], start=D(2026, 10, 28), end=D(2026, 10, 27))


def test_unknown_tier_raises():
    with pytest.raises(ValueError):
        build_daily_series(
            [(D(2026, 10, 27), "perfect", 1)], start=D(2026, 10, 27), end=D(2026, 10, 27)
        )