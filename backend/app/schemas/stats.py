# app/schemas/stats.py
from datetime import date
from typing import Literal

from pydantic import BaseModel

RangeKey = Literal["7d", "30d", "90d", "all"]


class TierCountsOut(BaseModel):
    correct: int
    almost_correct: int
    incorrect: int
    total: int


class DayPointOut(BaseModel):
    day: date
    counts: TierCountsOut
    accuracy: float | None  # None = no reviews that day


class TopicStatOut(BaseModel):
    topic: str | None  # None = untagged
    counts: TierCountsOut
    accuracy: float | None
    ranked: bool  # False = not enough events to rank yet


class StreaksOut(BaseModel):
    current: int
    longest: int


class StatsSummaryOut(BaseModel):
    range: RangeKey
    timezone: str
    start_day: date
    end_day: date
    totals: TierCountsOut
    accuracy: float | None
    streaks: StreaksOut
    series: list[DayPointOut]
    topics: list[TopicStatOut]