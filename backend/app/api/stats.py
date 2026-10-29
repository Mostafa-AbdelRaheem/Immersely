# app/api/stats.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.stats import (
    DayPointOut,
    RangeKey,
    StatsSummaryOut,
    StreaksOut,
    TierCountsOut,
    TopicStatOut,
)
from app.services.stats import InvalidTimezoneError, get_stats_summary
from app.services.stats_logic import TierCounts

router = APIRouter(prefix="/stats", tags=["stats"])


def _counts_out(c: TierCounts) -> TierCountsOut:
    return TierCountsOut(
        correct=c.correct,
        almost_correct=c.almost_correct,
        incorrect=c.incorrect,
        total=c.total,
    )


@router.get("/summary", response_model=StatsSummaryOut)
async def get_summary(
    range_key: RangeKey = Query(default="30d", alias="range"),
    tz: str = Query(default="UTC", max_length=64),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        s = await get_stats_summary(db, current_user.id, range_key, tz)
    except InvalidTimezoneError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid timezone",
        )

    return StatsSummaryOut(
        range=s.range_key,
        timezone=s.tz,
        start_day=s.start_day,
        end_day=s.end_day,
        totals=_counts_out(s.totals),
        accuracy=s.accuracy,
        streaks=StreaksOut(current=s.streaks.current, longest=s.streaks.longest),
        series=[
            DayPointOut(day=p.day, counts=_counts_out(p.counts), accuracy=p.accuracy)
            for p in s.series
        ],
        topics=[
            TopicStatOut(
                topic=t.topic,
                counts=_counts_out(t.counts),
                accuracy=t.accuracy,
                ranked=t.ranked,
            )
            for t in s.topics
        ],
    )