from datetime import date

from app.services.stats_logic import StreakInfo, compute_streaks

D = date


def test_real_data_yesterday_only_streak_still_alive():
    # Real case: events only on 2026-10-27, "today" is 2026-10-28.
    result = compute_streaks([D(2026, 10, 27)], today=D(2026, 10, 28))
    assert result == StreakInfo(current=1, longest=1)


def test_today_counts_when_active():
    days = [D(2026, 10, 26), D(2026, 10, 27), D(2026, 10, 28)]
    assert compute_streaks(days, today=D(2026, 10, 28)) == StreakInfo(3, 3)


def test_gap_of_a_full_day_breaks_current_streak():
    # Active 25th and 26th, nothing on the 27th, today is the 28th.
    days = [D(2026, 10, 25), D(2026, 10, 26)]
    assert compute_streaks(days, today=D(2026, 10, 28)) == StreakInfo(0, 2)


def test_no_events():
    assert compute_streaks([], today=D(2026, 10, 28)) == StreakInfo(0, 0)


def test_longest_can_be_an_older_run():
    days = [
        D(2026, 10, 1), D(2026, 10, 2), D(2026, 10, 3), D(2026, 10, 4),  # run of 4
        D(2026, 10, 27), D(2026, 10, 28),                                # run of 2
    ]
    assert compute_streaks(days, today=D(2026, 10, 28)) == StreakInfo(2, 4)


def test_duplicates_and_unordered_input():
    days = [D(2026, 10, 28), D(2026, 10, 26), D(2026, 10, 27), D(2026, 10, 27)]
    assert compute_streaks(days, today=D(2026, 10, 28)) == StreakInfo(3, 3)


def test_future_days_are_ignored():
    days = [D(2026, 10, 28), D(2026, 10, 29)]
    assert compute_streaks(days, today=D(2026, 10, 28)) == StreakInfo(1, 1)