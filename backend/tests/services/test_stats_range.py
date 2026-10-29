from datetime import date, datetime, timezone

import pytest

from app.services.stats_logic import resolve_range

UTC = timezone.utc


def test_7d_in_berlin_winter_time():
    # 2026-10-28 12:00 UTC is 13:00 in Berlin (CET after the 25 Oct switch).
    now = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    start, since = resolve_range("7d", "Europe/Berlin", now)
    assert start == date(2026, 10, 22)  # today + 6 days before = 7 days
    # Local midnight 22 Oct is still CEST (UTC+2) -> 21 Oct 22:00 UTC.
    assert since == datetime(2026, 10, 21, 22, 0, tzinfo=UTC)


def test_today_uses_user_timezone_not_utc():
    # 23:30 UTC on the 27th is already 00:30 on the 28th in Berlin.
    now = datetime(2026, 10, 27, 23, 30, tzinfo=UTC)
    start, _ = resolve_range("7d", "Europe/Berlin", now)
    assert start == date(2026, 10, 22)  # based on Berlin "today" = 28th
    start_utc, _ = resolve_range("7d", "UTC", now)
    assert start_utc == date(2026, 10, 21)  # based on UTC "today" = 27th


def test_all_has_no_lower_bound():
    now = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    start, since = resolve_range("all", "Europe/Berlin", now)
    assert since is None
    assert start == date(2026, 10, 28)


def test_30d_and_90d_lengths():
    now = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    assert resolve_range("30d", "UTC", now)[0] == date(2026, 9, 29)
    assert resolve_range("90d", "UTC", now)[0] == date(2026, 7, 31)


def test_since_is_timezone_aware_utc():
    now = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    _, since = resolve_range("30d", "Europe/Berlin", now)
    assert since.tzinfo is not None
    assert since.utcoffset().total_seconds() == 0


def test_unknown_range_raises():
    with pytest.raises(ValueError):
        resolve_range("1y", "UTC", datetime(2026, 10, 28, tzinfo=UTC))