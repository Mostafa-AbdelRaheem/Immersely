# app/api/topics.py
from fastapi import APIRouter

from app.core.topics import TOPICS

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("")
async def list_topics() -> list[str]:
    return TOPICS