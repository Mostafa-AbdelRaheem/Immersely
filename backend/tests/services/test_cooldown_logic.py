from datetime import datetime, timedelta, timezone

import pytest

from app.services.token_logic import is_in_cooldown

NOW = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
COOLDOWN = timedelta(seconds=60)


def test_no_previous_token_means_no_cooldown():
    assert is_in_cooldown(last_issued_at=None, now=NOW, cooldown=COOLDOWN) is False


def test_inside_the_window_is_in_cooldown():
    last = NOW - timedelta(seconds=59)
    assert is_in_cooldown(last_issued_at=last, now=NOW, cooldown=COOLDOWN) is True


def test_exactly_at_the_boundary_is_over():
    last = NOW - COOLDOWN
    assert is_in_cooldown(last_issued_at=last, now=NOW, cooldown=COOLDOWN) is False


def test_after_the_window_is_over():
    last = NOW - timedelta(seconds=61)
    assert is_in_cooldown(last_issued_at=last, now=NOW, cooldown=COOLDOWN) is False


def test_a_timestamp_in_the_future_counts_as_in_cooldown():
    last = NOW + timedelta(seconds=5)
    assert is_in_cooldown(last_issued_at=last, now=NOW, cooldown=COOLDOWN) is True


def test_naive_vs_aware_raises_instead_of_guessing():
    naive_last = datetime(2026, 11, 10, 11, 59, 30)
    with pytest.raises(TypeError):
        is_in_cooldown(last_issued_at=naive_last, now=NOW, cooldown=COOLDOWN)