import pytest

from app.services.stats_logic import TierCounts, build_topic_stats


def test_only_topics_with_enough_events_are_ranked():
    rows = [
        ("work", "correct", 3), ("work", "almost_correct", 2),  # 5 events
        ("greet", "correct", 2),                                 # 2 events
        ("cafe", "incorrect", 1),                                # 1 event
    ]
    stats = build_topic_stats(rows, min_events=5)
    by_name = {s.topic: s for s in stats}

    assert by_name["work"].ranked is True
    assert by_name["work"].accuracy == 0.8  # (3 + 1) / 5
    assert by_name["greet"].ranked is False
    assert by_name["cafe"].ranked is False
    assert stats[0].topic == "work"  # ranked topics come first


def test_ranked_sorted_weakest_first():
    rows = [
        ("a", "correct", 5),                              # 1.0
        ("b", "incorrect", 5),                            # 0.0
        ("c", "correct", 3), ("c", "incorrect", 2),       # 0.6
    ]
    stats = build_topic_stats(rows, min_events=5)
    assert [s.topic for s in stats] == ["b", "c", "a"]


def test_tie_broken_by_more_events_then_name():
    rows = [
        ("a", "almost_correct", 5),   # 0.5, 5 events
        ("b", "almost_correct", 10),  # 0.5, 10 events
        ("c", "almost_correct", 10),  # 0.5, 10 events
    ]
    stats = build_topic_stats(rows, min_events=5)
    assert [s.topic for s in stats] == ["b", "c", "a"]


def test_unranked_come_after_ranked_regardless_of_accuracy():
    rows = [
        ("solid", "correct", 5),     # ranked, accuracy 1.0
        ("tiny", "incorrect", 1),    # unranked, accuracy 0.0
    ]
    stats = build_topic_stats(rows, min_events=5)
    assert [s.topic for s in stats] == ["solid", "tiny"]
    assert [s.ranked for s in stats] == [True, False]


def test_untagged_none_topic_is_kept_separate():
    rows = [(None, "incorrect", 5), ("x", "correct", 5)]
    stats = build_topic_stats(rows, min_events=5)
    assert [s.topic for s in stats] == [None, "x"]  # None is weakest here
    assert stats[0].counts == TierCounts(0, 0, 5)


def test_tier_rows_for_same_topic_are_combined():
    stats = build_topic_stats([("x", "correct", 2), ("x", "correct", 3)], min_events=1)
    assert len(stats) == 1
    assert stats[0].counts.correct == 5


def test_min_events_must_be_positive():
    with pytest.raises(ValueError):
        build_topic_stats([], min_events=0)


def test_unknown_tier_raises():
    with pytest.raises(ValueError):
        build_topic_stats([("x", "perfect", 1)])