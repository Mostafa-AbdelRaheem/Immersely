# app/api/review.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.correction import CheckAnswerIn, CheckAnswerOut
from app.services.correction import (
    CorrectionFailedError,
    SentenceNotFoundError,
    check_answer,
)

router = APIRouter(prefix="/review", tags=["review"])


@router.post("/{sentence_id}/check", response_model=CheckAnswerOut)
@limiter.limit("10/minute")
async def check_sentence_answer(
    request: Request,
    sentence_id: uuid.UUID,
    answer_in: CheckAnswerIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await check_answer(
            db, current_user.id, sentence_id, answer_in.answer
        )
    except SentenceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sentence {sentence_id} not found",
        )
    except CorrectionFailedError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not grade your answer right now. Please try again.",
        )
    return result