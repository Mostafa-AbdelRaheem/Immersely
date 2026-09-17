from datetime import datetime, timedelta, timezone

import pytest

from app.services.srs import Grade, SRSFields, SRSState, update_srs

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)


def new_card() -> SRSFields:
    return SRSFields(due=NOW, interval_days=0, ease=2.5, reps=0, lapses=0, state=SRSState.NEW)


def review_card(interval_days=6, ease=2.5, reps=3) -> SRSFields:
    return SRSFields(
        due=NOW, interval_days=interval_days, ease=ease, reps=reps, lapses=0, state=SRSState.REVIEW
    )


class TestLearningPhase:
    def test_good_advances_to_next_step_without_graduating(self):
        result = update_srs(new_card(), Grade.GOOD, now=NOW)
        assert result.state == SRSState.LEARNING
        assert result.due == NOW + timedelta(minutes=10)
        assert result.reps == 1

    def test_good_twice_graduates_to_review(self):
        after_first = update_srs(new_card(), Grade.GOOD, now=NOW)
        after_second = update_srs(after_first, Grade.GOOD, now=NOW)
        assert after_second.state == SRSState.REVIEW
        assert after_second.interval_days == 1
        assert after_second.due == NOW + timedelta(days=1)
        assert after_second.reps == 1

    def test_easy_graduates_immediately_with_bonus(self):
        result = update_srs(new_card(), Grade.EASY, now=NOW)
        assert result.state == SRSState.REVIEW
        assert result.interval_days == 4
        assert result.ease == pytest.approx(2.65)
        assert result.reps == 1

    def test_hard_repeats_current_step(self):
        result = update_srs(new_card(), Grade.HARD, now=NOW)
        assert result.state == SRSState.LEARNING
        assert result.due == NOW + timedelta(minutes=10)
        assert result.reps == 0

    def test_again_resets_to_first_step_without_lapse(self):
        card = SRSFields(due=NOW, interval_days=0, ease=2.5, reps=1, lapses=0, state=SRSState.LEARNING)
        result = update_srs(card, Grade.AGAIN, now=NOW)
        assert result.state == SRSState.LEARNING
        assert result.due == NOW + timedelta(minutes=10)
        assert result.reps == 0
        assert result.lapses == 0
        assert result.ease == pytest.approx(2.3)


class TestReviewPhase:
    def test_good_multiplies_interval_by_ease(self):
        result = update_srs(review_card(interval_days=6, ease=2.5), Grade.GOOD, now=NOW)
        assert result.interval_days == round(6 * 2.5)
        assert result.ease == pytest.approx(2.5)
        assert result.due == NOW + timedelta(days=result.interval_days)
        assert result.reps == 4

    def test_hard_shrinks_growth_and_lowers_ease(self):
        result = update_srs(review_card(interval_days=10, ease=2.5), Grade.HARD, now=NOW)
        assert result.interval_days == round(10 * 1.2)
        assert result.ease == pytest.approx(2.35)

    def test_easy_gives_a_bigger_jump_and_raises_ease(self):
        result = update_srs(review_card(interval_days=10, ease=2.5), Grade.EASY, now=NOW)
        assert result.interval_days == round(10 * 2.5 * 1.3)
        assert result.ease == pytest.approx(2.65)

    def test_again_causes_a_lapse_and_drops_to_relearning(self):
        result = update_srs(review_card(interval_days=20, ease=2.5), Grade.AGAIN, now=NOW)
        assert result.state == SRSState.RELEARNING
        assert result.interval_days == 0
        assert result.lapses == 1
        assert result.reps == 0
        assert result.due == NOW + timedelta(minutes=10)
        assert result.ease == pytest.approx(2.3)

    def test_ease_never_drops_below_floor(self):
        card = review_card(interval_days=5, ease=1.35)
        result = update_srs(card, Grade.AGAIN, now=NOW)
        assert result.ease == pytest.approx(1.3)

    def test_interval_never_drops_below_one_day(self):
        card = review_card(interval_days=1, ease=1.3)
        result = update_srs(card, Grade.HARD, now=NOW)
        assert result.interval_days >= 1


class TestRelearning:
    def test_good_in_relearning_eventually_regraduates(self):
        card = SRSFields(due=NOW, interval_days=0, ease=2.3, reps=0, lapses=1, state=SRSState.RELEARNING)
        after_first = update_srs(card, Grade.GOOD, now=NOW)
        assert after_first.state == SRSState.RELEARNING
        after_second = update_srs(after_first, Grade.GOOD, now=NOW)
        assert after_second.state == SRSState.REVIEW
        assert after_second.interval_days == 1

    def test_relearning_preserves_lapse_count(self):
        card = SRSFields(due=NOW, interval_days=0, ease=2.3, reps=0, lapses=2, state=SRSState.RELEARNING)
        result = update_srs(card, Grade.GOOD, now=NOW)
        assert result.lapses == 2


class TestDeterminism:
    def test_same_inputs_produce_same_output(self):
        card = review_card()
        r1 = update_srs(card, Grade.GOOD, now=NOW)
        r2 = update_srs(card, Grade.GOOD, now=NOW)
        assert r1 == r2

    def test_input_is_never_mutated(self):
        card = review_card()
        update_srs(card, Grade.GOOD, now=NOW)
        assert card == review_card()