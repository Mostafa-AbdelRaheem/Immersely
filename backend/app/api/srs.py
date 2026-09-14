# app/api/srs.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.srs import DueCountOut, GradeIn, SentenceWithSRS
from app.services.sentences import SentenceNotFoundError
from app.services.srs import count_due_sentences, grade_sentence, list_due_sentences

router = APIRouter(prefix="/srs", tags=["srs"])


@router.get("/due", response_model=list[SentenceWithSRS])
async def get_due_sentences(
    topic: str | None = None,
    limit: int = Query(default=50, gt=0, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_due_sentences(db, current_user.id, topic=topic, limit=limit)


@router.get("/due/count", response_model=DueCountOut)
async def get_due_count(
    topic: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await count_due_sentences(db, current_user.id, topic=topic)
    return DueCountOut(count=count)


@router.post("/{sentence_id}/grade", response_model=SentenceWithSRS)
async def grade(
    sentence_id: uuid.UUID,
    grade_in: GradeIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await grade_sentence(db, current_user.id, sentence_id, grade_in.grade)
    except SentenceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentence not found")