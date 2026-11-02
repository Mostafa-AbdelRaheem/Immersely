# app/api/articles.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.article import ArticleCreate, ArticleRead
from app.services.articles import (
    ArticleGenerationFailedError,
    ArticleNotFoundError,
    NoSentencesForTopicError,
    create_article,
    delete_article,
    get_article,
    list_articles,
)

router = APIRouter(prefix="/articles", tags=["articles"])


@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create(
    request: Request,
    article_in: ArticleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_article(db, current_user.id, article_in.topic)
    except NoSentencesForTopicError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No sentences for topic '{article_in.topic}'",
        )
    except ArticleGenerationFailedError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not generate an article right now. Please try again.",
        )


@router.get("", response_model=list[ArticleRead])
async def list_all(
    topic: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_articles(db, current_user.id, topic=topic)


@router.get("/{article_id}", response_model=ArticleRead)
async def get_one(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_article(db, current_user.id, article_id)
    except ArticleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_article(db, current_user.id, article_id)
    except ArticleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)