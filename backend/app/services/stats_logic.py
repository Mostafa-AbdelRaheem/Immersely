# app/services/stats_logic.py
"""Pure statistics math. No database, no FastAPI, so it is trivially unit-testable."""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

# Single source of truth for how a tier counts towards accuracy.
CORRECT_WEIGHT = 1.0
ALMOST_CORRECT_WEIGHT = 0.5
INCORRECT_WEIGHT = 0.0


@dataclass(frozen=True)
class TierCounts:
    correct: int = 0
    almost_correct: int = 0
    incorrect: int = 0

    @property
    def total(self) -> int:
        return self.correct + self.almost_correct + self.incorrect

    def __add__(self, other: "TierCounts") -> "TierCounts":
        return TierCounts(
            self.correct + other.correct,
            self.almost_correct + other.almost_correct,
            self.incorrect + other.incorrect,
        )


def accuracy(counts: TierCounts) -> float | None:
    """Weighted accuracy in [0, 1], or None when there are no events.

    None (not 0.0) matters: "no data" must not look like "0% correct".
    """
    if counts.total == 0:
        return None
    score = (
        counts.correct * CORRECT_WEIGHT
        + counts.almost_correct * ALMOST_CORRECT_WEIGHT
        + counts.incorrect * INCORRECT_WEIGHT
    )
    return score / counts.total


def counts_from_tier_rows(rows: Iterable[tuple[str, int]]) -> TierCounts:
    """Turn SQL rows like [('correct', 5), ('almost_correct', 5)] into TierCounts."""
    values = {"correct": 0, "almost_correct": 0, "incorrect": 0}
    for tier, n in rows:
        if tier not in values:
            raise ValueError(f"Unknown tier: {tier!r}")
        values[tier] += n
    return TierCounts(**values)

@dataclass(frozen=True)
class StreakInfo:
    current: int
    longest: int


def compute_streaks(active_days: Iterable[date], today: date) -> StreakInfo:
    """Streaks over local calendar days with at least one review.

    current: consecutive active days ending today, or ending yesterday if today
             has no review yet (the streak is still alive, just not extended).
    longest: the longest run of consecutive active days ever.
    `today` is passed in (the user's local date) so this stays pure.
    """
    days = {d for d in active_days if d <= today}  # ignore anything "in the future"
    if not days:
        return StreakInfo(current=0, longest=0)

    longest = 0
    for d in days:
        if d - timedelta(days=1) not in days:  # d starts a run
            length = 1
            while d + timedelta(days=length) in days:
                length += 1
            longest = max(longest, length)

    anchor = today if today in days else today - timedelta(days=1)
    current = 0
    while anchor - timedelta(days=current) in days:
        current += 1

    return StreakInfo(current=current, longest=longest)

@dataclass(frozen=True)
class DayPoint:
    day: date
    counts: TierCounts

    @property
    def accuracy(self) -> float | None:
        return accuracy(self.counts)


def build_daily_series(
    rows: Iterable[tuple[date, str, int]],
    start: date,
    end: date,
) -> list[DayPoint]:
    """One DayPoint per calendar day in [start, end], including empty days.

    rows: (local_day, tier, count) tuples from SQL. Rows outside the range are
    ignored, so a loose query can never leak extra days into the chart.
    """
    if end < start:
        raise ValueError("end must not be before start")

    by_day: dict[date, list[tuple[str, int]]] = {}
    for day, tier, n in rows:
        if start <= day <= end:
            by_day.setdefault(day, []).append((tier, n))

    series: list[DayPoint] = []
    current = start
    while current <= end:
        counts = counts_from_tier_rows(by_day.get(current, []))
        series.append(DayPoint(day=current, counts=counts))
        current += timedelta(days=1)
    return series

@dataclass(frozen=True)
class TopicStat:
    topic: str | None  # None = sentences with no topic tags
    counts: TierCounts
    ranked: bool       # True when there are enough events to rank this topic

    @property
    def accuracy(self) -> float | None:
        return accuracy(self.counts)


def build_topic_stats(
    rows: Iterable[tuple[str | None, str, int]],
    min_events: int = 5,
) -> list[TopicStat]:
    """Per-topic accuracy, weakest ranked topics first.

    rows: (topic, tier, count) tuples from SQL. Topics below min_events are
    returned last and flagged ranked=False, so one unlucky answer can't
    make a barely-reviewed topic look like the weakest one.
    """
    if min_events < 1:
        raise ValueError("min_events must be at least 1")

    by_topic: dict[str | None, list[tuple[str, int]]] = {}
    for topic, tier, n in rows:
        by_topic.setdefault(topic, []).append((tier, n))

    stats = []
    for topic, tier_rows in by_topic.items():
        counts = counts_from_tier_rows(tier_rows)
        stats.append(TopicStat(topic, counts, ranked=counts.total >= min_events))

    def sort_key(s: TopicStat):
        # Ranked first; among ranked: lowest accuracy, then most events, then name.
        acc = s.accuracy if s.ranked else 0.0
        return (not s.ranked, acc, -s.counts.total, s.topic or "")

    return sorted(stats, key=sort_key)

RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}


def resolve_range(
    range_key: str, tz: str, now: datetime
) -> tuple[date, datetime | None]:
    """Return (start_day, since_utc) for a range key.

    start_day: first local calendar day shown in the chart.
    since_utc: timezone-aware UTC lower bound for created_at, or None for "all".
    `now` is passed in (timezone-aware) so this stays pure and testable.
    For "all", start_day is today; the service moves it to the first event day.
    """
    zone = ZoneInfo(tz)
    today = now.astimezone(zone).date()
    if range_key == "all":
        return today, None
    if range_key not in RANGE_DAYS:
        raise ValueError(f"Unknown range: {range_key!r}")
    start_day = today - timedelta(days=RANGE_DAYS[range_key] - 1)
    local_midnight = datetime.combine(start_day, time.min, tzinfo=zone)
    return start_day, local_midnight.astimezone(timezone.utc)