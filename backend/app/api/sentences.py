# app/api/sentences.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.sentence import SentenceCreate, SentenceRead, SentenceUpdate
from app.services.sentences import (
    SentenceNotFoundError,
    create_sentence,
    delete_sentence,
    get_sentence,
    list_sentences,
    update_sentence,
)

router = APIRouter(prefix="/sentences", tags=["sentences"])


@router.post("", response_model=SentenceRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create(
    request: Request,
    sentence_in: SentenceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sentence = await create_sentence(db, current_user.id, sentence_in)
    return sentence


@router.get("", response_model=list[SentenceRead])
async def list_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_sentences(db, current_user.id)


@router.get("/{sentence_id}", response_model=SentenceRead)
async def get_one(
    sentence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        sentence = await get_sentence(db, current_user.id, sentence_id)
    except SentenceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sentence not found"
        )
    return sentence


@router.patch("/{sentence_id}", response_model=SentenceRead)
async def update(
    sentence_id: uuid.UUID,
    sentence_in: SentenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        sentence = await update_sentence(db, current_user.id, sentence_id, sentence_in)
    except SentenceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sentence not found"
        )
    return sentence


@router.delete("/{sentence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    sentence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_sentence(db, current_user.id, sentence_id)
    except SentenceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sentence not found"
        )