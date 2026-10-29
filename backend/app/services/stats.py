# app/services/stats.py
"""Queries feeding the pure functions in stats_logic.py.

Every query is scoped to user_id. Day bucketing happens in SQL via AT TIME ZONE.
The time window is a plain timestamptz comparison on created_at so the
(user_id, created_at) index can be used.
"""
import uuid
from collections import defaultdict
from collections.abc import Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_event import ReviewEvent
from app.models.sentence import Sentence
from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.services.stats_logic import (
    DayPoint,
    StreakInfo,
    TierCounts,
    TopicStat,
    accuracy,
    build_daily_series,
    build_topic_stats,
    compute_streaks,
    counts_from_tier_rows,
    resolve_range,
)

class InvalidTimezoneError(Exception):
    pass


def validate_timezone(tz: str) -> str:
    """Return tz unchanged if it is a real IANA name, else raise."""
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise InvalidTimezoneError(tz)
    return tz


async def tier_counts(
    db: AsyncSession, user_id: uuid.UUID, since: datetime | None = None
) -> list[tuple[str, int]]:
    stmt = (
        select(ReviewEvent.tier, func.count())
        .where(ReviewEvent.user_id == user_id)
        .group_by(ReviewEvent.tier)
    )
    if since is not None:
        stmt = stmt.where(ReviewEvent.created_at >= since)
    result = await db.execute(stmt)
    return [(tier, n) for tier, n in result.all()]


async def daily_tier_counts(
    db: AsyncSession,
    user_id: uuid.UUID,
    tz: str,
    since: datetime | None = None,
) -> list[tuple[date, str, int]]:
    # timezone(tz, ts) is Postgres' function form of "ts AT TIME ZONE tz".
    local_day = cast(func.timezone(tz, ReviewEvent.created_at), Date).label("day")
    stmt = (
        select(local_day, ReviewEvent.tier, func.count())
        .where(ReviewEvent.user_id == user_id)
        .group_by("day", ReviewEvent.tier)
        .order_by("day", ReviewEvent.tier)
    )
    if since is not None:
        stmt = stmt.where(ReviewEvent.created_at >= since)
    result = await db.execute(stmt)
    return [(day, tier, n) for day, tier, n in result.all()]


def expand_topic_rows(
    rows: Iterable[tuple[list[str] | None, str, int]],
) -> list[tuple[str | None, str, int]]:
    """Split (topics array, tier, count) rows into (topic, tier, count) rows.

    A sentence with several topics counts in each of them; an empty or missing
    topics array lands in the topic=None ("untagged") bucket.
    """
    totals: dict[tuple[str | None, str], int] = defaultdict(int)
    for topics, tier, n in rows:
        for topic in (topics or [None]):
            totals[(topic, tier)] += n
    return [(topic, tier, n) for (topic, tier), n in totals.items()]


async def topic_tier_counts(
    db: AsyncSession, user_id: uuid.UUID, since: datetime | None = None
) -> list[tuple[str | None, str, int]]:
    stmt = (
        select(Sentence.topics, ReviewEvent.tier, func.count())
        .join(Sentence, Sentence.id == ReviewEvent.sentence_id)
        .where(ReviewEvent.user_id == user_id)
        .group_by(Sentence.topics, ReviewEvent.tier)
    )
    if since is not None:
        stmt = stmt.where(ReviewEvent.created_at >= since)
    result = await db.execute(stmt)
    return expand_topic_rows(result.all())

@dataclass(frozen=True)
class StatsSummary:
    range_key: str
    tz: str
    start_day: date
    end_day: date
    totals: TierCounts
    series: list[DayPoint]
    topics: list[TopicStat]
    streaks: StreakInfo

    @property
    def accuracy(self) -> float | None:
        return accuracy(self.totals)


async def get_stats_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    range_key: str,
    tz: str,
    min_topic_events: int = 5,
    now: datetime | None = None,
) -> StatsSummary:
    validate_timezone(tz)
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo(tz)).date()
    start_day, since = resolve_range(range_key, tz, now)

    # One all-time query: feeds streaks, the chart and the range totals.
    daily_rows = await daily_tier_counts(db, user_id, tz)
    active_days = {day for day, _, _ in daily_rows}

    if range_key == "all":
        past_days = [d for d in active_days if d <= today]
        if past_days:
            start_day = min(past_days)

    totals = counts_from_tier_rows(
        (tier, n) for day, tier, n in daily_rows if start_day <= day <= today
    )
    series = build_daily_series(daily_rows, start_day, today)
    topics = build_topic_stats(
        await topic_tier_counts(db, user_id, since), min_events=min_topic_events
    )
    streaks = compute_streaks(active_days, today)

    return StatsSummary(
        range_key=range_key,
        tz=tz,
        start_day=start_day,
        end_day=today,
        totals=totals,
        series=series,
        topics=topics,
        streaks=streaks,
    )