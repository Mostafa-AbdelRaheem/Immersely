# app/api/topics.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.topics import TOPICS
from app.models.user import User
from app.schemas.topics import TopicOverview
from app.services.topics import get_topic_overview

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("")
async def list_topics() -> list[str]:
    return TOPICS


@router.get("/overview", response_model=list[TopicOverview])
async def topic_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_topic_overview(db, current_user.id)