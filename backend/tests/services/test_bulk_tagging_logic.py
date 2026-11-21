# tests/services/test_bulk_tagging_logic.py
from app.schemas.bulk_tagging import BatchTagItem
from app.schemas.sentence import SentenceUpdate
from app.services.bulk_tagging_logic import (
    MAX_GRAMMAR_TAG_LEN,
    TagOutcome,
    normalize_grammar_tag,
    normalize_topics,
    reconcile,
)


def _item(index, topics, tag=None):
    return BatchTagItem(index=index, topics=topics, grammar_tag=tag)


def test_max_grammar_len_matches_the_schema_cap():
    metadata = SentenceUpdate.model_fields["grammar_tag"].metadata
    caps = [m.max_length for m in metadata if hasattr(m, "max_length")]
    assert caps == [MAX_GRAMMAR_TAG_LEN]


def test_grammar_tag_none_and_blank_become_none():
    assert normalize_grammar_tag(None) is None
    assert normalize_grammar_tag("   ") is None


def test_grammar_tag_is_trimmed():
    assert normalize_grammar_tag("  perfekt ") == "perfekt"


def test_grammar_tag_at_limit_is_kept():
    assert normalize_grammar_tag("a" * MAX_GRAMMAR_TAG_LEN) == "a" * MAX_GRAMMAR_TAG_LEN


def test_grammar_tag_over_limit_becomes_none_not_truncated():
    assert normalize_grammar_tag("a" * (MAX_GRAMMAR_TAG_LEN + 1)) is None


def test_topics_are_deduplicated_in_order_as_plain_strings():
    result = normalize_topics(["weather", "housing", "weather"])
    assert result == ("weather", "housing")
    assert all(type(t) is str for t in result)


def test_reconcile_accepts_all_good_items():
    items = [_item(1, ["weather"], "perfekt"), _item(2, ["housing"])]
    accepted, missing = reconcile({1, 2}, items)
    assert missing == []
    assert accepted[1] == TagOutcome(("weather",), "perfekt")
    assert accepted[2] == TagOutcome(("housing",), None)


def test_reconcile_reports_missing_labels_sorted():
    accepted, missing = reconcile({1, 2, 3}, [_item(2, ["weather"])])
    assert list(accepted) == [2]
    assert missing == [1, 3]


def test_duplicate_label_is_discarded_entirely_and_retried():
    items = [_item(1, ["weather"]), _item(2, ["weather"]), _item(2, ["housing"])]
    accepted, missing = reconcile({1, 2, 3}, items)
    assert list(accepted) == [1]
    assert missing == [2, 3]


def test_label_we_never_sent_is_ignored():
    accepted, missing = reconcile({1}, [_item(1, ["weather"]), _item(47, ["housing"])])
    assert list(accepted) == [1]
    assert missing == []


def test_unsent_label_does_not_poison_a_sent_one():
    # 0 was never sent; it must not affect the real label 1.
    accepted, _ = reconcile({1}, [_item(0, ["housing"]), _item(1, ["weather"])])
    assert accepted[1].topics == ("weather",)


def test_empty_topics_are_treated_as_missing():
    accepted, missing = reconcile({1, 2}, [_item(1, []), _item(2, ["weather"])])
    assert list(accepted) == [2]
    assert missing == [1]


def test_no_items_means_everything_is_missing():
    assert reconcile({1, 2}, []) == ({}, [1, 2])


def test_accepted_outcome_has_cleaned_grammar_tag():
    accepted, _ = reconcile({1}, [_item(1, ["weather"], "  ")])
    assert accepted[1].grammar_tag is None