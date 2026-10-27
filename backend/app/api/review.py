# app/api/review.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.correction import CheckAnswerIn, CheckAnswerOut
from app.schemas.review_session import (
    ReviewGradeIn,
    ReviewGradeOut,
    SessionStartIn,
    SessionStartOut,
)
from app.services.correction import (
    CorrectionFailedError,
    SentenceNotFoundError,
    check_answer,
)
from app.services.review_session import InvalidSceneError, record_review
from app.services.scene_verification import SceneVerificationFailedError
from app.services.scenes import NoDueSentencesError
from app.services.session_chunks import MalformedSceneError
from app.services.session_start import start_session
from app.services.sentences import SentenceNotFoundError as GradeSentenceNotFoundError

router = APIRouter(prefix="/review", tags=["review"])


@router.post("/session/start", response_model=SessionStartOut)
@limiter.limit("10/minute")
async def start_review_session(
    request: Request,
    session_in: SessionStartIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        plan = await start_session(
            db, current_user.id, session_in.topic, session_in.max_targets
        )
    except NoDueSentencesError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No due sentences to review",
        )
    except (SceneVerificationFailedError, MalformedSceneError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not prepare the review session right now. Please try again.",
        )
    return plan


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


@router.post("/{sentence_id}/grade", response_model=ReviewGradeOut)
@limiter.limit("60/minute")
async def grade_sentence_review(
    request: Request,
    sentence_id: uuid.UUID,
    grade_in: ReviewGradeIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        sentence = await record_review(db, current_user.id, sentence_id, grade_in)
    except GradeSentenceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sentence {sentence_id} not found",
        )
    except InvalidSceneError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene not found for this sentence",
        )
    return sentence